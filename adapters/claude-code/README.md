# Adapter: Claude Code

Solo diferencias de plataforma. La metodología está en `methodology/`; el mapeo tier → modelo en `routing/profiles.yaml` (`platforms.claude-code`).

## Capacidades reales

| Necesidad | Mecanismo | Nota |
|---|---|---|
| Cambiar modelo/esfuerzo de la sesión principal | `/model`, `/effort` (humano) o `claude --model --effort` al arrancar | Una skill no puede cambiarlo a mitad de sesión. No lo intentes: delega. |
| Ejecutar con otro tier | Herramienta **Agent** con `model` y `effort` | `model` del Agent tiene prioridad sobre el frontmatter del agente. Esta skill autoriza explícitamente fijar `effort` según el tier. |
| Restringir herramientas de un subagente | Agentes en `~/.claude/agents/*.md` (`tools`, `disallowedTools`) | Ver `agents/` de este adapter (`monday-*`). |
| Paralelizar | Varias llamadas Agent en el mismo turno; `run_in_background` | Si editan los mismos archivos: `isolation: "worktree"`. |
| Aislar ediciones | `isolation: "worktree"` | Revisa e integra el diff tú mismo. |
| Imponer permisos de un contrato en modo headless | `claude -p --allowedTools … --disallowedTools … --permission-mode …` | Traduce `permissions.commands` a reglas `Bash(<cmd>:*)`. En sesión interactiva es conductual (Nivel 1). |
| Gate de alcance | `python3 <Monday>/scripts/monday.py check-scope <contrato>` | Tras la ejecución. En contratos `schema: 1` audita automáticamente archivos ignorados no efímeros; `excluded_areas` se audita siempre. |

## Límites de Enforcement y Gobernanza

- **Límites de Enforcement:** Las restricciones de `permissions.commands` en sesiones interactivas son conductuales (Nivel 1). En modo headless (`claude -p`), las allowlists de herramientas (`--allowedTools`) imponen límites mecánicos de plataforma (Nivel 2), pero no constituyen un aislamiento de sistema operativo (chroot/sandbox).
- **Gate de alcance (`check-scope`):** Es una auditoría posterior (Nivel 4), no una prevención en tiempo real. Detecta violaciones tras la ejecución y antes de aceptar el entregable.
- **Ciclo de vida de capacidades:** Opera bajo 4 estados deterministas (`Disponible`, `Autorizada`, `Preparada`, `Activa`). Se auditan con `monday.py cap status`.
- **Límites del modo Gestionado:** En modo Gestionado, Claude Code no puede ampliar unilateralmente su alcance autorizado, relajar exclusiones de seguridad ni saltarse los human gates requeridos.
- **Aislamiento de memoria por proyecto:** El contexto, memoria y decisiones residen estrictamente en `.monday/` del repositorio local. El catálogo compartido de capacidades define herramientas disponibles pero jamás transfiere memoria, contexto ni secretos entre distintos proyectos.

## Delegar desde Claude Code

1. Decide el tier con [routing.md §3](../../methodology/routing.md#3-ejecutar-o-delegar).
2. Elige el agente por **función** (`profiles.yaml → agents`): explorar → `monday-scout`, ejecutar → `monday-worker`, revisar → `monday-reviewer`. Para lo que no encaja: `general-purpose`.
3. Pasa `model` y `effort` del tier (`python3 scripts/monday.py tier DEEP --platform claude-code`). Especifícalos siempre: omitirlos usa el frontmatter del agente (un valor de respaldo que puede quedar desfasado respecto a `profiles.yaml`) o hereda el de la sesión.
4. El prompt es el brief de [routing.md §4](../../methodology/routing.md#4-el-brief-todo-encargo-delegado) o un puntero al contrato.
5. Verifica el resultado (P9) antes de seguir.

Los subagentes de Claude Code pueden anidarse, pero Monday limita la profundidad a tres niveles ([routing.md §7](../../methodology/routing.md#7-límites-estructurales)); por eso `monday-worker` y `monday-reviewer` no reciben la herramienta Agent.

## Recibir un contrato de Antigravity (modo headless)

Antigravity invoca a Claude con un prompt autocontenido que apunta al contrato, p. ej.:

```
Usa la skill monday. Ejecuta el contrato .monday/contracts/MON-0012-x.yaml como executor.
Escribe el reporte en .monday/reports/MON-0012-x.yaml y responde solo STATUS + 5 líneas de resumen.
```

Claude actúa como Executor ([workflow.md](../../methodology/workflow.md#procedimiento-del-executor)): puede sub-delegar dentro de lo que permita `routing.allow_delegation`, y su respuesta final es `STATUS` + ruta del reporte. No ve la conversación de Antigravity: si el contrato no basta, responde `NEEDS_CONTEXT` con las preguntas concretas.

## Instalación

`install.sh` en la raíz enlaza la skill en `~/.claude/skills/monday` y, con `--agents`, crea enlaces simbólicos (SSOT, no copias) de `agents/*.md` en `~/.claude/agents/` (no sobrescribe archivos existentes). `install.sh --check` verifica, sin escribir nada, los enlaces, que cada `monday-*` apunte a un archivo legible cuyo frontmatter declare su `name:`, y la presencia de residuos obsoletos. `install.sh --purge-legacy` retira agentes obsoletos de `~/.claude/agents/` tras validar todos los objetivos y respaldar los archivos regulares. `install.sh --uninstall` elimina únicamente los enlaces que apuntan a Monday.
