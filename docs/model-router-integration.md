# Model Router — Propuesta de integración en Monday

**Estado:** propuesta de arquitectura / Feature M-007 pendiente de implementación y validación.  
**Objetivo:** hacer que Monday seleccione delegaciones y modelos de forma consciente de capacidad, complejidad, riesgo, esfuerzo y evidencia, sin perder el núcleo agnóstico ni duplicar su sistema actual de roles.

## 1. Principio de diseño

El Router es una política central de orquestación, no un nuevo agente ni un plugin externo. Monday conserva el liderazgo, contratos, memoria, gates y cierre verificable. El Router responde: *qué rol/capacidad necesita esta unidad de trabajo, qué tier/esfuerzo es suficiente y cuándo escalar*.

No reemplaza los roles `explorer`, `implementer` y `reviewer`; extiende su selección y los tiers abstractos. Modelos y nombres de proveedores concretos se mantienen en configuración del adaptador, no en `core/method.md`, roles ni lógica central.

## 2. Áreas de trabajo y perfiles abstractos

| Área | Perfil / rol abstracto | Ruta inicial propuesta | Escalamiento |
|---|---|---|---|
| Planificación y coordinación | planner/orchestrator | estándar/medio; fast para tareas simples | deep para ambigüedad, impacto o arquitectura |
| Exploración / research | explorer/research | fast o estándar | deep cuando fuentes contradicen o el análisis es crítico |
| Implementación / coding | implementer | estándar | deep para problemas difíciles, arquitectura o debugging complejo |
| Testing | tester (ejecución y diagnóstico) | fast para checks simples; estándar para análisis | deep para fallos complejos; la evidencia siempre viene de comandos/tests |
| Auditoría / Goldfish | reviewer independiente | deep en riesgo/impacto que lo amerite | modelo/esfuerzo independiente o mayor si la revisión no detecta/explica fallos |
| UI/UX y frontend | design/frontend | estándar; perfil visual especializado cuando esté disponible | deep para flujos complejos o decisiones visuales importantes |

Los perfiles de área son etiquetas de routing, no necesariamente agentes nuevos. Reutilizar los roles actuales y crear un rol/agente solo si la auditoría demuestra que es necesario.

## 3. Señales para decidir la ruta

Clasificar cada unidad de trabajo con señales explícitas, sin una matriz de niveles rígida:

- **Complejidad:** cantidad de componentes, dependencias, novedad y razonamiento requerido.
- **Riesgo:** impacto del error, reversibilidad, seguridad, datos, dinero, migraciones o APIs.
- **Incertidumbre:** falta de contexto, contradicciones, requisitos poco claros o resultados previos fallidos.
- **Capacidad requerida:** investigación, código, diseño visual, razonamiento largo, ejecución de tests, crítica independiente.
- **Restricciones:** modelos disponibles en la sesión, políticas/permisos, esfuerzo/quota del usuario y límites de escalamiento.
- **Evidencia:** resultados de tests/builds, diffs, logs y verificaciones, no autoevaluación textual del modelo.

## 4. Ciclo de routing

1. El líder define unidad de trabajo y contrato (objetivo, scope, criterio verificable).
2. El Router asigna área/rol, capacidades, tier abstracto y esfuerzo sugerido.
3. El adaptador resuelve el tier/perfil a modelo y parámetros disponibles en esa plataforma.
4. Se ejecuta la tarea con brief autocontenido y permisos del rol.
5. Se verifica mediante evidencia observable; los tests/commands no se sustituyen por el juicio del modelo.
6. Si hay insuficiencia, se diagnostica el motivo y se escala de forma dirigida: cambiar tier/esfuerzo, rol o enfoque; no repetir exactamente el mismo intento.
7. Los reintentos y escaladas tienen límites. Al agotarlos, se informa bloqueo y se solicita decisión humana.
8. Se registra la decisión y resultado para evaluación futura, sin almacenar secretos ni datos sensibles.

## 5. Política de escalamiento

Escalar solo con causa: fallo de verificación, evidencia incompleta, ambigüedad crítica, contradicción, hallazgo de auditoría o dificultad diagnosticada. No escalar automáticamente por tamaño de prompt.

