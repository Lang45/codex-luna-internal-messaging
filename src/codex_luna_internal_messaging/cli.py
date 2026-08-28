"""Inspect and safely update a complete Codex model catalog.

This utility intentionally requires an explicit catalog path and a compare-and-
swap SHA-256 value. It never discovers or edits config.toml and never restarts
Codex.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

MODEL_SLUG = "gpt-5.6-luna"
SUPPORTED_BEFORE_VALUES = {None, "v1", "v2"}


class CatalogError(RuntimeError):
    """A safe, user-actionable catalog validation failure."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_catalog(path: Path) -> tuple[bytes, dict[str, Any], list[dict[str, Any]], int]:
    if not path.is_file():
        raise CatalogError(f"catalog_not_found: {path}")

    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CatalogError(f"catalog_is_not_valid_utf8_json: {exc}") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        raise CatalogError("unsupported_catalog_shape: expected an object with a models array")

    models = payload["models"]
    if not all(isinstance(model, dict) for model in models):
        raise CatalogError("unsupported_catalog_shape: every models entry must be an object")

    matches = [index for index, model in enumerate(models) if model.get("slug") == MODEL_SLUG]
    if len(matches) != 1:
        raise CatalogError(
            f"luna_model_count_mismatch: expected exactly one {MODEL_SLUG}, found {len(matches)}"
        )

    return raw, payload, models, matches[0]


def inspect_catalog(catalog_path: str | os.PathLike[str]) -> dict[str, Any]:
    path = Path(catalog_path).expanduser().resolve()
    raw, _payload, models, luna_index = _read_catalog(path)
    version = models[luna_index].get("multi_agent_version")
    return {
        "ok": True,
        "action": "status",
        "catalog": str(path),
        "sha256": _sha256(raw),
        "model_count": len(models),
        "luna_slug": MODEL_SLUG,
        "luna_multi_agent_version": version,
        "ready_for_v2_child_collaboration": version == "v2",
    }


def _next_backup_path(path: Path, now: dt.datetime | None = None) -> Path:
    timestamp = (now or dt.datetime.now(dt.timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    candidate = path.with_name(f"{path.name}.backup-{timestamp}.json")
    counter = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.backup-{timestamp}-{counter}.json")
        counter += 1
    return candidate


def _assert_only_luna_version_changed(
    before: dict[str, Any], after: dict[str, Any], luna_index: int
) -> None:
    before_copy = copy.deepcopy(before)
    after_copy = copy.deepcopy(after)
    before_luna = before_copy["models"][luna_index]
    after_luna = after_copy["models"][luna_index]
    before_luna.pop("multi_agent_version", None)
    after_luna.pop("multi_agent_version", None)
    if before_copy != after_copy:
        raise CatalogError("unexpected_semantic_delta: fields other than Luna multi_agent_version changed")


def enable_catalog(
    catalog_path: str | os.PathLike[str],
    expected_sha256: str,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    path = Path(catalog_path).expanduser().resolve()
    raw, payload, models, luna_index = _read_catalog(path)
    current_sha256 = _sha256(raw)
    normalized_expected = expected_sha256.strip().lower()
    if normalized_expected != current_sha256:
        raise CatalogError(
            "catalog_sha256_mismatch: run status again and review the catalog before retrying"
        )

    current_version = models[luna_index].get("multi_agent_version")
    if current_version not in SUPPORTED_BEFORE_VALUES:
        raise CatalogError(
            f"unsupported_luna_multi_agent_version: {current_version!r}; no changes were made"
        )
    if current_version == "v2":
        return {
            "ok": True,
            "action": "already_enabled",
            "catalog": str(path),
            "sha256": current_sha256,
            "backup": None,
        }

    updated = copy.deepcopy(payload)
    updated["models"][luna_index]["multi_agent_version"] = "v2"
    _assert_only_luna_version_changed(payload, updated, luna_index)
    updated_bytes = (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    updated_sha256 = _sha256(updated_bytes)

    if dry_run:
        return {
            "ok": True,
            "action": "would_enable",
            "catalog": str(path),
            "before_sha256": current_sha256,
            "after_sha256": updated_sha256,
            "backup": None,
        }

    backup_path = _next_backup_path(path)
    shutil.copy2(path, backup_path)

    # Fail closed if the catalog changed after the initial compare-and-swap check.
    if _sha256(path.read_bytes()) != current_sha256:
        raise CatalogError(
            f"catalog_changed_during_update: no write was made; backup retained at {backup_path}"
        )

    original_mode = stat.S_IMODE(path.stat().st_mode)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(updated_bytes)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.chmod(temp_path, original_mode)
        if _sha256(path.read_bytes()) != current_sha256:
            raise CatalogError(
                f"catalog_changed_before_replace: no write was made; backup retained at {backup_path}"
            )
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

    verification = inspect_catalog(path)
    if not verification["ready_for_v2_child_collaboration"]:
        raise CatalogError(
            f"post_write_verification_failed: restore the backup at {backup_path}"
        )

    return {
        "ok": True,
        "action": "enabled",
        "catalog": str(path),
        "before_sha256": current_sha256,
        "after_sha256": verification["sha256"],
        "backup": str(backup_path),
        "restart_required": True,
        "fresh_parent_task_required": True,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex-luna-internal-messaging",
        description="Inspect or enable the Luna v2 model-catalog gate used by Codex subagents.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Inspect a complete model catalog")
    status_parser.add_argument("--catalog", required=True, help="Explicit path to the complete JSON catalog")

    enable_parser = subparsers.add_parser("enable", help="Set Luna multi_agent_version to v2 safely")
    enable_parser.add_argument("--catalog", required=True, help="Explicit path to the complete JSON catalog")
    enable_parser.add_argument(
        "--expected-sha256",
        required=True,
        help="SHA-256 returned by a fresh status call",
    )
    enable_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and show the semantic change without writing or backing up",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result = inspect_catalog(args.catalog)
        else:
            result = enable_catalog(
                args.catalog,
                args.expected_sha256,
                dry_run=args.dry_run,
            )
    except CatalogError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
