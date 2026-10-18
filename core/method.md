# Monday — Método

Procedimientos que desarrollan las reglas de oro de `AGENTS.md`. No las repite: si algo aquí parece contradecirlas, mandan ellas. Léelo cuando trabajes en modo **registrado** u **orquestado**; en modo directo basta `AGENTS.md`.

Comandos: `M=python3 .monday/monday.py` (en el repositorio de Monday, `.monday` apunta a `core/`).

## 1. Elegir el modo

Decide por **complejidad** (cuánto hay que entender y coordinar) y **riesgo** (qué cuesta equivocarse), no por el tamaño del texto que te pegaron. Ante la duda en el riesgo, elige el más alto; ante la duda en la complejidad, empieza ligero y sube si aparece evidencia (anúncialo). Nunca bajes en silencio.

| Riesgo | Señales |
|---|---|
| low | Local, reversible, cubierto por tests |
| medium | Cambia comportamiento visible, varios módulos o código sin tests |
| high | Seguridad, datos persistentes, dinero, migraciones, APIs públicas, concurrencia |

Las acciones irreversibles o con efectos fuera del workspace no son un nivel de riesgo: son **puertas humanas** (§5) en cualquier modo.

| Modo | Cuándo | Qué exige |
|---|---|---|
| Directo | Cambio claro y local, riesgo low, cabe en pocos pasos | Hacerlo, ejecutar la comprobación relevante y decir qué cambió y cómo se verificó |
| Registrado | Criterios de aceptación no obvios, varios pasos, riesgo medium, o el usuario quiere seguimiento | Feature en `features.json` → `start` → trabajo → `done` |
| Orquestado | Hay que explorar antes de diseñar, varias unidades de trabajo, o riesgo high | Registrado + exploración delegada + implementación con brief + revisión independiente |

## 2. Ciclo de una feature (registrado y orquestado)

1. **Definir.** Añade o ajusta la entrada en `features.json`: `id`, `title`, `status: pending`, `risk`, `scope` (globs de lo que se puede tocar; concretos, no `**`), `acceptance_criteria` (cada uno con `id`, `text` y, si es posible, `verify`: un comando que **pueda fallar** si el criterio no se cumple). Un criterio sin `verify` es manual y exigirá evidencia explícita. Opcional: `depends_on`, `review_required`, `description`.
2. **Comprobar el contrato contra el repo.** Los comandos de `verify` existen y se ejecutan; las rutas de `scope` existen o son las que se crearán. Ejecútalos una vez: si ya pasan antes del cambio, no demuestran nada (salvo que sean de regresión).
3. **Empezar.** `$M start <id>` fija la base del diff. Escribe el plan en `progress/current.md` (pasos → cómo se verifica cada uno).
4. **Explorar** si hace falta (§3). Los hallazgos que deban persistir van a `progress/exploration_logs.md`.
5. **Implementar** en pasos pequeños; actualiza «Estado y próximos pasos» de `current.md` al completar cada paso o antes de una pausa larga.
6. **Verificar** con `$M verify <id>` y `$M scope <id>` mientras iteras.
7. **Revisar** (obligatorio si `risk: high` o `review_required`): revisión independiente (§3), registrada con `$M review`.
8. **Cerrar** con `$M done <id>`: ejecuta `./init.sh` (`--full` si el riesgo es medium o high), los criterios, el alcance, la revisión y comprueba que el contrato no cambió desde `start`. Si rechaza, no hay éxito: corrige o bloquea. Antes, rellena «Resumen» en `current.md`; `done` lo mueve a `history.md`.

Si el contrato (risk, scope, criterios) debe cambiar durante el trabajo, edítalo y registra el cambio con `$M amend <id> --reason "…"`: queda en el historial e invalida la revisión previa. Ampliar alcance o rebajar riesgo es decisión del humano.

Si no puedes continuar: `$M block <id> --reason "<qué bloquea · opciones · recomendación>"` y escala.

## 3. Roles y delegación

