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

## Release evidence

- Public repository: `https://github.com/Lang45/codex-luna-internal-messaging`.
- GitHub read-back: `visibility=PUBLIC`, `isPrivate=false`, default branch `main`.
- Initial implementation commit:
  `b4af7a783181c9786f83b794adb69d214e65a7af`.
- Local validation: 7/7 unit tests, Python compile check, pyproject parse,
  active-catalog read-only status, staged diff check, and public-data scan passed.
- GitHub Actions run `33145237613` completed successfully on Ubuntu and Windows
  with Python 3.10 and 3.13; all four jobs passed.
- The workflow uses `actions/checkout@v7` and `actions/setup-python@v7`, the
  current stable major releases checked from their official repositories. Final
  delivery still requires the latest `main` run to pass after this update.
- The active complete catalog was only inspected and reported Luna v2. The
  release process did not edit that catalog, Codex config, permissions, or app
  processes.

## Boundaries

- `multi_agent_version` is an internal implementation detail and may change.
- The utility does not promise support for future Codex versions.
- Future releases are incomplete until GitHub visibility, remote commit, and CI
  results are read back again.
