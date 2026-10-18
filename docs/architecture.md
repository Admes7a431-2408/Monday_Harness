# Arquitectura de Monday

Lectura obligatoria antes de cambiar Monday. Normativa: `Arquitectura Óptima de Arnés para Agentes IA.md` (la guía). Evidencia histórica: `progress/exploration_logs.md` (auditoría de AgentForge y capacidades reales de las plataformas).

## Visión en una página

```text
                 humano ── intención, puertas humanas, revisión si no hay subagentes
                   │
   AGENTS.md  ◄────┤  punto de entrada (<200 líneas): protocolo, reglas de oro, mapa
                   │
   líder (sesión principal de cualquier plataforma)
     │  lee features.json + progress/current.md; elige modo directo/registrado/orquestado
     ├── explorador (FAST, solo lectura) ─► hallazgos ─► progress/exploration_logs.md
     ├── implementador (STANDARD, escribe dentro de scope) ─► diff + comandos
     └── revisor (DEEP, solo lectura) ─► `monday review` (anclado al diff)
                   │
   monday done ── init.sh · criterios ejecutables · alcance (git) · revisión ─► history.md
                   │
   adaptadores ── hooks: SessionStart (estado) · PreToolUse (guarda) · Stop (init.sh)
```

**Núcleo (`core/`, se copia a `<proyecto>/.monday/`):** método (`method.md`), roles (`roles/`), política (`policy.json`), CLI determinista (`monday.py`) y plantillas. No nombra plataformas ni modelos (lo comprueba un test).

**Adaptadores (`adapters/<plataforma>/`):** solo traducen. Configuración de hooks que llama a `monday.py hook …`, agentes cuyo cuerpo es un puntero de una línea a `.monday/roles/<rol>.md` y el mapeo tier → modelo en su frontmatter. Añadir una plataforma = una carpeta + una entrada en `ADAPTERS` de `monday.py`.

**Proyecto:** `AGENTS.md`, `init.sh`, `features.json`, `progress/`, `docs/architecture.md` son del proyecto (semillas que Monday crea una vez y nunca sobrescribe), salvo el bloque gestionado de `AGENTS.md`.

## Mecanismos de confianza y su alcance real

| Mecanismo | Tipo | Qué garantiza | Límite |
|---|---|---|---|
| `monday done` | Determinista | No hay `done` sin `init.sh` (`--full` si risk ≥ medium), criterios, alcance, revisión (si aplica) y contrato sin cambios desde `start`; deja evidencia en `history.md` | Quien edita `features.json` y recalcula la huella a propósito puede falsearlo: detecta descuidos y atajos, no fraude deliberado |
| Criterios con `verify` | Determinista | Evidencia fresca ejecutada por `monday`, no declarada por el agente | La calidad del criterio depende de quien lo escribe (el método exige que pueda fallar) |
| Revisión anclada al diff | Determinista | Un cambio posterior a la revisión invalida el `approve` | Quién revisó (`--by`) es declarativo |
| Guarda `PreToolUse` | Plataforma | Escrituras fuera de `scope`, rutas protegidas y comandos de `policy.json` se interceptan antes de ejecutarse | Comandos de shell que escriben archivos no se analizan (los detecta `done`); los patrones son una red, no un sandbox |
| Hook `Stop` | Plataforma | El agente no termina con cambios y `init.sh` en rojo sin una nueva oportunidad de corregir; si aun así termina en rojo, queda en `history.md` | Bloquea una vez por fallo idéntico (anti-bucle); no controla el texto final que muestra la plataforma |
| Estado de verificación (`.monday/runtime/verification.json`) | Determinista | `status` y el inicio de sesión comunican ROJO / VERDE / DESACTUALIZADA / ninguna; la ausencia de evidencia nunca se presenta como éxito | Es la última verificación registrada (hook o `done`); `done` siempre verifica de nuevo |
| `monday check` + manifiesto | Determinista | Archivos gestionados sin divergencias; adaptadores registrados; `AGENTS.md` < 200 líneas | Detecta, no impide |
| Reglas de oro y método | Conductual | Criterio del agente | Un modelo puede ignorarlas; por eso lo crítico tiene mecanismo |

## Compatibilidad comprobada

