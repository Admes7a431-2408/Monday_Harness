# Governance: contratos, autoridad y escalamiento

Los contratos son el mecanismo central de autoridad (P8). No son prompts: son la frontera explícita de responsabilidad, alcance, permisos, criterios de éxito, verificación y escalamiento de un trabajo. Plantilla: [`contracts/templates/task.yaml`](../contracts/templates/task.yaml).

## Fuentes de autoridad (de mayor a menor)

1. **El humano** — en la conversación o en un human gate. Puede ampliar o revocar cualquier cosa.
2. **Reglas del proyecto** — `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, configuración de permisos de la plataforma. Un contrato no puede autorizar lo que estas prohíben.
3. **El contrato** de la tarea.
4. **El brief del agente padre** — nunca concede más de lo que el contrato del padre le concede a él (la autoridad solo se estrecha al delegar).
5. **Valores por defecto** de Monday (ver abajo).

## Cuándo hace falta un contrato escrito

| Level | Forma |
|---|---|
| L0 | Ninguna: la petición explícita del humano es la autoridad. |
| L1 | El brief de 6 líneas ([routing.md §4](routing.md#4-el-brief-todo-encargo-delegado)). |
| L2 | Contrato ligero: `id`, `level`, `risk`, `objective`, `scope`, `acceptance_criteria`, `verification`. |
| L3–L4 | Contrato completo en `.monday/contracts/<id>.yaml`; uno por stream en L4. |

Escribe solo los campos que aportan. Un campo vacío no es una restricción: es ruido.

## Valores por defecto (cuando el contrato no dice nada)

- **Alcance:** solo los archivos necesarios para el objetivo; nada en `excluded_areas`; nada fuera del workspace.
- **Comandos:** lectura, build, tests, linters y formateadores *en modo comprobación* están permitidos. Instalar dependencias, migraciones, cambiar configuración global, operaciones de red con efectos y cualquier operación git que publique o reescriba historia (`push`, `merge`, `rebase`, `reset --hard`, `commit` si no se pidió) requieren autorización.
- **Delegación:** según `routing.allow_delegation` ([routing.md §7](routing.md#7-límites-estructurales)); si el contrato no lo dice, `down`.

## Permisos y Enforcement Real

El sistema no promete protecciones mágicas: distingue con rigor técnico entre lo que previene mecánicamente antes de ocurrir, lo que detecta después y lo que depende del comportamiento del modelo.

### Matriz de Enforcement Real

| Nivel | Mecanismo | Dónde se aplica | Amenaza que cubre | Limitación real |
|---|---|---|---|---|
| **1. Conductual (Soft Gate)** | Prompts de sistema, briefs, `AGENTS.md`, `CLAUDE.md`, roles de agente. | Instrucciones al LLM en cada turno. | Desviación accidental del rol o de la intención declarada. | Un LLM puede ignorar o alucinar reglas; no impide físicamente ninguna acción. |
| **2. Plataforma (Platform Enforcement)** | Mecanismos nativos del host (e.g. subagentes de solo lectura, allowlists de herramientas, sandboxing del IDE o CLI). | Entorno de ejecución host (Claude Code CLI, IDE AGY sandbox). No son flags de `monday.py`. | Ejecución de comandos no autorizados o escrituras fuera del sandbox permitido por la herramienta. | Depende exclusivamente de la plataforma host; si el host no aplica aislamiento a nivel de proceso o el sandbox se desactiva, no existe barrera técnica. |
| **3. Técnico Determinista (Hard Gate)** | Validación sintáctica y semántica estricta (`scripts/monday.py validate`), rechazo de claves desconocidas, detección de typos (`check_unknown_keys`). | Validación de contratos, reportes y perfiles antes de iniciar. | Errores tipográficos que anulen silenciosamente exclusiones, campos maliciosos o esquemas incompatibles. | Opera sobre entradas estructuradas; requiere validación estricta de esquema (`schema: 1`). |
| **4. Auditoría Posterior (Post-action Audit)** | `scripts/monday.py check-scope` (auditoría automática en `schema: 1`, flags `--include-ignored` / `--no-include-ignored`), diff git contra `HEAD`, verificación cruzada de comandos en reporte (`validate_report`). | Al completar la ejecución o como gate de aceptación previa al commit. | Detección de archivos fuera de alcance, fugas en carpetas ignoradas o reportes sin evidencia real. | **Detecta después de la modificación, no la previene en tiempo real**. El filtro de evidencia trivial (`schema: 1`) es de coincidencia sintáctica y no sustituye la verificación de fondo de Gate G8. |
| **5. Inobservable / No Aislado** | Subprocesos opacos, llamadas de red sin proxy de inspección, archivos temporales fuera del repo. | Nivel de sistema operativo sin instrumentación. | Ninguna. | El sistema **no puede observar ni bloquear** estas acciones. Deben documentarse explícitamente y requerir Human Gate para autorizar su uso. |

### Modos de Gestión bajo Gobernanza Unificada

Monday aplica una única política de gobernanza: **una capacidad nunca adquiere mayor autoridad ni relaja sus restricciones por el mero hecho de cambiar de modo**.

1. **Manual:** El usuario define sus preferencias, límites y decisiones reservadas. El sistema aplica esas preferencias sin obligarlo a autorizar individualmente cada paso técnico rutinario. Solicita intervención cuando una decisión queda fuera de las preferencias autorizadas o implica un riesgo que exige aprobación explícita.
2. **Recomendado:** El sistema identifica capacidades útiles, explica brevemente su beneficio técnico, coste y consecuencias, y solicita autorización previa antes de utilizarlas.
3. **Gestionado:** El sistema puede adaptar la estrategia y activar dinámicamente capacidades previamente autorizadas dentro de límites explícitos. Debe detenerse y escalar inmediatamente si se requiere ampliar permisos, alterar políticas fundamentales o superar el alcance aprobado.

### Ciclo de Vida de Capacidades

Las capacidades del harness (declaradas en `capabilities/catalog.yaml`) operan bajo 4 estados deterministas:

- **Disponible:** Definida e indexada en el catálogo formal, pero no autorizada para la tarea actual (o no preparada en el entorno).
- **Autorizada:** Concedida formalmente por el usuario o en el contrato de la tarea (`scope.capabilities` / `permissions`), pero sus dependencias o prueba de humo (`check_cmd`) aún no se satisfacen en el entorno.
- **Preparada:** Verificada técnicamente en el entorno local (`check_cmd` devuelve código 0) y autorizada para su uso. Estar preparada no concede permiso de ejecución libre sin contrato.
- **Activa:** En uso directo durante la tarea en curso (`--active NOMBRE`). La activación temporal no genera una autorización persistente nueva.

Se auditan y verifican mediante:
```bash
python3 scripts/monday.py cap status [NOMBRE] [--active NOMBRE] [--authorized CAP1,CAP2] [--contract RUTA]
```

*Modo de inspección ambiental vs modo contractual:*
- Sin `--contract` ni `--authorized`, `monday.py cap status` evalúa la salud técnica del entorno: las herramientas con dependencias satisfechas (`check_cmd` = 0) reportan `Preparada`, y las que fallan o faltan reportan `Disponible`.
- Con `--contract` o `--authorized`, se aplica la política de la tarea: una capacidad solo se considera `Preparada` o `Activa` si está explícitamente autorizada. Si no está autorizada, permanece en `Disponible`. Si está autorizada pero falla su prueba de humo, queda en `Autorizada` (bloqueando su ejecución hasta que se prepare).

### Aislamiento de Memoria por Proyecto

- **Límites de proyecto:** La memoria, decisiones, secretos, contexto y artefactos de cada proyecto se confinan estrictamente al repositorio local (`.monday/`).
- **Nivel de protección real:** El aislamiento entre proyectos opera a nivel conductual (Nivel 1) y mediante auditoría de Git diff (Nivel 4). No constituye una jaula a nivel de kernel/OS salvo que el usuario ejecute los agentes en contenedores o sandboxes dedicados.
- **Ubicación canónica:** `.monday/` es la ubicación canónica y fuente de verdad del proyecto. Las herramientas mantienen retrocompatibilidad de lectura con `.agentforge/` para proyectos heredados sin migrar. Monday jamás escribe nuevo estado en `.agentforge/`; `monday init` siempre inicializa `.monday/` e incluye el comando seguro `--migrate-legacy`.


## Human gates

Detente y pide decisión humana antes de:

1. Acciones **irreversibles o destructivas** (borrar datos, `reset --hard`, sobrescribir trabajo ajeno).
2. Cambios **sensibles para la seguridad** (auth, secretos, permisos, cifrado) cuando no estaban explícitamente en el contrato.
3. **Efectos fuera del workspace** (push, merge, publicar, desplegar, enviar mensajes, llamar APIs con efectos).
4. Un contrato o plan **tan roto que cualquier camino es una suposición**.
5. Lo que el contrato liste en `human_gates`.

Fuera de estos casos, no interrumpas: decide dentro de tu autoridad y deja constancia (ver *rulings*). Para preguntar bien: una sola ronda, solo lo que bloquea, cada pregunta con tu recomendación y el coste de equivocarse. Los hechos los investigas tú; las decisiones son del humano.

## Desviaciones

Cuando durante la ejecución aparece algo no previsto:

```
¿Se puede resolver dentro del contrato (alcance, permisos, criterios)?
 ├─ sí, y es una decisión menor  → decide y regístrala como ruling
 ├─ sí, pero cambia el enfoque   → decide, regístrala y márcala en el reporte como deviation
 └─ no                           → detente y escala (al padre o al humano) con:
                                   qué encontraste · por qué bloquea · opciones · recomendación