El **líder** es el agente que habla con el humano. Lee `features.json` y `current.md`, decide el modo, delega, integra y responde del resultado. Mantiene su contexto libre de lecturas masivas de código: eso lo hace el explorador.

| Rol | Tier | Permisos | Entregable | Definición |
|---|---|---|---|---|
| Explorador | FAST | Solo lectura | Hallazgos `archivo:línea` + archivos a tocar + riesgos | `.monday/roles/explorer.md` |
| Implementador | STANDARD | Escritura dentro de `scope` | Cambio + comandos ejecutados y su salida | `.monday/roles/implementer.md` |
| Revisor | DEEP | Solo lectura + ejecutar comprobaciones | Veredicto por ejes + hallazgos + reglas propuestas | `.monday/roles/reviewer.md` |

El tier es abstracto; cada adaptador lo traduce a un modelo concreto.

**Cuándo delegar.** Delega lo que consume mucho contexto y poco razonamiento (búsquedas amplias, muchos archivos, cambios repetitivos ya decididos) y la revisión independiente. Hazlo tú si cabe en pocos pasos o depende de mucho contexto de la conversación: escribir el brief costaría más que hacerlo.

**Brief** (todo encargo; el subagente no ve tu conversación):

```
Rol: <explorer|implementer|reviewer> — lee .monday/roles/<rol>.md
Feature: <id> (features.json) · Objetivo: <una frase verificable>
Contexto: <rutas a leer: exploration_logs, docs/architecture.md, archivos clave>
Alcance: <scope de la feature o "solo lectura">
Hecho cuando: <criterios y cómo comprobarlos>
Devuelve: STATUS + ≤15 líneas
```

**Estados de respuesta** (primera línea): `DONE` · `DONE_WITH_CONCERNS` (hecho, con dudas explícitas) · `NEEDS_CONTEXT` (falta un dato concreto) · `BLOCKED` (no puede o no debe seguir: alcance, permisos, capacidad) · `FAILED` (lo intentó; adjunta la evidencia).

**Verifica lo delegado.** El informe de un subagente son afirmaciones, no hechos: mira el diff, reejecuta la comprobación o lee las citas `archivo:línea`. Después decide aceptar, reintentar con una corrección concreta (nunca igual), subir de tier o escalar. Tras dos correcciones fallidas sobre lo mismo, cambia de enfoque o escala al humano.

**Límites.** Los subagentes no delegan. Varios implementadores en paralelo solo con alcances disjuntos (o en worktrees separados). El revisor nunca es quien implementó. Quien corrige los hallazgos es el implementador, no el revisor.

## 4. Verificación y evidencia

- **Fresca:** ejecutada después del último cambio. **Observada:** el comando y su salida, no «debería funcionar». **Capaz de fallar:** una comprobación que no puede fallar ante el defecto no es evidencia.
- **Estados:** `PASS` (ejecutada y superada) · `FAIL` (ejecutada y fallida) · `UNAVAILABLE` (no se pudo ejecutar: falta herramienta o entorno) · `MANUAL` (comprobada por una persona o agente, con evidencia escrita). `UNAVAILABLE` nunca cuenta como éxito: o se aporta evidencia manual (`--manual AC2="…"`) o la feature no se cierra.
- **Rápida vs completa:** `./init.sh` (integridad del harness + checks rápidos) antes de escribir código; `./init.sh --full` (suite completa, e2e/UI) la ejecuta `done` al cerrar features de riesgo medium/high.
- **Bugs:** primero un repro que falle; después el arreglo; el mismo repro pasa a ser test de regresión.
- **Al responder al humano:** di qué se ejecutó y qué no. «No verificado» dicho a tiempo vale más que un éxito ambiguo.

## 5. Gobernanza

**Autoridad**, de mayor a menor: el humano → reglas del proyecto (`AGENTS.md`, configuración de la plataforma) → la feature (`scope`, criterios) → el brief del líder (solo puede estrechar, nunca ampliar).

**Sin pedir permiso:** leer, buscar, editar dentro del alcance, ejecutar builds, tests y linters en modo comprobación.