| Capacidad | Claude Code 2.1.301 | Antigravity CLI 1.4.2 |
|---|---|---|
| Carga de `AGENTS.md` | Vía `CLAUDE.md` → `@AGENTS.md` — e2e ✔ | Nativa — e2e ✔ |
| Estado inyectado al iniciar sesión | `SessionStart` (stdout) — e2e ✔ | `SessionStart` (`injectSteps`) — e2e ✔ |
| Guarda de alcance | `PreToolUse` → `ask` (pregunta en interactivo; deniega en headless) — e2e ✔ headless | `PreToolUse` → `deny` (`ask`/`force_ask` se autoaprueban en `accept-edits`) — e2e ✔ headless |
| No terminar en rojo | `Stop` → `block` — e2e ✔ | `Stop` → `continue` — e2e ✔; la `response` de `agy -p` no es controlable (puede ser texto anterior al bloqueo) → el resultado se juzga con `monday status`/`done` (D-011) — e2e ✔ normal y adversarial |
| Ejecutar `./init.sh` desde el agente en headless | Según permisos de la sesión | Solo con `command(./init.sh)` en la allowlist global de agy; sin ella, el modo print deniega y **termina** la ejecución (ni hooks ni `--mode auto` lo evitan) |
| Agentes por rol | `.claude/agents/` con `model`/`tools` — e2e ✔ (`--agent`) | `.agents/agents/` — e2e ✔ (`--agent`); modelo y herramientas por agente **no verificados** (heredan la sesión) |
| Requiere validación manual | Diálogo `ask` en sesión interactiva; delegación real del líder a subagentes | Antigravity IDE (solo se probó el CLI); restricción de herramientas del explorador/revisor |

## Decisiones

### D-001 — El repositorio es el sistema: copia versionada en `.monday/` (2026-10-18)

Contexto: AgentForge instalaba la metodología como skill global por symlink; el proyecto dependía de la máquina. Decisión: `install` copia `core/` a `<proyecto>/.monday/` con un manifiesto de hashes; se versiona con el proyecto. Alternativas descartadas: symlink global (no portable, rompe en otra máquina o CI); submódulo git (fricción y no funciona sin git). Consecuencias: actualizar es explícito (`install` de nuevo) y con backup; `check` detecta ediciones locales de archivos gestionados.

### D-002 — `features.json` es el contrato (2026-10-18)

Contexto: AgentForge tenía contratos YAML de ~40 campos y reportes autodeclarados; la guía propone `features.json`. Decisión: cada feature es el contrato: `scope` + `acceptance_criteria` con `verify` ejecutable; el CLI escribe los campos de control (`base`, `review`, fechas). Alternativas descartadas: contratos separados (dos fuentes de verdad del mismo requisito); YAML (requiere PyYAML). Consecuencias: el agente no puede «reportar» éxito: lo ejecuta `monday done`.

### D-003 — Tres modos en lugar de L0–L5 × 4 tiers × 8 gates (2026-10-18)

Contexto: la matriz de AgentForge era correcta pero costosa de aplicar y de recordar. Decisión: directo / registrado / orquestado, más riesgo low/medium/high; lo irreversible se trata como puerta humana por tipo de acción, no como nivel. El tier lo fija el rol. Alternativas descartadas: conservar la matriz (ceremonia fija); un solo modo (o burocracia para lo trivial o nada para lo arriesgado). Consecuencias: las gates de AgentForge sobreviven como comprobaciones de `done`.

### D-004 — Python 3 stdlib como única dependencia (2026-10-18)

Contexto: hay que validar JSON, emparejar globs con `**`, consultar git y hablar JSON con los hooks. Decisión: un único `monday.py` sin dependencias externas. Alternativas descartadas: Bash + jq (frágil con JSON anidado y globs; jq es otra dependencia); PyYAML (dependencia instalable por pip). Consecuencias: si falta `python3`, `init.sh` falla con un mensaje explícito.

### D-005 — Hooks finos que llaman al CLI (2026-10-18)

Contexto: AgentForge evitó hooks (AD-006) y todo su cumplimiento quedó en conductual o a posteriori. Decisión: tres hooks por plataforma (`SessionStart`, `PreToolUse`, `Stop`), toda la lógica en `monday.py hook`, misma política para ambas plataformas. Un hook que falla internamente no bloquea al agente (*fail-open*, con aviso por stderr). Alternativas descartadas: clasificador de prompts por regex (AgentForge lo descartó con evidencia); lógica en cada adaptador (copias divergentes). Consecuencias: la respuesta a la plataforma se adapta a su semántica observada (`ask` en Claude, `deny` en agy). Sin `SubagentStop`: pedir «corrige» a un explorador o revisor de solo lectura es incoherente; quien responde del resultado es el líder (`Stop`). El anti-bucle firma *qué* comprobaciones fallan, no su salida, y el hook no corre si solo cambió la memoria.

