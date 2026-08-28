# Codex Luna Internal Messaging

[简体中文](README.zh-CN.md)

A small, auditable utility for inspecting and safely changing the complete
Codex model-catalog entry that gates v2 collaboration tools for spawned
`gpt-5.6-luna` subagents.

> **Important:** `multi_agent_version` is an internal Codex implementation
> detail, not a currently documented user-facing compatibility promise. Back up
> your catalog, review every change, and expect future Codex releases to change
> this behavior.

## What this fixes

In the affected runtime shape, a parent can expose multi-agent tools while a
spawned Luna child still lacks internal `collaboration.send_message`. OpenAI's
open-source Codex gate requires a v2 child with an agent path to use a model
preset whose `multi_agent_version` is also v2.

This utility:

- reads only the complete JSON catalog path you explicitly provide;
- requires a fresh SHA-256 compare-and-swap value before writing;
- requires exactly one `gpt-5.6-luna` entry;
- changes only Luna's `multi_agent_version` from missing/v1 to v2;
- creates a timestamped backup;
- writes atomically and verifies the result;
- never edits `config.toml`, never changes permissions, and never restarts Codex.

The implementation evidence and important limits are documented in
[docs/INTERNALS.md](docs/INTERNALS.md).

## Requirements

- Python 3.10 or newer
- a complete Codex model catalog in JSON format
- a Codex release with multi-agent v2 support

## Inspect first

Run directly from a clone:

```powershell
$env:PYTHONPATH = "$PWD\src"
py -3 -X utf8 -m codex_luna_internal_messaging status `
  --catalog "C:\path\to\complete-model-catalog.json"
```

On macOS or Linux, use `python3` and the corresponding path syntax.

The command returns only a small status object, including the current catalog
SHA-256. It does not print model instructions or other catalog contents.

## Dry-run and enable

Copy the SHA-256 from a fresh status call:

```powershell
$catalogSha = "<fresh status sha256>"

py -3 -X utf8 -m codex_luna_internal_messaging enable `
  --catalog "C:\path\to\complete-model-catalog.json" `
  --expected-sha256 $catalogSha `
  --dry-run
```

Review the result, then omit `--dry-run` to create a backup and apply the
single semantic change:

```powershell
py -3 -X utf8 -m codex_luna_internal_messaging enable `
  --catalog "C:\path\to\complete-model-catalog.json" `
  --expected-sha256 $catalogSha
```

The writer normalizes JSON formatting to two-space indentation. All model
objects and fields remain semantically unchanged except Luna's
`multi_agent_version`. The original bytes are retained in the reported backup.

## Activate and verify

1. Ensure your Codex `model_catalog_json` setting points to the complete catalog
   you reviewed. This repository does not edit that setting.
2. Fully restart Codex so the process reloads model metadata.
3. Start a fresh parent task. Existing tasks may retain the old model object.
4. Use [the minimal acceptance prompt](prompts/verify-internal-message.md).
5. Pass only when the parent receives a real internal `MESSAGE` before the
   child's `FINAL_ANSWER`, and the child reaches `Done`.

Do not inspect nested `functions.exec` `ALL_TOOLS` to decide whether the direct
tool exists. Do not use `list_threads` or `send_message_to_thread` as a fallback;
those are cross-task operations, not internal parent-child communication.

## Permissions are separate

The [official OpenAI subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)
explains that spawned agents inherit the parent turn's live permission mode.
Communication verification does not require switching Full access or Read-only.
Choose permissions only for the real task's needs or when the user explicitly
requests a restriction.

## Tests

```powershell
py -3 -X utf8 -m unittest discover -s tests -v
```

The suite covers status, one-field enablement, backup creation, idempotence,
dry-run behavior, SHA-256 mismatch rejection, duplicate Luna rejection, and
unknown-version rejection.

## License

MIT. This project is independent and is not an official OpenAI product.
