# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); [semantic versioning](https://semver.org/).

## [1.0.0] - 2026-10-20

First public version of Monday. It is a rebuild rather than an evolution of the AgentForge codebase below; only a few small helpers (such as the glob matcher used for scope) closely mirror AgentForge's. Their history is preserved in this repository through a merge that keeps it intact, without rewriting it.

### Added

- **Model-agnostic core** (`core/`), installed into each project as a versioned copy in `.monday/` with a manifest of hashes that detects local edits to managed files.
- **`AGENTS.md` entry point** (under 200 lines) with a managed block. The method has three modes (direct, tracked, orchestrated) and three risk levels.
- **Project memory:**
  - `features.json` is the executable contract: scope plus acceptance criteria with commands.
  - `progress/current.md`, `progress/exploration_logs.md` and `progress/history.md` hold the work in progress, persistent findings and history.
  - `docs/architecture.md` records conventions and decisions.
- **`monday.py` CLI** (Python 3, standard library only): `status`, `check`, `start`, `verify`, `scope`, `review`, `done`, `amend`, `block`, `guard`, `hook`, `install`, `rollback`.
- **`monday done`** closes a feature only when all of these pass: `init.sh` (`--full` for medium and high risk), every criterion, the scope check against the git diff, an independent review anchored to the reviewed diff (when required), and an unchanged contract fingerprint. Check results are `PASS`, `FAIL`, `UNAVAILABLE` or `MANUAL`, and rejections are recorded in the history.
- **Persisted verification state.** `status` and the session-start hook report the last `init.sh` result (CLI output in Spanish: `ROJO`, `VERDE`, `DESACTUALIZADA` or `ninguna registrada`); missing evidence is never shown as success. A session that ends with a red `init.sh` is recorded in the history.
- **Platform-neutral roles:** explorer, implementer and reviewer.
- **Claude Code adapter:** `CLAUDE.md` → `@AGENTS.md`, `SessionStart`/`PreToolUse`/`Stop` hooks, and the `monday-explorer`, `monday-implementer` and `monday-reviewer` agents.
- **Antigravity CLI adapter:** `.agents/hooks.json` (`SessionStart`/`PreToolUse`/`Stop`) and the same agents in `.agents/agents/`. The scope guard checks the paths in the arguments of any non-read tool, so it does not depend on `agy`'s changing tool names.
- **Install, update and rollback.** Install merges instead of overwriting, an update stops when managed files were edited locally, and `rollback` restores the previous state (`--all` uninstalls). Local runtime state is never distributed.
- **Installing into existing projects.** Install prints notices (`AVISO:`) for what it does not manage: an `init.sh` of the project's own that does not run `monday check`, Monday 0.9 / AgentForge leftovers in the project, and the global links of the 0.9 and 0.1 `install.sh`. It never modifies them. The README documents how to check, uninstall and upgrade from 0.9, and how to ask an agent to install Monday from the public repository.
- **Tests:**
  - 51 deterministic tests: the eight validation scenarios, distribution, design integrity and regressions.
  - Release checks (`tests/release_check.sh`) and a clean-folder quick start (`tests/quickstart.sh [url [ref]]`, also run against the public repository).
  - Real-agent validation (`tests/e2e_adapters.sh`): 16 checks, including a forced false success report.

### Changed from AgentForge

- YAML contracts and self-reported results → `features.json` entries whose criteria Monday runs itself.
- Levels L0–L5 × tiers × gates G1–G8 → three modes. The role sets the tier, and the concrete model lives only in the adapter.
- Global skill linked with symlinks → a per-project copy ("the repository is the system").
- No hooks → three thin hooks, with all logic in the CLI.
- PyYAML → standard library only.

### Removed

- AgentForge's routing profiles and postures, the capability catalog and `cap status`, the Interface Integrity Gate as a separate mechanism, `--purge-legacy`, `af.py`, and the `.agentforge/` migration.

### Known limitations

See [README → Known limitations](README.md#known-limitations). In short:

- the final message a platform shows is not controlled by Monday;
- the stop hook has documented edge cases;
- the `amend` guard does not see shell aliases;
- `features.json` is an editable file;
- tested on Linux only.

## [0.9.0] - 2026-10-18 (AgentForge repository)

First transition of AgentForge to the Monday name: the `monday.py` CLI, the `.monday/` project directory, `monday-*` subagents and a capability catalog. Preserved as tag `v0.9.0`.

## [0.1.0] - 2026-10-07 (AgentForge)

AgentForge's methodology, with routing L0–L5, quality gates, YAML contracts, the `af.py` tooling and the Claude Code and Antigravity adapters. Preserved as tag `v0.1.0`.
