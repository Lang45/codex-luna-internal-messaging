# Codex Luna Internal Messaging project handoff

## Root principles

- The user-authorized goal is a standalone public repository for the Luna
  subagent internal-message compatibility finding.
- Never edit a discovered path implicitly. The utility accepts an explicit
  complete-catalog path, requires a fresh SHA-256, backs up, and writes atomically.
- Never edit Codex configuration, restart Codex, or change permission modes.
- Keep official documentation, open-source implementation evidence, and local
  runtime observations clearly separated.
- Do not publish local paths, rollout IDs, account data, credentials, or raw
  model instructions.

## Current state

- Repository name: `Lang45/codex-luna-internal-messaging`.
- Version: `0.1.0`.
- Runtime dependency: Python 3.10+ standard library only.
- Public evidence is pinned to OpenAI Codex commit
  `6be2a6ca952ac9f70676ce4dd07fda27175aa9dd`.
- The utility supports `status` and compare-and-swap `enable` commands.
- The repository includes a minimal fresh-task acceptance prompt and unit tests.

## Remaining release steps

1. Run the full unit test suite and compile check.
2. Run a dry-run against a temporary fixture and a read-only status check against
   the active complete catalog.
3. Scan the repository for secrets and local identifiers.
4. Initialize Git, commit once, create the public GitHub repository, and push.
5. Read back visibility, default branch, commit, and CI status.

## Boundaries

- `multi_agent_version` is an internal implementation detail and may change.
- The utility does not promise support for future Codex versions.
- No release or upload is complete until GitHub visibility and commit are read
  back from the remote.
