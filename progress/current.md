# Tarea en curso

<!-- Lo mantiene el líder. `monday done` mueve «Resumen» a history.md y reinicia este archivo. -->

Feature: M-001 — Monday 1.0.0: núcleo agnóstico, adaptadores Claude Code y Antigravity, distribución reversible y validación (desde 2026-10-18T16:57:46-04:00)

## Plan

1. Fase I — investigación de la guía y AgentForge → `progress/exploration_logs.md` ✔
2. Fase II — arquitectura mínima → `docs/architecture.md` (decisiones D-001…)
3. Fase III — núcleo (`core/`), adaptadores, distribución → AC1, AC2, AC3 ✔ (tests en verde)
4. Fase IV — validación con agentes reales (`tests/e2e_adapters.sh`) → AC4
5. Fase V — README, CHANGELOG, notas de release → AC5 (manual)
6. Revisión independiente (risk high) → `monday review` → `monday done M-001`

## Estado y próximos pasos

- Fases I–V hechas; revisión independiente aprobada en ronda 3; `done` rechazó por AC4 (agy) → feature reanudada para resolver AC4 reforzando el adaptador (decisión humana: opción 2, AC4 intacto).
- Causa raíz (exploration_logs): agy -p devuelve el último texto del modelo con SUCCESS; ningún hook lo altera y el soft-deny no reinvoca Stop.
- Corrección: estado de verificación persistido (`verification.json`) comunicado por `status`/inicio de sesión; sesión terminada en rojo → history.md; e2e AC4 juzga por estado verificable + escenario adversarial. 46 tests OK; las 5 nuevas fallan con el código anterior.
- Siguiente: e2e real completa → revisión independiente de la corrección → `monday done M-001`.

## Bloqueos y errores

- Ruling (arranque): el repositorio no tenía commits al hacer `start`, así que `preexisting` capturó archivos creados por esta misma feature. Se dejó solo la guía normativa como preexistente — por qué: el resto es trabajo de M-001 — coste si me equivoco: ninguno, el alcance cubre esos archivos.
- Hallazgo de las pruebas: `__pycache__` aparecía como cambio fuera de alcance; se resuelve con `.gitignore` del proyecto (Monday no ignora artefactos por su cuenta: los declara el proyecto).

## Resumen para el historial

- Monday 1.0.0 construido desde la guía normativa; AgentForge auditado como evidencia histórica (exploration_logs). Decisiones D-001…D-010 en docs/architecture.md.
- La revisión independiente encontró 3 defectos importantes reales (rollback pisaba archivos fusionados; contrato de features.json manipulable sin rastro; anti-bucle del Stop roto por salidas variables) y uno en la 2.ª ronda (base del diff fuera de la huella); todos con test de regresión.
- Hallazgos de plataforma: en agy `{}` deniega y `ask`/`force_ask` se autoaprueban en accept-edits → Monday usa `deny`.
- Revisión ronda 3: approve (monday-reviewer). Minor diferido a M-004 (guarda de `amend` vía alias).
- Pendiente fuera de alcance: M-002 (Codex), M-003 (Antigravity IDE), validación interactiva del diálogo `ask` en Claude Code.
