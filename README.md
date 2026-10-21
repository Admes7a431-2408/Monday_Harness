# Monday

**A model-agnostic harness for software development with AI agents.**

Monday is my first attempt at building a modular workflow that makes working with AI coding agents more predictable, verifiable and safe, without depending on any specific model or vendor to guarantee the quality of the process.

> **Status: v1.0.0, first public version.** Monday is a working experiment, not a mature framework. It is tested on Linux with Claude Code and the Antigravity CLI. Read [Known limitations](#known-limitations) before relying on it.

## Why it exists

Monday started as **AgentForge**, a personal project born from a simple concern: I wanted to trust the work of my AI agents more, and I wanted the same workflow regardless of which model I was using that day.

AgentForge explored contracts, quality gates, scope control and model routing. Its two releases are preserved as witnesses of that evolution: [`v0.1.0`](https://github.com/Admes7a431-2408/Monday_Harness/releases/tag/v0.1.0) (AgentForge) and [`v0.9.0`](https://github.com/Admes7a431-2408/Monday_Harness/releases/tag/v0.9.0) (first transition to the Monday name). Monday 1.0 keeps that intention but rebuilds it with fewer moving parts. The project's memory lives in the repository instead of the chat, contracts are executable, and the guarantees that matter are enforced by a CLI or a hook rather than by the model's goodwill. The Git history keeps both stages.

This version is what I learned along the way. It is a starting point, not the final form of the idea.

## Problems it tries to reduce

Monday does not eliminate these risks. It tries to make them smaller, visible and controllable:

- **Lost context between sessions**: work is hard to resume once the conversation is gone.
- **Results that look right but have no evidence**: "done" and "it works" stated by the agent itself.
- **Scope creep and unauthorized actions**: agents editing what they were not asked to touch, or running irreversible commands.
- **Inconsistent workflows across models and platforms.**
- **Over-reliance on chat memory and on the agent's own claims.**

## Principles

- **Model independence**: the workflow and its quality criteria do not belong to an AI vendor.
- **Modularity**: integrations with agents and environments are swappable adapters; the core does not change.
- **Verification over blind trust**: results are backed by evidence whenever possible.
- **Continuity**: important state persists outside the conversation.
- **Explicit limits**: an agent's technical capability is not authorization to act.
- **Simplicity**: every component must justify its existence, with no duplicated rules or context.
- **Open evolution**: Monday is meant to learn and change through real use.

## How it works

Installing Monday into a project adds a small set of files. All of them are plain Markdown, JSON or Bash.

| File | Purpose |
|---|---|
| `AGENTS.md` | Entry point for any agent (under 200 lines): session protocol, golden rules, project map |
| `init.sh` | Quick (`./init.sh`) and full (`./init.sh --full`) validation of the project |
| `features.json` | Backlog: each task's scope and executable acceptance criteria. This is the contract |
| `progress/current.md`, `exploration_logs.md`, `history.md` | Task in progress, findings worth keeping, history with evidence |
| `docs/architecture.md` | Conventions, decisions and rules learned from repeated mistakes |
| `.monday/` | Managed core: method, roles, policy and the `monday.py` CLI (Python 3, standard library only) |
| Adapters | `CLAUDE.md` + `.claude/` (Claude Code) and `.agents/` (Antigravity): hooks and role agents |

The agent picks a **mode** based on complexity and risk:

- **Direct**: a clear, local, low-risk change. Do it, run the relevant check, say what changed.
- **Tracked**: a feature in `features.json` with criteria, closed with `monday done`.
- **Orchestrated**: exploration by a read-only explorer, implementation from a brief, and an independent review.

**Closing a task is decided by Monday, not by the agent.** `monday done <id>` accepts a feature only if all of these pass:

- `init.sh`;
- every acceptance criterion's command;
- the scope check against the git diff;
- for high-risk work, an independent review anchored to the exact diff that was reviewed.

Changing the contract after starting requires `monday amend`, which is recorded in the history. A failed or missing verification is never reported as success.

Each adapter wires three hooks into its platform:

- the project state is injected when a session starts;
- writes outside the active feature's scope, and irreversible commands, are intercepted before they run;
- the agent cannot stop with uncommitted changes and a red `init.sh` without being told to fix it or explain it.

The last verification result is persisted and shown by `monday status`, because an agent's final message is not evidence.

## What "model-agnostic" means here

- The core (`core/method.md`, `core/roles/`, `core/monday.py`) never names a platform or a model. A test enforces this.
- Roles are expressed as abstract tiers: explorer = fast, implementer = standard, reviewer = deep. Each adapter maps them to concrete models in one place.
- Adapters only translate. Hooks call the same CLI, and the role agents are one-line pointers to the core role files, so there are no divergent copies of the rules.
- Adding a platform means adding an `adapters/<name>/` folder and one entry in `ADAPTERS` in `core/monday.py`.

## Integrations

| | Claude Code (2.1.301) | Antigravity CLI `agy` (1.4.2, 1.4.3) |
|---|---|---|
| Implemented | `CLAUDE.md` → `@AGENTS.md`, `SessionStart`/`PreToolUse`/`Stop` hooks, `monday-explorer`/`-implementer`/`-reviewer` agents with per-role model and tools | Native `AGENTS.md`, `.agents/hooks.json` (`SessionStart`/`PreToolUse`/`Stop`), the same three agents in `.agents/agents/` |
| Tested with real agents (headless) | Context loading, scope guard, stop hook, closure decided by verification (including a forced false "all checks pass" report), role agent loading | Same checks |
| Not yet validated | The permission dialog in interactive sessions | Antigravity IDE (only the CLI was tested); per-agent model and tool restrictions |

Platform differences that were measured, not assumed:

- In `agy`, a `PreToolUse` hook answering `ask` is auto-approved in `accept-edits` mode, so Monday uses `deny` there.
- `agy` changed its tool catalogue without changing its version: the same 1.4.2 offered `edit_file`/`Path` instead of `write_to_file`/`TargetFile`. The Antigravity guard therefore watches every non-read tool and checks the paths in its arguments, instead of relying on a list of tool names.
- In our runs, `agy -p` returned the model's last text with `status: SUCCESS`, even when a hook had blocked it afterwards, and no hook could change that output. Judge the outcome with `monday status` or `monday done`, never with the agent's message.

## Getting started

Requirements: Python 3 (standard library only; 3.8 or later should work, but only 3.14 has been tested), Bash and git. Git is strongly recommended: without it, scope and review checks need manual evidence. To use the adapters you need Claude Code and/or the Antigravity CLI (`agy`); Monday itself does not need either.

Clone Monday **outside** your project (it is only the installer's source; the project gets its own copy in `.monday/`):

```bash
tmp="$(mktemp -d)"
git clone --depth 1 --branch v1.0.0 https://github.com/Admes7a431-2408/Monday_Harness.git "$tmp/monday"
python3 "$tmp/monday/core/monday.py" install /path/to/your/project --dry-run   # preview: lists every file it would create or merge
python3 "$tmp/monday/core/monday.py" install /path/to/your/project             # Claude Code + Antigravity
python3 "$tmp/monday/core/monday.py" install /path/to/your/project --platform claude   # or one platform: claude | antigravity
cd /path/to/your/project
./init.sh                             # project checks + harness integrity
python3 .monday/monday.py check       # harness integrity only: managed files, hooks, features.json
python3 .monday/monday.py status      # version, features, last verification
```

Then fill in the project map in `AGENTS.md` and your lint and test commands in `init.sh` (`QUICK_CHECKS`, `FULL_CHECKS`), commit the result, and start a new agent session so the platform loads `AGENTS.md` and the hooks. The clone in `$tmp` can be deleted.

- **Installation never overwrites your files.** An existing `AGENTS.md`, `CLAUDE.md`, `.claude/settings.json` or `.agents/hooks.json` is merged: Monday's block or hooks are added and everything else is kept. An existing `init.sh`, `features.json`, `docs/architecture.md` or `progress/*` file is left untouched. Uncommitted changes are not affected: install only writes the files it lists.
- **Notices.** Install prints `AVISO:` lines for things it does not manage. Examples: an `init.sh` of your own that does not run `python3 .monday/monday.py check` (add that line, or `./init.sh` will not validate the harness), and Monday 0.9 leftovers (see below).
- **Idempotent.** Running the same install again reports `sin cambios` ("no changes").
- **Updating** means running `install` again from a newer Monday checkout. If a managed file was edited inside the project, the update stops (or use `--force`).
- **Uninstalling.** Every install keeps a backup in `.monday/backups/`. `python3 .monday/monday.py rollback` undoes the last install or update, and `python3 .monday/monday.py rollback --all` uninstalls Monday completely: created files are removed and merged files are restored to their original bytes. Files you changed after installing (for example your `features.json` or `progress/history.md`) are kept unless you pass `--force`. Add `--dry-run` to preview.

### Asking an agent to install it

In the target project, give Claude Code or Antigravity an instruction like this:

> Install Monday in this project from https://github.com/Admes7a431-2408/Monday_Harness following its README ("Getting started"). Clone it into a temporary directory outside this project, run the install with `--dry-run` first and show me the plan, then install, run `./init.sh` and `python3 .monday/monday.py check`, and report every `AVISO:` line. Do not commit.

The agent needs permission to run `git clone` and `python3`. After installing, start a new session: the instructions and hooks are loaded when a session starts.

### Upgrading from Monday 0.9 or AgentForge

Monday 0.9 (tag `v0.9.0`) and AgentForge (tag `v0.1.0`) used a different mechanism. Their `install.sh` linked a global skill into `~/.claude/skills/` and `~/.gemini/config/skills/` (`monday` or `agentforge`), plus, with `--agents`, agents into `~/.claude/agents/` (`monday-reviewer`/`-scout`/`-worker` or `af-*`). Their projects had `.monday/CONTEXT.md`, `.monday/contracts/` and `.monday/reports/` (or `.agentforge/`). Monday 1.0 uses none of them.

1. Remove the global links, which would otherwise load the old method in every project: run `bash install.sh --uninstall --agents` from the old checkout those links point to (`readlink ~/.claude/skills/monday` or `readlink ~/.claude/skills/agentforge`; install's `AVISO:` lists every link it found). It only removes links to its own directory, and without `--agents` it leaves the agents in place. Alternatively, delete those symlinks by hand.
2. Install 1.0 as above. Install warns about the old project files and global links it finds, and never modifies them.
3. Move what is still useful into `features.json` and `progress/`, then delete the old files yourself.

### Everyday use

```bash
M="python3 .monday/monday.py"
$M status                 # current state, last verification result, next step
$M start F-001            # start a feature; fixes the diff base and the contract fingerprint
$M verify F-001           # run its criteria: PASS / FAIL / UNAVAILABLE / manual
$M scope F-001            # changed files vs. the feature's scope
$M review F-001 --verdict approve --by monday-reviewer
$M done F-001             # close it, only if all the evidence supports it
$M amend F-001 --reason "…"   # record a contract change (asks a human when hooks are active)
$M block F-001 --reason "…"   # stop and escalate
$M guard src/x.py         # may I write here? (manual fallback when hooks are unavailable)
```

A minimal feature:

```json
{
  "id": "F-001", "title": "Fix rounding of the invoice total", "status": "pending", "risk": "medium",
  "scope": ["src/billing/totals.py", "tests/billing/**"],
  "acceptance_criteria": [
    {"id": "AC1", "text": "The reported case fails before and passes after", "verify": "pytest -q tests/billing/test_totals.py"},
    {"id": "AC2", "text": "The invoice text reads well in the PDF"}
  ]
}
```

`AC2` has no `verify` command, so it is manual: `done` will require `--manual AC2="<evidence>"`.

## How Monday itself is verified

| Kind | What | Command |
|---|---|---|
| Deterministic | 51 unit and scenario tests: the eight validation scenarios, install/update/rollback, design integrity, regressions | `./init.sh` |
| Simulated | Hook behaviour with hand-built payloads in the format observed on each platform (part of the suite above) | `python3 -m unittest discover -s tests -v` |
| Release checks | Contract integrity, secrets and private-data audit, version coherence, preserved history | `bash tests/release_check.sh` |
| Clean-folder quick start | The commands in this README, from a fresh clone of the local repository or of a published URL and tag | `bash tests/quickstart.sh` · `bash tests/quickstart.sh https://github.com/Admes7a431-2408/Monday_Harness.git v1.0.0` |
| Real agents | 16 checks on both platforms, including adversarial runs. Not deterministic; it spends tokens and needs logged-in CLIs | `bash tests/e2e_adapters.sh` |

Monday is developed with Monday: this repository has its own `AGENTS.md`, `features.json` and `progress/`, and its completed features were closed with `monday done`, rejections included (see `progress/history.md`).

## Known limitations

- **The agent's final message is not controlled.** Platforms may show stale or false text as the result (verified in `agy -p`). Monday makes the real state visible (`status`, `history.md`) and refuses to close, but it cannot rewrite what the platform prints.
- **Stop hook:**
  - It blocks once per identical failure, to avoid loops.
  - It does not run when a platform terminates on its own; for example, `agy` print mode ends the run when it soft-denies a tool.
  - In Claude Code, if another `Stop` hook of yours blocks first, Monday only records the failure.
- **`amend` guard:** the hooks ask for permission on `monday.py amend`, but not when it is invoked through a shell alias (`$M amend`). The change is still recorded and invalidates any review.
- **`features.json` and `.monday/runtime/verification.json` are plain files.** Monday detects careless or shortcut edits (contract fingerprint, fresh re-verification in `done`). It does not stop a deliberate forgery.
- **Shell commands that write files** are not analysed by the scope guard; they are caught by the scope check at `done`. The same applies to an Antigravity tool that writes without exposing the path in a recognisable argument (names ending in `path`, `file`, `dir`, `uri`, or `filename`/`source`/`destination` holding a path-like value) or in a patch header. Writes inside the platform's own artifact directory are not guarded.
- **Antigravity headless:** an agent can only run `./init.sh` if you add `command(./init.sh)` to `permissions.allow` in `~/.gemini/antigravity-cli/settings.json`. Monday does not change global settings.
- **Out-of-scope writes in Antigravity are denied, not asked**, because `ask` is not reliable there. A human widens the scope or performs the action.
- **Monorepos:** with Monday installed in a subdirectory, scope only sees that subdirectory. Files ignored by git do not count as changes.
- **Platforms:** tested on Linux only. macOS should work (Bash + Python) but is untested; Windows is not supported.
- **Language:** the operating instructions (the `AGENTS.md` block, `core/method.md`, roles) and the architecture records are written in Spanish, the author's working language.

## Evolving and contributing

The backlog lives in [`features.json`](features.json). Open items include a Codex CLI adapter, validation on the Antigravity IDE, and the `amend` alias guard.

To contribute, work the Monday way:

1. Describe the change as a feature with executable acceptance criteria.
2. Keep `./init.sh` green.
3. Close it with `monday done`.

New rules are added only with evidence of a repeated problem; see `core/method.md` §8. Architecture decisions and their discarded alternatives are in [`docs/architecture.md`](docs/architecture.md). The original AgentForge audit is in [`progress/exploration_logs.md`](progress/exploration_logs.md). Issues and pull requests are welcome.

## Repository layout

```text
core/            model-agnostic core (copied into <project>/.monday/)
  monday.py      CLI: state, verification, guards, hooks, install/rollback
  method.md      method: modes, task cycle, delegation, verification, governance, memory
  roles/         explorer · implementer · reviewer
  policy.json    protected paths and commands that require human approval
  templates/     project seeds
adapters/        claude-code · antigravity
tests/           deterministic tests, release checks, real-agent validation
docs/            architecture and decisions
```

## Acknowledgements

- The design guide behind this version ([`Arquitectura Óptima de Arnés para Agentes IA.md`](Arquitectura%20Óptima%20de%20Arnés%20para%20Agentes%20IA.md), in Spanish) synthesises harness-engineering ideas presented by Benjamín Cordero and BettaTech.
- AgentForge drew conceptual inspiration from [obra/superpowers](https://github.com/obra/superpowers), [mattpocock/skills](https://github.com/mattpocock/skills), [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills), [nobodyohm-web/claude-code-model-router](https://github.com/nobodyohm-web/claude-code-model-router), [BearGare/claude-skills](https://github.com/BearGare/claude-skills) and [shaaz1000/claude-router](https://github.com/shaaz1000/claude-router). Some of those ideas survive in Monday: evidence before claims, self-contained briefs, status protocol, and two-axis independent review.

Mentioning these projects is a technical acknowledgement. It does not imply sponsorship, endorsement or affiliation.

## License

[MIT](LICENSE) © 2026 Admes.
