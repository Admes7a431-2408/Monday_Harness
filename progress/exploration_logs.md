# Registro de exploración

Hallazgos que deben sobrevivir a la sesión. Cada entrada: fecha · feature · tema; hechos con fuente (`archivo:línea`, comando, URL). Marca las inferencias como tales.

## 2026-10-18 · M-001 · Auditoría de AgentForge (fuente histórica de Monday)

Fuente: `git clone https://github.com/Admes7a431-2408/AgentForge` (solo lectura, en scratchpad). Tags `v0.1.0` (2026-10-07, «AgentForge») y `v0.9.0` (2026-10-18, «transmutación a Monday»). 13 commits; ~5.200 líneas, de las cuales 1.512 son tests y 697 `scripts/monday.py`.

**Hechos observados**

- Forma: una *skill* global (`SKILL.md` + `methodology/` con 7 archivos, ~500 líneas) enlazada por symlink en `~/.claude/skills/monday` y `~/.gemini/config/skills/monday`; memoria por proyecto en `.monday/{CONTEXT.md,contracts/,reports/}`.
- Clasificación en 3 ejes: level L0–L5, tier FAST/STANDARD/DEEP/MAX, risk low–critical; 8 quality gates (G1–G8) seleccionadas por una matriz level×risk (`methodology/quality-gates.md`).
- Contratos YAML (`task.yaml`, ~40 campos posibles) y reportes YAML con `verification_results` autodeclarados; `monday.py validate` comprueba su *estructura*, `check-scope` compara el diff git con `allowed_files` (G5).
- Tooling: Python + PyYAML; `install.sh` de 342 líneas (symlinks, `--purge-legacy`, `--check`).
- Subagentes Claude `monday-scout|worker|reviewer` con `model`/`tools` en frontmatter.
- Validación real con agentes (AD-009): el executor declaró G5 `pass` de memoria; el orquestador escribió contratos con comandos inventados; `agy -p` termina con `SUCCESS` vacío si se deniega una acción.
- Sin hooks (AD-006): todo el cumplimiento era conductual salvo `check-scope` a posteriori.

**Diagnóstico (inferencias)**

- La intención es sólida y estable entre releases: confianza basada en evidencia, alcance controlado, delegación por coste cognitivo y portabilidad entre plataformas.
- Complejidad accidental: 6 niveles + 4 tiers + 4 riesgos + 8 gates + matriz; contratos más largos que muchos cambios; la evidencia vive en reportes que el propio agente escribe, de modo que el script valida forma, no verdad.
- El estado del trabajo no estaba en ningún sitio: no había «tarea en curso», backlog ni historial recuperable fuera de contratos/reportes sueltos. La guía lo resuelve con `features.json` + `progress/`.
- La metodología global en `~/.claude/skills` hace que el proyecto dependa de la instalación de la máquina; contradice «el repositorio es el sistema».

**Veredicto por componente**

| Componente AgentForge | Veredicto | En Monday 1.0 |
|---|---|---|
| Principios P1–P12 | Transformar | 8 reglas de oro en `AGENTS.md`; el detalle operativo en `core/method.md` |
| Levels L0–L5 | Transformar | 3 modos: directo / registrado / orquestado |
| Tiers FAST/STANDARD/DEEP/MAX | Transformar | El tier lo fija el rol; el mapeo a modelos vive solo en cada adaptador. MAX descartado |
| Risk low–critical | Simplificar | low / medium / high; lo «critical» es una puerta humana por tipo de acción (`policy.json`) |
| Gates G1–G8 + matriz | Transformar | `monday done` ejecuta: `init.sh`, criterios, alcance y revisión (si risk high) |
| Contratos `task.yaml` | Fusionar | La entrada de `features.json` es el contrato (scope + criterios ejecutables) |
| Reportes `report.yaml` | Descartar | La evidencia la produce `monday done` y la registra en `progress/history.md` |
| Protocolo de estados DONE/…/FAILED + brief | Conservar | `core/method.md` §Delegación |
| `check-scope` (G5) | Conservar y endurecer | `monday scope` + `monday guard` en hooks (preventivo) |
| Interface Integrity Gate | Descartar como mecanismo | Se expresa como criterio de aceptación o eje del revisor |
| `cap status` / `catalog.yaml` (4 estados) | Descartar | Matriz de capacidades y alternativas en `core/method.md`; estado `UNAVAILABLE` en verificaciones |
| `routing/profiles.yaml`, posturas | Descartar | Frontmatter de los agentes de cada adaptador |
| `CONTEXT.md` / glosario / ADR | Fusionar | `docs/architecture.md` del proyecto |
| Subagentes `monday-*` | Transformar | `monday-explorer|implementer|reviewer`, cuerpo = puntero a `.monday/roles/` |
| Instalación por symlink global | Descartar | Copia versionada en `<proyecto>/.monday/` con manifiesto de hashes, backup y rollback |
| PyYAML | Descartar | Python 3 stdlib + JSON |
| `--purge-legacy`, `af.py` shim, migración `.agentforge/` | Descartar | Específicos de la transición AgentForge→Monday |

## 2026-10-18 · M-001 · Capacidades reales de las plataformas (máquina local)

- Claude Code 2.1.301: lee `CLAUDE.md` (no `AGENTS.md`; se usa import `@AGENTS.md`), agentes en `.claude/agents/*.md`, hooks en `.claude/settings.json` (`SessionStart`, `PreToolUse` con `permissionDecision`, `Stop`/`SubagentStop` con `decision: block`).
- Antigravity CLI `agy` 1.4.2 (cadenas embebidas en el binario, `strings`): lee `AGENTS.md`/`GEMINI.md` y `.agents/rules/*.md`; agentes Markdown en `.agents/agents/`; hooks de workspace en `<workspace>/.agents/hooks.json` con eventos `SessionStart`, `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop`. `PreToolUse` recibe `{"toolCall":{"name","args"}}` y responde `{"decision":"allow|deny|ask|force_ask"}`; `Stop` responde `{"decision":"continue"}` para impedir la parada; el `cwd` del hook es el directorio de `hooks.json`. Nombres de herramientas de edición (inferencia, a confirmar): `write_to_file`, `replace_file_content`, `multi_replace_file_content` con arg `TargetFile`; comandos `run_command` con `CommandLine`.
- Python 3.14 + PyYAML disponibles; `jq` sí; `shellcheck` no.
- **Confirmado con `agy -p` (gemini-3.8-flash-low, `--mode accept-edits`, workspace de prueba):** `AGENTS.md` del workspace se carga; `SessionStart` con `injectSteps.systemMessage` llega al modelo; `PreToolUse` recibe `write_to_file` con `args.TargetFile` (ruta absoluta) y `run_command` con `args.CommandLine`; `Stop` recibe `terminationReason`, `executionNum` (sin flag equivalente a `stop_hook_active`).
- **Semántica de la respuesta de `PreToolUse` en agy (observada):** sin stdout = neutral (se aplica la política normal); `{}`, `{"decision":""}` o salida no-JSON = **denegado**; `{"decision":"ask"}` se autoaprueba en modo `accept-edits`. Consecuencia: el adaptador no imprime nada para «sin objeción» y usa `force_ask` para pedir permiso.
