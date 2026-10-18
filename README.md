# Monday

Harness agnóstico para agentes de IA: un flujo de trabajo consistente y resultados **verificables**, sea cual sea el modelo o el entorno (Claude Code, Antigravity, …).

Monday no confía en lo que el agente dice: confía en lo que se puede ejecutar. Una tarea solo se cierra cuando `monday done` ha ejecutado las comprobaciones del proyecto, los criterios de aceptación, el control de alcance contra el diff de git y, si el riesgo lo exige, una revisión independiente anclada a ese mismo diff.

## De AgentForge a Monday

Monday nació como **AgentForge**, un experimento para aumentar la confianza en el trabajo de los agentes y mantener el mismo flujo con distintos modelos. Sus releases (`v0.1.0`, `v0.9.0`, en [Admes7a431-2408/AgentForge](https://github.com/Admes7a431-2408/AgentForge)) quedan como testigos de esa evolución: contratos, gates de calidad, delegación por coste cognitivo y adaptadores por plataforma.

Monday 1.0 conserva esa intención y la reconstruye con menos piezas: la memoria vive en el repositorio y no en la conversación, los contratos son ejecutables, y las garantías importantes las aplica un CLI o un hook, no la buena voluntad del modelo. El análisis de qué se reutilizó, transformó o descartó está en [`progress/exploration_logs.md`](progress/exploration_logs.md) y las decisiones en [`docs/architecture.md`](docs/architecture.md).

## Cómo funciona

Al instalar Monday en un proyecto se crean:

| Archivo | Para qué |
|---|---|
| `AGENTS.md` | Punto de entrada para cualquier agente (<200 líneas): protocolo, reglas de oro y mapa del proyecto |
| `init.sh` | Validación rápida (`./init.sh`) y completa (`./init.sh --full`) del proyecto |
| `features.json` | Backlog: alcance y criterios de aceptación ejecutables de cada tarea |
| `progress/current.md` · `exploration_logs.md` · `history.md` | Tarea en curso · hallazgos que persisten · historial con evidencia |
| `docs/architecture.md` | Convenciones, decisiones y reglas aprendidas |
| `.monday/` | Núcleo gestionado (método, roles, política, CLI); no se edita en el proyecto |
| Adaptadores | `CLAUDE.md` + `.claude/` (Claude Code), `.agents/` (Antigravity): hooks y agentes por rol |

El agente elige un **modo** según complejidad y riesgo: *directo* (cambio claro y local), *registrado* (feature con criterios) u *orquestado* (exploración delegada, implementación con brief y revisión independiente). Los detalles están en [`core/method.md`](core/method.md).

Los hooks de cada plataforma añaden tres garantías: el estado del proyecto se inyecta al iniciar sesión, las escrituras fuera del alcance de la feature en curso y los comandos irreversibles se interceptan antes de ejecutarse, y el agente no puede terminar con cambios y `init.sh` en rojo sin corregirlo o explicarlo.

## Requisitos

- Python 3 (solo biblioteca estándar; probado con 3.14, requiere ≥ 3.8), Bash.
- git (recomendado: sin git, el alcance y la revisión exigen evidencia manual).
- Claude Code y/o Antigravity CLI para los adaptadores. En Antigravity headless (`agy -p`), para que el agente pueda ejecutar `./init.sh` hay que añadir `command(./init.sh)` a `permissions.allow` de `~/.gemini/antigravity-cli/settings.json` (configuración global; Monday no la toca).

## Instalar, actualizar y revertir

```bash
git clone <este repositorio> monday
python3 monday/core/monday.py install /ruta/al/proyecto --dry-run     # ver qué haría
python3 monday/core/monday.py install /ruta/al/proyecto               # ambas plataformas
python3 monday/core/monday.py install /ruta/al/proyecto --platform claude   # solo una
```

- **Nunca sobrescribe** archivos del proyecto: `AGENTS.md`, `CLAUDE.md` y la configuración de la plataforma se fusionan (se añade el bloque o los hooks de Monday y se conserva lo demás).
- **Actualizar** = volver a ejecutar `install` desde una versión nueva de Monday. Si alguien editó un archivo gestionado en el proyecto, la actualización se detiene (o `--force`).
- **Revertir:** cada instalación guarda un backup en `.monday/backups/`. `python3 .monday/monday.py rollback` deshace la última; `rollback --all` desinstala por completo. Los archivos que el proyecto modificó después de instalar (p. ej. `features.json` con trabajo) se conservan salvo `--force`.

Después de instalar: completa el mapa de `AGENTS.md`, configura `QUICK_CHECKS`/`FULL_CHECKS` en `init.sh` y ejecuta `./init.sh`.

## Uso

```bash
M="python3 .monday/monday.py"
$M status                 # estado actual y siguiente paso (también lo inyecta el hook de inicio)
$M check                  # integridad del harness (lo llama init.sh)
$M start F-001            # empieza una feature y fija la base del diff
$M verify F-001           # ejecuta los criterios: PASS / FAIL / UNAVAILABLE / manual
$M scope F-001            # archivos cambiados frente al alcance
$M review F-001 --verdict approve --by monday-reviewer
$M done F-001             # cierra solo si todo lo anterior lo respalda
$M amend F-001 --reason "…"   # cambio de risk/scope/criterios: queda en el historial
$M block F-001 --reason "…"
$M guard src/x.py         # ¿puedo escribir aquí sin pedir permiso? (alternativa sin hooks)
```

Una feature mínima:

```json
{
  "id": "F-001", "title": "Arreglar el redondeo del total", "status": "pending", "risk": "medium",
  "scope": ["src/billing/totals.py", "tests/billing/**"],
  "acceptance_criteria": [
    {"id": "AC1", "text": "El caso reportado falla antes y pasa después", "verify": "pytest -q tests/billing/test_totals.py"},
    {"id": "AC2", "text": "El texto de la factura se lee bien en el PDF"}
  ]
}
```

`AC2` no tiene `verify`: es manual y `done` exigirá `--manual AC2="<evidencia>"`.

## Compatibilidad

Comprobada con agentes reales (`tests/e2e_adapters.sh`) en Claude Code 2.1.301 y Antigravity CLI 1.4.2: carga de `AGENTS.md`, inyección de estado, guarda de alcance, hook de parada y carga de los agentes por rol. Pendiente de validación manual: el diálogo de permiso en sesiones interactivas, Antigravity IDE y la restricción de herramientas por agente en Antigravity. Tabla completa en [`docs/architecture.md`](docs/architecture.md#compatibilidad-comprobada).

Otra plataforma (Codex, Cursor…) se añade con una carpeta en `adapters/` y una entrada en `ADAPTERS` de `core/monday.py`; el núcleo no cambia.

## Probar Monday desde cero

```bash
./init.sh                                   # harness de este repo + 48 pruebas (escenarios S1–S8, distribución, diseño, regresiones)
bash tests/install_roundtrip.sh             # instalar → init.sh → reinstalar → rollback --all deja el directorio vacío
bash tests/e2e_adapters.sh claude           # agentes reales (consume tokens; requiere sesión iniciada)
bash tests/e2e_adapters.sh antigravity
```

## Estructura del repositorio

```text
core/            núcleo agnóstico (se copia a <proyecto>/.monday/)
  monday.py      CLI: estado, verificación, guardas, hooks, install/rollback
  method.md      método: modos, ciclo, delegación, verificación, gobernanza, memoria
  roles/         explorer · implementer · reviewer
  policy.json    rutas protegidas y comandos que requieren permiso humano
  templates/     semillas del proyecto
adapters/        claude-code · antigravity (hooks + agentes-puntero)
tests/           pruebas deterministas y validación e2e
docs/            arquitectura y decisiones
```

Este repositorio usa Monday para sí mismo: `.monday` apunta a `core/` y su trabajo se registra en `features.json` y `progress/`.

## Limitaciones conocidas

- Los hooks interceptan las herramientas de edición y los comandos de `policy.json`; un comando de shell que escribe archivos fuera de alcance no se detecta hasta `monday done`.
- `features.json` es un archivo editable: Monday detecta incoherencias de forma, no la mala fe. El autor de una revisión (`--by`) es declarativo.
- El texto final de un agente no es evidencia: `agy -p` puede devolver un texto anterior a un bloqueo con `status: SUCCESS`. Juzga el resultado con `monday status` (línea «Verificación») o `monday done`.
- En Antigravity, lo fuera de alcance se **deniega** (no hay un «preguntar» fiable en modo `accept-edits`): el humano amplía el `scope` o ejecuta la acción.
- En un monorepo con Monday en un subdirectorio, el alcance solo mira ese subdirectorio, y los archivos en `.gitignore` no cuentan como cambios.
- Probado en Linux. macOS debería funcionar (Bash + Python); Windows no está soportado.

## Licencia

[MIT](LICENSE) © 2026 Admes.
