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

- Hecho: fases I–V; 41 tests, `install_roundtrip.sh` y e2e 12/12 en verde (Claude Code + agy).
- Revisión independiente (monday-reviewer, DEEP): ronda 1 changes_required (3 important, 5 minor) → corregidos con 8 regresiones; ronda 2 changes_required (huella sin base/preexisting; `amend` sin puerta humana) → corregidos.
- Siguiente: ronda 3 de revisión → `monday done M-001` (ejecuta init.sh --full y AC4: e2e real).

## Bloqueos y errores

- Ruling (arranque): el repositorio no tenía commits al hacer `start`, así que `preexisting` capturó archivos creados por esta misma feature. Se dejó solo la guía normativa como preexistente — por qué: el resto es trabajo de M-001 — coste si me equivoco: ninguno, el alcance cubre esos archivos.
- Hallazgo de las pruebas: `__pycache__` aparecía como cambio fuera de alcance; se resuelve con `.gitignore` del proyecto (Monday no ignora artefactos por su cuenta: los declara el proyecto).

## Resumen para el historial

- Monday 1.0.0 construido desde la guía normativa; AgentForge auditado como evidencia histórica (exploration_logs). Decisiones D-001…D-010 en docs/architecture.md.
- La revisión independiente encontró 3 defectos importantes reales (rollback pisaba archivos fusionados; contrato de features.json manipulable sin rastro; anti-bucle del Stop roto por salidas variables) y uno en la 2.ª ronda (base del diff fuera de la huella); todos con test de regresión.
- Hallazgos de plataforma: en agy `{}` deniega y `ask`/`force_ask` se autoaprueban en accept-edits → Monday usa `deny`.
- Revisión ronda 3: approve (monday-reviewer). Minor diferido a M-004 (guarda de `amend` vía alias).
- Pendiente fuera de alcance: M-002 (Codex), M-003 (Antigravity IDE), validación interactiva del diálogo `ask` en Claude Code.