```

- **Ruling** (una línea en el reporte): `Ruling: <qué decidí> — <por qué> — <coste si me equivoco>`.
- **Prerrequisito grande:** si "tengo que arreglar X antes de Y" supera aproximadamente un tercio del tamaño de la tarea, es una decisión de alcance, no de implementación: escala.
- **Hallazgos fuera de alcance** (bugs ajenos, código muerto, deuda): van a `unexpected_findings` del reporte, no al diff (P7).
- **Señales de deriva de alcance:** explicar el cambio requiere la palabra "además"; se está editando un tercer grupo de archivos sin relación; el plan se ha reiniciado más de una vez.

## Reglas de escalamiento

| Desde | Hacia | Cuándo |
|---|---|---|
| Subagente | Agente padre | `ESCALATE`/`BLOCKED`: tier insuficiente, fuera de alcance, falta permiso o información. |
| Executor | Orchestrator | El contrato es ambiguo, contradictorio o insuficiente; la solución requiere ampliar alcance. |
| Cualquiera | Humano (L5) | Human gates; fallo en MAX; conflicto entre requisitos que nadie tiene autoridad para resolver. |

Escalar no es fallar: un `ESCALATE` bien fundado vale más que trabajo hecho sobre una suposición. Nadie es penalizado por escalar; sí por ocultar.

## Trazabilidad

Cada trabajo de L2+ deja: contrato (o brief) → líneas `Route:` → rulings → reporte. El `id` del contrato aparece en el reporte y, si aplica, en el mensaje de commit. Con eso cualquier agente o humano puede reconstruir *quién autorizó qué, quién lo hizo, con qué capacidad y cómo se verificó*.