### D-006 — El líder escribe la memoria; explorador y revisor son de solo lectura (2026-10-18)

Contexto: la guía hace que el explorador escriba `exploration_logs.md` y que el revisor edite reglas. Decisión: ambos devuelven su resultado y el líder decide qué persiste; el revisor solo escribe su veredicto con `monday review`. Alternativas descartadas: dar escritura a los roles de lectura (pierden independencia y aumentan el ruido en la memoria). Consecuencias: la herramienta de solo lectura puede imponerse en la plataforma (Claude: `tools`).

### D-007 — Sin agente «líder» definido (2026-10-18)

Contexto: la guía lista `leader.md`. Decisión: el líder es la sesión principal que habla con el humano; su comportamiento está en `AGENTS.md` y `method.md` §3. Alternativas descartadas: un subagente líder (un orquestador anidado sin el contexto de la conversación). Consecuencias: tres agentes por plataforma, no cuatro.

### D-008 — Revisión anclada al diff (2026-10-18)

Contexto: un `approve` sobre un diff que luego cambia no prueba nada. Decisión: `monday review` guarda una huella (rutas + hashes del contenido cambiado desde `base`); `done` la recalcula. Consecuencias: cualquier cambio posterior exige una nueva revisión.

### D-009 — `history.md` registra también rechazos (2026-10-18)

Contexto: la automejora necesita detectar errores repetidos sin crear otro registro. Decisión: `done` rechazado, `review changes_required` y `block` añaden una entrada breve a `history.md`. Alternativas descartadas: un `errors.md` aparte (otro registro del mismo estado). Consecuencias: el revisor busca patrones en un único archivo.

### D-010 — Huella del contrato y `monday amend` (2026-10-18)

Contexto: la revisión independiente de M-001 demostró que rebajar `risk`, ampliar `scope` o vaciar un `verify` en `features.json` permitía un `done` aceptado sin rastro. Decisión: `start` guarda la huella de risk/scope/criterios/revisión/dependencias y de la base del diff (`base`, `preexisting`); `done` la exige intacta; `amend --reason` la renueva, lo registra en `history.md` e invalida la revisión; `amend` está en `policy.json`, así que con hooks requiere permiso humano. Alternativas descartadas: proteger `features.json` con la guarda (el líder debe poder añadir features); comparar con `git show <base>` (falla si la feature se creó sin commitear). Consecuencias: cambiar el contrato es posible pero siempre visible.

### D-011 — El cierre lo decide la verificación, nunca el informe del agente (2026-10-18)

Contexto: en AC4, un agente de Antigravity bloqueado por el hook `Stop` terminó por un soft-deny del modo print; `agy -p` devolvió su texto *anterior* al bloqueo con `status: SUCCESS` (`progress/exploration_logs.md`). Sondas: ningún hook de agy altera `response` ni `status`, y una terminación por soft-deny no vuelve a invocar `Stop`. Decisión: la barrera está en el límite de integración, no en el texto: el hook y `done` registran el último resultado de `init.sh` con la huella del árbol; `status` (y el inicio de sesión) lo comunican sin ambigüedad; terminar en rojo deja entrada en `history.md`; el cierre solo lo concede `done` con verificación fresca. La e2e (AC4) dejó de aceptar «el agente informó del fallo» como evidencia y añade un escenario adversarial (informe falso forzado). Alternativas descartadas: reescribir la respuesta con hooks (no soportado, comprobado); bloquear indefinidamente en `Stop` (no cubre la terminación por soft-deny y genera bucles); un wrapper de ejecución propio (capa redundante con `done`/`status`). Consecuencias: el consumidor de un agente (humano, orquestador o CI) debe juzgar con `monday status`/`done`, no con el texto.

## Reglas aprendidas

- El texto final de un agente nunca es evidencia de éxito, tampoco en las pruebas e2e: el criterio debe leer estado verificable (`status`, `done`, `init.sh`) — evidencia: AC4 rechazado en el cierre de M-001 (`progress/history.md`) y su causa raíz (`progress/exploration_logs.md`).

- Los criterios que ejecutan Python en tests deben usar `python3 -B` o un `.gitignore` con `__pycache__/`: una caché `.pyc` del mismo segundo y tamaño ocultó un arreglo y apareció como cambio fuera de alcance — evidencia: primera ejecución de `tests/test_monday.py` (2026-10-18).
- Nunca asumir la semántica de una respuesta de hook: comprobarla con el CLI real. `{}` deniega en agy y `ask` se autoaprueba en `accept-edits` — evidencia: `progress/exploration_logs.md` (2026-10-18).