- Máximo sugerido: dos intentos correctivos/escaladas por problema; luego bloqueado y humano, salvo política configurable y justificada.
- Evitar saltar directamente al modelo/esfuerzo máximo por defecto.
- No lanzar múltiples agentes duplicados; paralelizar solo unidades disjuntas y útiles.
- No degradar silenciosamente si una ruta no está disponible. Fallback debe preservar capacidades requeridas o declarar `BLOCKED/UNAVAILABLE`.
- El Router puede recomendar; los gates deterministas y autorización humana siguen prevaleciendo.

## 6. Goldfish / revisión independiente

La revisión independiente es una función de calidad, no una etiqueta de modelo. Cuando se exige revisión (riesgo alto, arquitectura, seguridad, cambios amplios o criterios explícitos):

- El revisor no puede ser el implementador.
- Debe recibir un paquete de revisión: contrato/spec, diff exacto, comandos y resultados, decisiones relevantes y preguntas de auditoría.
- No se le entrega la cadena de razonamiento privada del coordinador ni se le pide simular independencia dentro del mismo agente.
- La revisión se registra y se ancla al diff; cualquier cambio posterior invalida el resultado según el mecanismo actual.
- Si la plataforma no permite independencia real, Monday debe declarar la limitación y usar revisión alternativa verificable o escalar al humano.

## 7. Configuración y responsabilidades

- **Core:** señales, reglas de routing abstractas, límites, fallbacks, trazabilidad, validación de configuración y tests deterministas.
- **Adaptadores:** disponibilidad/capacidades reales, mapeo de perfiles/tier/esfuerzo a modelos y parámetros, límites de plataforma; sin duplicar política central.
- **Roles:** contratos e instrucciones neutrales de tarea.
- **Proyecto:** especifica restricciones, criterios, preferencias y presupuesto/esfuerzo cuando corresponda.
- **Usuario:** conserva puertas humanas, acciones externas y cambios irreversibles.

La configuración debe poder desactivar rutas, declarar capacidades, establecer preferencias y límites. No codificar nombres/versiones de modelos en el core.

## 8. Observabilidad y evaluación

Registrar, de forma compacta y configurable: feature/task ID, rol/área, señales de clasificación, ruta seleccionada, motivo, modelo/tier/esfuerzo resuelto por el adaptador, resultado, verificaciones, escalamiento y latencia si está disponible. Cuotas/costos solo si se reciben de una fuente real; no estimarlos como hechos.

Usar resultados observables para comparar: éxito verificable, retrabajo/escaladas, calidad de revisión, latencia y consumo disponible. No convertir benchmarks externos ni ranking de Arena en garantías; usar datos empíricos del uso del harness.

## 9. Implementación por fases

1. **Auditoría:** mapear delegación, frontmatter de agentes, tiers, hooks y tests actuales; identificar puntos de extensión y posibles duplicaciones.
2. **Spec + tests:** definir schema/configuración neutral, señales, decisiones deterministas y fixtures para routing/fallback/escalamiento.
3. **Core Router:** implementar selector/policy en stdlib; no hacer llamadas a proveedores desde core.
4. **Adaptadores:** integrar mapeos reales y validar en CLIs; documentar capacidades no probadas.
5. **Goldfish:** formalizar el paquete y registro de revisión independiente sin romper revisión anclada actual.
6. **Telemetría mínima:** registro seguro de decisiones/resultados y evaluación; evitar observabilidad excesiva.
7. **Rollout:** modo observación (router recomienda, delegación existente ejecuta) → activar gradualmente → comparar resultados → convertirlo en ruta por defecto si supera pruebas.

## 10. No objetivos / salvaguardas

- No reemplazar de golpe los agentes, hooks, gates, CLI o contratos existentes.
- No hacer que Monday dependa de Claude, Gemini, un proveedor, ranking de modelos o servicio externo.
- No auto-ejecutar acciones irreversibles ni ampliar scope.
- No confundir la salida del modelo con evidencia.
- No prometer independencia Goldfish si el contexto/modelo/ejecutor no es realmente separado.
- No agregar framework, dependencia o infraestructura hasta demostrar necesidad.

## 11. Condición de aceptación

La Feature M-007 debe cerrar solo cuando routing y escalamiento estén implementados y probados, los adaptadores mapeen capacidades reales, la revisión independiente funcione según límites de plataforma, la documentación describa lo que existe (no lo aspiracional), y la suite completa de regresión pase. Esta propuesta por sí sola no constituye implementación.
