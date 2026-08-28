from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from codex_luna_internal_messaging.cli import CatalogError  # noqa: E402
from codex_luna_internal_messaging.cli import enable_catalog  # noqa: E402
from codex_luna_internal_messaging.cli import inspect_catalog  # noqa: E402


def catalog_payload(version: str | None = "v1") -> dict:
    luna = {"slug": "gpt-5.6-luna", "display_name": "GPT-5.6 Luna", "priority": 3}
    if version is not None:
        luna["multi_agent_version"] = version
    return {
        "models": [
            {"slug": "gpt-5.6-sol", "multi_agent_version": "v2", "priority": 1},
            luna,
            {"slug": "gpt-5.6-terra", "multi_agent_version": "v2", "priority": 2},
        ]
    }


def write_catalog(path: Path, payload: dict) -> str:
    raw = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


class CatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "catalog.json"

    def test_status_reports_v1_as_not_ready(self) -> None:
        expected_sha = write_catalog(self.path, catalog_payload("v1"))
        result = inspect_catalog(self.path)
        self.assertEqual(result["sha256"], expected_sha)
        self.assertEqual(result["model_count"], 3)
        self.assertEqual(result["luna_multi_agent_version"], "v1")
        self.assertFalse(result["ready_for_v2_child_collaboration"])

    def test_enable_changes_only_luna_and_creates_backup(self) -> None:
        before = catalog_payload("v1")
        expected_sha = write_catalog(self.path, before)
        result = enable_catalog(self.path, expected_sha)
        self.assertEqual(result["action"], "enabled")
        backup = Path(result["backup"])
        self.assertTrue(backup.is_file())
        self.assertEqual(json.loads(backup.read_text(encoding="utf-8")), before)

        after = json.loads(self.path.read_text(encoding="utf-8"))
        expected_after = copy.deepcopy(before)
        expected_after["models"][1]["multi_agent_version"] = "v2"
        self.assertEqual(after, expected_after)

    def test_enable_is_idempotent_after_success(self) -> None:
        expected_sha = write_catalog(self.path, catalog_payload("v1"))
        enable_catalog(self.path, expected_sha)
        current_sha = inspect_catalog(self.path)["sha256"]
        result = enable_catalog(self.path, current_sha)
        self.assertEqual(result["action"], "already_enabled")
        self.assertIsNone(result["backup"])

    def test_dry_run_does_not_write_or_create_backup(self) -> None:
        expected_sha = write_catalog(self.path, catalog_payload(None))
        before = self.path.read_bytes()
        result = enable_catalog(self.path, expected_sha, dry_run=True)
        self.assertEqual(result["action"], "would_enable")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob("*.backup-*.json")), [])

    def test_hash_mismatch_fails_closed(self) -> None:
        write_catalog(self.path, catalog_payload("v1"))
        before = self.path.read_bytes()
        with self.assertRaisesRegex(CatalogError, "catalog_sha256_mismatch"):
            enable_catalog(self.path, "0" * 64)
        self.assertEqual(self.path.read_bytes(), before)

    def test_duplicate_luna_is_rejected(self) -> None:
        payload = catalog_payload("v1")
        payload["models"].append(copy.deepcopy(payload["models"][1]))
        write_catalog(self.path, payload)
        with self.assertRaisesRegex(CatalogError, "luna_model_count_mismatch"):
            inspect_catalog(self.path)

    def test_unknown_version_is_rejected(self) -> None:
        expected_sha = write_catalog(self.path, catalog_payload("disabled"))
        before = self.path.read_bytes()
        with self.assertRaisesRegex(CatalogError, "unsupported_luna_multi_agent_version"):
            enable_catalog(self.path, expected_sha)
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
