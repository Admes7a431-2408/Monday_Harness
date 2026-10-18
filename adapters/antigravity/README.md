# Adapter: Antigravity

Solo diferencias de plataforma. La metodología está en `methodology/`; el mapeo tier → modelo en `routing/profiles.yaml` (`platforms.antigravity`).

## Capacidades reales

| Necesidad | Mecanismo | Nota |
|---|---|---|
| Cambiar modelo de la sesión principal | `/model` (humano; persiste entre sesiones) | No se asume cambio por tarea. Para otro tier, delega. |
| Descargar contexto / paralelizar **con el mismo modelo** | Subagente nativo `invoke_subagent` — `TypeName: research` (solo lectura) o `self` (capacidad completa) | La documentación no garantiza modelo/esfuerzo por subagente: trátalos como *mismo tier*. Ideales para P11 (contexto caro, razonamiento barato). |
| Ejecutar con **otro tier** de Gemini | Subproceso headless: `agy -p "<brief>" --model <m> --effort <e> --mode plan --output-format json` | Valores con `python3 scripts/monday.py tier <TIER> --platform antigravity`. `--mode plan` = solo lectura; `--mode accept-edits` solo con contrato que autorice escribir. |
| Delegar la **ejecución** a Claude Code | Skill `claude`: `~/.gemini/config/skills/claude/scripts/ask-claude.sh [--write] --model <m> --effort <e> "<prompt>"` | Tier con `monday.py tier <TIER> --platform claude-code`. Es el handoff Orchestrator → Executor por defecto. |
| Seguimiento de tareas | Task artifact (`write_to_file`, `IsArtifact: true`, `ArtifactType: "task"`) | `manage_task` es para procesos en segundo plano, no checklists. |
| Supervisar subagentes | `/agents` (estado, pasos, permisos pendientes) | |
| Imponer permisos de comandos en headless | `~/.gemini/antigravity-cli/settings.json → permissions.allow` | Sintaxis `command(<binario> <subcomando>)`. Nunca `--dangerously-skip-permissions`. |
| Gate de alcance | `python3 <Monday>/scripts/monday.py check-scope <contrato>` | Tras recibir el resultado del executor. En contratos `schema: 1` audita automáticamente archivos ignorados no efímeros; `excluded_areas` se audita siempre. |

## Límites de Enforcement y Gobernanza

- **Límites de Sandbox y Plataforma:** El entorno sandbox de AGY aísla red y filesystem externo, pero los subagentes dentro de un mismo espacio de trabajo comparten visibilidad del árbol de trabajo. Las restricciones de `permissions.commands` son conductuales a menos que se configure `settings.json -> permissions.allow`.
- **Gate de alcance (`check-scope`):** Es una auditoría posterior determinista (Nivel 4), no una prevención en tiempo real. Detecta desviaciones una vez completada la tarea.
- **Ciclo de vida de 4 estados:** Las herramientas siguen los estados `Disponible`, `Autorizada`, `Preparada` y `Activa`. `monday.py cap status` reporta el estado verificado.
- **Límites del modo Gestionado:** En modo Gestionado, Antigravity no puede ampliar de forma autónoma su propio alcance ni rebajar salvaguardas o saltarse gates humanos definidos.
- **Aislamiento de memoria por proyecto:** El contexto, historial y memoria viven exclusivamente en `.monday/` del proyecto. El catálogo de capacidades centralizado jamás propaga memoria, contexto ni variables confidenciales entre repositorios distintos.

## Antigravity como Orchestrator

1. Aplica el [procedimiento del Orchestrator](../../methodology/workflow.md#procedimiento-del-orchestrator). Investiga con subagentes `research` cuando la exploración es amplia.
2. Escribe cada contrato en `.monday/contracts/<id>.yaml` y valídalo: `python3 <Monday>/scripts/monday.py validate <ruta>`.
3. Lanza al executor con un prompt corto que apunta al contrato (Claude no ve esta conversación):

   ```bash
   eval "$(python3 <Monday>/scripts/monday.py tier STANDARD --platform claude-code)"   # define $model y $effort
   ~/.gemini/config/skills/claude/scripts/ask-claude.sh --write --model "$model" --effort "$effort" \
     "Usa la skill monday. Ejecuta el contrato .monday/contracts/MON-0012-x.yaml como executor. \
      Escribe el reporte en .monday/reports/MON-0012-x.yaml y responde solo STATUS + 5 líneas."
   ```

   El tier sale de `routing.preferred_tier` del contrato. `--write` solo si el contrato autoriza escribir; nunca mientras tú editas los mismos archivos.
4. **Verifica** (P9): lee el reporte, `git diff`, ejecuta `verification.commands` y `monday.py check-scope <contrato> --base <commit de partida>`. Si la [matriz de gates](../../methodology/quality-gates.md#selección) exige G8, pide revisión independiente (Claude `monday-reviewer`/DEEP en solo lectura, o `agy` en `--mode plan` con un tier DEEP).
5. Integra, reporta y, si hubo señal, registra aprendizajes.

## Antigravity como Executor

Cuando el humano le da una tarea L0–L2 directamente, Antigravity la ejecuta él mismo siguiendo el [procedimiento del Executor](../../methodology/workflow.md#procedimiento-del-executor) y aplica la misma decisión ejecutar/delegar ([routing.md §3](../../methodology/routing.md#3-ejecutar-o-delegar)).

## Límites

- Las llamadas anidadas entre puentes están bloqueadas por `AGENT_BRIDGE_DEPTH` (Claude invocado por Antigravity no puede invocar a Antigravity). Encaja con el límite de tres niveles.
- Si la salida de un headless dice `[denegado en headless: …]`, faltó un permiso: repórtalo, no reintentes a ciegas.
- En `agy -p` una acción denegada puede terminar el turno **sin respuesta** (`status: SUCCESS`, `response` vacío). Comprueba `denied_actions` en el JSON. Para encargos de solo lectura, indica en el brief que use únicamente herramientas de lectura de archivos y no comandos de terminal (verificado 2026-10-07).

## Instalación

`install.sh` en la raíz enlaza la skill en `~/.gemini/config/skills/monday` (descubrimiento global de Antigravity). Para un solo proyecto, enlázala en `<proyecto>/.agents/skills/monday`.
