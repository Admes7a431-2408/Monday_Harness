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
- **Semántica de la respuesta de `PreToolUse` en agy (observada):** sin stdout = neutral (se aplica la política normal); `{}`, `{"decision":""}` o salida no-JSON = **denegado**; `{"decision":"ask"}` se autoaprueba en modo `accept-edits`. Consecuencia: el adaptador no imprime nada para «sin objeción»; para objetar usa `deny` (ver la entrada siguiente: `force_ask` también se autoaprueba).
- **Confirmado con `tests/e2e_adapters.sh` (2026-10-18; Claude Code 2.1.301 con haiku; agy 1.4.2 con gemini-3.8-flash-medium):** en `agy -p --mode accept-edits` tanto `ask` como `force_ask` se **autoaprueban** (README.md se modificó con la guarda disparada, ver `hooks.log`); solo `deny` bloquea. En `claude -p --permission-mode acceptEdits`, `permissionDecision: ask` deniega en headless (en interactivo pregunta al humano). `claude agents` lista sesiones en segundo plano, no definiciones; la carga de un agente de proyecto se comprueba con `claude -p --agent <nombre>` (y `agy -p --agent <nombre>`).
- **Comportamiento tras bloqueo del hook de parada (no determinista):** el mismo escenario terminó unas veces con el agente corrigiendo el bug y otras explicando el fallo; ambas salidas cumplen el diseño («corrige o explica»).

## 2026-10-18 · M-001 · Causa raíz del fallo de AC4 en Antigravity

Fuentes: transcripción `~/.gemini/antigravity-cli/brain/7a94b426-…/.system_generated/logs/transcript_full.jsonl` y log `~/.gemini/antigravity-cli/log/cli-20261018_172849.log` de la ejecución fallida; sondas en el scratchpad con agy 1.4.2 (gemini-3.8-flash-low).

**Secuencia observada (hechos):**
1. Paso 4–6: el agente inserta el comentario y escribe su respuesta («No other changes were made…»).
2. Paso 7: el hook `Stop` de Monday bloquea con `continue` y el motivo (`init.sh` en rojo). **El hook funcionó.**
3. Pasos 8–18: el agente investiga; intenta leer `.monday/hooks/stop.sh`, `.gemini/hooks.json`, y lee la skill global **heredada de AgentForge** en `~/.gemini/config/skills/monday` (symlink a `~/Documentos/.Proyectos/AgentForge`, fuera de este proyecto).
4. Paso 19: `Print mode: soft-denying tool confirmation "ViewFile"` → la CLI termina en el acto.
5. `agy -p` devolvió como `response` el último texto del modelo (paso 6, **anterior al bloqueo**) y `status: SUCCESS`.

**Capacidades comprobadas de agy (sondas):**
- Q1: tras un `continue` del hook `Stop`, una terminación por soft-deny en modo print **no vuelve a invocar `Stop`** (un único evento `stop` registrado) y la `response` concatena el texto previo.
- Q2: ningún hook altera la salida de `agy -p`: `PostInvocation` con `injectSteps` (`userMessage`, `systemMessage`, `ephemeralMessage`) y `terminationBehavior: terminate` añade pasos a la transcripción pero `response` sigue siendo el último texto del modelo y `status` sigue `SUCCESS`. El payload real de `PostInvocation` no incluye `modelOutput`.

**Conclusión:** el componente que dejó llegar el informe contradictorio es la salida de `agy -p` (texto del modelo + `SUCCESS`), que Monday no puede controlar desde el adaptador. Ninguna corrección dentro de la plataforma lo garantiza; la barrera determinista debe estar en el límite de integración: estado de verificación persistido y comunicado por Monday, y cierre decidido solo por verificación fresca. La prueba e2e aceptaba el texto del modelo como evidencia («o informó del fallo»): ese era el punto débil del propio criterio de prueba.

**Contaminación del entorno (fuera de alcance, requiere decisión humana):** `~/.claude/skills/monday` y `~/.gemini/config/skills/monday` siguen enlazando a AgentForge; los agentes de la máquina descubren esa metodología antigua además de la de Monday.
- **Primera e2e tras la corrección (2026-10-18 18:37):** 14/16. En `antigravity/adversarial` el agente, siguiendo el protocolo de `AGENTS.md`, intentó `./init.sh` antes de editar; el modo print lo soft-denegó (no está en la allowlist global de agy) y la ejecución terminó **sin cambios** (transcripción `brain/34e5132f-…`). No hubo `Stop` porque no había nada que verificar; Monday informó «Verificación: ninguna registrada — sin evidencia no hay éxito» y `done` rechazó. La prueba solo aceptaba ROJO/DESACTUALIZADA: se amplió a «ninguna» (también no-éxito) y la precondición «el agente dejó cambios» se trata con un reintento y, si no se cumple, UNAVAILABLE (nunca PASS).
- **Comandos en `agy -p` (sondas 2026-10-18):** un `PreToolUse` con `{"decision":"allow"}` **no** evita que el modo print deniegue un `run_command` fuera de la allowlist global; `--mode auto` tampoco. La denegación termina la ejecución. Consecuencia: en Antigravity headless el paso de protocolo `./init.sh` solo es ejecutable si el usuario añade `command(./init.sh)` a `~/.gemini/antigravity-cli/settings.json` (configuración global: decisión humana). Sin eso, Monday sigue protegiendo el cierre (`done`, `status`), pero el agente no puede autoverificarse.

## 2026-10-19 · M-005 · Catálogo de herramientas variable en agy

- `monday done M-005` rechazó AC2: en `antigravity` la escritura fuera de alcance pasó en las dos tandas. Transcripción `brain/588ab99b-…`: agy 1.4.2 (sin cambio de versión) ofreció `read_file`/`edit_file` con argumento `Path` en lugar de `view_file`/`write_to_file` con `TargetFile`. El matcher del adaptador y la tabla de herramientas de escritura no incluían `edit_file`: la guarda no se ejecutó.
- Herramientas de escritura nombradas en el binario: `write_to_file`, `replace_file_content`, `multi_replace_file_content`, `edit_file`, `write_file`, `create_file`, `delete_file`, `apply_patch`, `edit_notebook`. Recuento en transcripciones locales: `view_file` 405, `run_command` 244, `write_to_file` 44, `read_file` 40, `replace_file_content` 37, `edit_file` 6.
- Corrección: matcher `*` y guarda por argumentos (claves que terminan en path/file/dir/uri y cabeceras de parche) para toda herramienta que no sea de lectura; falla cerrada ante herramientas nuevas.
- **Validación real tras la corrección (2026-10-19):** e2e antigravity 8/8; en la prueba de alcance agy ofreció una tercera variante (`read_file` + `write_file`), ausente de toda lista previa, y la guarda genérica la denegó (`hooks.log`/transcripción).
