# Spec Gate / EGM — propuesta M-008

## Propósito
Revisar la especificación antes de programar cuando el costo de asumir requisitos supera la fricción de planificar. Se reutilizan Explorer, Implementer y Reviewer; no se instala un plugin ni se crean agentes permanentes redundantes.

## Activación adaptativa
- No requerido: cambios pequeños, localizados, reversibles, prototipos/UI exploratoria sin lógica crítica.
- Ligero: feature moderada o con incertidumbre: una revisión de comprensión y un pase crítico (puede ser un mismo agente en contextos separados si se declara la limitación).
- Obligatorio: dinero, seguridad, persistencia/migraciones, concurrencia, reglas de negocio complejas, arquitectura, impacto alto o ambigüedad crítica.

Los activadores y niveles deben ser configurables y evaluados junto con M-007 Router. Riesgo incierto se trata conservadoramente; no imponer revisiones múltiples por defecto.

## Flujo
1. Elephant (líder con contexto): prepara spec breve: objetivo/no objetivos, reglas, decisiones, scope, criterios verificables, escenarios, persistencia/error/recovery cuando aplique. Pregunta al usuario solo decisiones bloqueantes con recomendación.
2. Goldfish — comprensión: recibe solo spec y referencias explícitamente permitidas; devuelve su interpretación y enumera huecos/ambigüedades que obligarían a inventar.
3. Goldfish — crítica/simplificación: revisa contradicciones, edge cases, seguridad, integridad, concurrencia, fallos y alternativa más simple, según el riesgo. El Router decide si se separan agentes/modelos o se hacen pases secuenciales; nunca se afirma independencia si comparten contexto.
4. Reconciliación: líder clasifica hallazgos (bloqueante/importante/menor), corrige spec y consulta al usuario los bloqueantes. No acepta suposiciones como decisiones del usuario.
5. Gate: aprobación registrada; spec congelada para implementación. Cambios sustanciales reabren el Gate.
6. Implementación: implementador trabaja contra spec aprobada y scope; pausa si detecta contradicción o requisito nuevo.
7. Post-implementación: revisor conserva revisión independiente del diff, tests/evidencia y contrato. Spec Gate no sustituye revisión final ni monday done.

## Principios
- Contexto Goldfish mínimo y autocontenido, sin conversación previa del Elephant; referencias permitidas declaradas.
- La revisión evalúa el documento, no especula sobre lo que el usuario «seguramente quiso».
- Evitar ciclos infinitos: rondas limitadas; tras límite, escalar o aceptar riesgo explícitamente por humano.
- Coste y latencia importan: no activar EGM en tareas triviales.
- Requisitos funcionales y seguridad deben verificarse en la capa autoritativa (p. ej. servidor/backend), no solo en UI.
- Fallo/corrupción de datos: preservar original, error controlado y recuperación; no reemplazar automáticamente datos reales con fixtures.
- Concurrencia, idempotencia, permisos y recovery se incluyen cuando son relevantes, no como checklist universal.
- El resultado debe incluir evidencia/criterios testeables y no depender del informe verbal del agente.

## Integración con M-007
M-007 resuelve routing (rol/modelo/capacidad/esfuerzo y escalamiento). M-008 define el protocolo pre-code y cuándo exigirlo. Router selecciona cantidad y capacidades de revisores de forma proporcional; core define política neutral y adaptadores declaran capacidades reales. La falta de subagentes/contexto independiente se reporta y se recurre a revisión alternativa o humano.

## Estado
Diseño propuesto. No implementa el Gate ni modifica runtime. La Feature M-008 en features.json gobierna auditoría, tests, rollout y aceptación.
