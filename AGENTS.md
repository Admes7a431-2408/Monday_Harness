# AGENTS.md — Monday

Repositorio del harness Monday. Monday se gestiona con su propio protocolo: aquí `.monday` es un enlace a `core/` (no hay copia instalada).

<!-- monday:begin · bloque gestionado por Monday; `monday install` lo actualiza. Edita solo fuera del bloque. -->
## Protocolo Monday

Este proyecto usa el harness **Monday**: el repositorio es el sistema y la memoria vive en archivos, no en la conversación.

**Al empezar una sesión:** `python3 .monday/monday.py status` → lee `progress/current.md` → `./init.sh`. Si `init.sh` falla, detente y reporta el error antes de escribir código.

**Elige el modo** (detalle en `.monday/method.md` §1):

| Modo | Cuándo | Cierre |
|---|---|---|
| Directo | Claro, local, riesgo low | Di qué cambió y qué comprobación ejecutaste |
| Registrado | Varios pasos, criterios no obvios o riesgo medium | `monday done <id>` aceptado |
| Orquestado | Exploración previa, varias unidades o riesgo high | Igual + revisión independiente registrada |

**Reglas de oro**

1. **Evidencia o nada.** No digas «hecho», «arreglado» ni «funciona» sin un comando ejecutado después del último cambio y su salida. Lo no verificado se declara no verificado.
2. **`done` lo decide `monday`.** Una feature solo se marca `done` con `python3 .monday/monday.py done <id>` aceptado; nunca edites `status` a mano. Si lo rechaza, no hay éxito.
3. **Alcance.** Toca solo lo que exige el objetivo (`scope` de la feature). Lo que encuentres fuera se anota, no se arregla. Si necesitas salir, detente y escala.
4. **Puertas humanas.** Pide permiso antes de acciones irreversibles o con efectos fuera del proyecto: borrar datos, reescribir historia git, push/merge/tag, publicar, desplegar, dependencias o configuración globales, secretos.
5. **Piensa antes, cambia poco.** Enuncia qué vas a cambiar y por qué; si hay varias interpretaciones, dilo. La solución más simple que cumpla los criterios; cambios quirúrgicos, estilo existente.
6. **Delega con contrato.** Un subagente recibe un brief autocontenido (`.monday/method.md` §3) y devuelve `STATUS`. Su informe son afirmaciones: verifícalas tú. Sigues siendo responsable del resultado.
7. **La memoria se escribe.** Mantén `progress/current.md` al día en cada paso; lo que deba sobrevivir a la sesión va a su archivo (tabla abajo), no solo al chat.
8. **Errores que se repiten se convierten en reglas**, no los aislados (`.monday/method.md` §8).

**Memoria del proyecto**

| Archivo | Para qué |
|---|---|
| `features.json` | Backlog: id, alcance, criterios de aceptación verificables, estado |
| `progress/current.md` | Plan y próximos pasos de la tarea en curso |
| `progress/exploration_logs.md` | Hallazgos de exploración que deben persistir |
| `progress/history.md` | Cierres, rechazos y decisiones con su evidencia |
| `docs/architecture.md` | Convenciones, decisiones vigentes y reglas aprendidas (léelo antes de implementar) |

**Cuándo leer más:** modo registrado u orquestado → `.monday/method.md`. Al delegar → `.monday/roles/<rol>.md`. Comandos: `python3 .monday/monday.py --help`. `.monday/` lo gestiona Monday: no lo edites aquí.
<!-- monday:end -->

## Mapa del proyecto

| Ruta | Contenido |
|---|---|
| `core/` | Núcleo agnóstico: se copia tal cual a `<proyecto>/.monday/` |
| `core/monday.py` | CLI (Python 3, solo stdlib): estado, verificación, guardas, hooks, install/rollback |
| `core/method.md` · `core/roles/` | Método y roles (explorer, implementer, reviewer) |
| `core/policy.json` | Rutas protegidas y comandos que exigen permiso humano |
| `core/templates/` | Semillas del proyecto: `AGENTS.md` (bloque gestionado), `init.sh`, `features.json`, `progress/*`, `architecture.md` |
| `adapters/claude-code/` · `adapters/antigravity/` | Lo único específico de cada plataforma: hooks y agentes-puntero |
| `tests/test_monday.py` | Escenarios S1–S8, distribución e integridad del diseño |
| `tests/e2e_adapters.sh` | Validación con agentes reales (manual: requiere CLIs y sesión) |
| `docs/architecture.md` | Arquitectura, decisiones y reglas aprendidas |
| `Arquitectura Óptima de Arnés para Agentes IA.md` | Guía normativa de referencia |

## Reglas de este repositorio

- `core/method.md` y `core/roles/` no nombran plataformas ni modelos; eso vive solo en `adapters/` (lo comprueban los tests).
- Este bloque gestionado debe ser idéntico al de `core/templates/AGENTS.md` (lo comprueban los tests): edita la plantilla y cópialo aquí.
- Sin dependencias fuera de la biblioteca estándar de Python 3 y Bash.

## Comandos

- Rápido: `./init.sh` (harness + tests) · completo: `./init.sh --full`
- Tests: `python3 -m unittest discover -s tests -v`
