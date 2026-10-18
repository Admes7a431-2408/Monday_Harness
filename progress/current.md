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

- Hecho: CLI `core/monday.py`, método, roles, plantillas, adaptadores, 32 tests + `install_roundtrip.sh` en verde.
- Siguiente: `docs/architecture.md`, `tests/e2e_adapters.sh` (claude -p / agy -p), README/CHANGELOG, revisión.

## Bloqueos y errores

- Ruling (arranque): el repositorio no tenía commits al hacer `start`, así que `preexisting` capturó archivos creados por esta misma feature. Se dejó solo la guía normativa como preexistente — por qué: el resto es trabajo de M-001 — coste si me equivoco: ninguno, el alcance cubre esos archivos.
- Hallazgo de las pruebas: `__pycache__` aparecía como cambio fuera de alcance; se resuelve con `.gitignore` del proyecto (Monday no ignora artefactos por su cuenta: los declara el proyecto).

## Resumen para el historial

<!-- Qué se hizo, decisiones tomadas y hallazgos fuera de alcance. Breve. -->