**Puertas humanas** (detente y pregunta): borrar datos o trabajo ajeno, reescribir historia git, `push`/`merge`/`tag`/publicar/desplegar, instalar dependencias globales o cambiar configuración global, tocar secretos o credenciales, cambios de seguridad no previstos, escribir fuera del proyecto. `.monday/policy.json` lista los patrones que los hooks interceptan; es una red de seguridad, no un sustituto del criterio.

**Desviaciones.** Si resolver la tarea exige salir del `scope`: no lo hagas. Detente y escala con *qué encontraste · por qué bloquea · opciones · recomendación*. Ampliar el `scope` es una decisión del humano (o del líder si el humano se la delegó) y queda registrada en `features.json`. Lo que encuentres fuera de alcance (bugs ajenos, deuda) se anota en el resumen, no se arregla. Señales de deriva: necesitas la palabra «además» para explicar el cambio; editas un tercer grupo de archivos sin relación; un prerrequisito supera un tercio de la tarea.

**Preguntar bien:** una sola ronda, solo lo que bloquea, cada pregunta con tu recomendación. Los hechos los investigas tú.

## 6. Memoria

| Archivo | Responsabilidad única | Escribe |
|---|---|---|
| `features.json` | Requisitos, criterios, alcance y estado de cada feature | Líder; los campos de control los escribe `monday` |
| `progress/current.md` | Plan, estado y próximos pasos de la feature en curso | Líder (implementador si se le pide) |
| `progress/exploration_logs.md` | Hallazgos de exploración que deben persistir, con fuente | Líder, a partir del informe del explorador |
| `progress/history.md` | Registro de cierres, rechazos, bloqueos y revisiones con su evidencia | `monday` (+ el resumen de `current.md`) |
| `docs/architecture.md` | Convenciones, decisiones vigentes y reglas aprendidas | Líder, con aprobación humana si cambia una decisión |

No dupliques: si un dato ya vive en uno de estos archivos, enlázalo. No conviertas cada acción en documentación: escribe lo que otro agente necesitaría para continuar.

**Recuperación tras una interrupción.** `$M status` → lee `progress/current.md` → `git status`/`git diff` → `./init.sh` → continúa desde «Estado y próximos pasos». La conversación anterior no es necesaria; si lo fuera, la memoria estaba incompleta: corrígela.

## 7. Capacidades y alternativas

Monday no presupone que la plataforma ofrezca todo. Si falta una capacidad, usa la alternativa y dilo.

| Capacidad | Si falta |
|---|---|
| Subagentes | Ejecuta los roles en secuencia: explora y anota en `exploration_logs.md`, implementa leyendo solo esa entrada, y pide la revisión al humano o a otra plataforma en solo lectura (`--by human` / `--by <plataforma>`). |
| Hooks | Llama a mano a `$M guard <ruta>` antes de escribir fuera de lo obvio y a `$M guard --cmd "<cmd>"` antes de comandos dudosos; `done` comprueba el alcance a posteriori igualmente. |
| git | `scope` y `review` no pueden anclarse al diff: `done` exige `--manual scope="<lista de archivos tocados>"` (y `review="…"` si aplica). |
| Herramienta de un criterio (p. ej. Playwright) | El criterio queda `UNAVAILABLE`; ciérralo solo con evidencia manual o instala la herramienta con permiso. |
| Python 3 | `init.sh` falla con un mensaje claro: Monday no puede verificar nada sin su CLI. |

## 8. Automejora

Un fallo aislado se corrige, no se convierte en regla. Cuando el mismo tipo de error aparece **dos o más veces** en `progress/history.md` (rechazos, revisiones `changes_required`) o un revisor lo marca como patrón, el revisor propone una regla preventiva concisa y el líder la añade a «Reglas aprendidas» de `docs/architecture.md` citando la evidencia. Una regla que deja de aportar se retira. Los cambios al método de Monday se proponen en su repositorio, no se editan en `.monday/`.
