# Tarea en curso

<!-- Lo mantiene el líder. `monday done` mueve «Resumen» a history.md y reinicia este archivo. -->

Feature: M-005 — Preparar la publicación de Monday 1.0.0 (identidad pública, historial unido con AgentForge, auditoría previa) (desde 2026-10-19T22:32:56-04:00)

## Plan

1. Unir historiales: AgentForge `main` (2f3554d) + tags como ancestros de `main` local sin reescritura (merge `-s ours`) → AC6.
2. Identidad pública: README en inglés (historia AgentForge → Monday, filosofía, alcance honesto), CHANGELOG en inglés con historia de releases → AC5, AC7.
3. Auditoría de publicación y quickstart desde carpeta limpia (`tests/release_check.sh`, `tests/quickstart.sh`) → AC3, AC4.
4. AC4 de M-001 intacto y en verde con agentes reales → AC2.
5. Revisión independiente → `monday done M-005`.
6. Plan de operaciones remotas para autorización humana (renombrar, push, release). No ejecutarlas.

## Estado y próximos pasos

## Bloqueos y errores

## Resumen para el historial

- Historial de AgentForge (main 2f3554d, tags v0.1.0/v0.9.0) unido como ancestro con merge `-s ours` (D-012): árbol intacto, push futuro fast-forward, sin reescritura.
- README y CHANGELOG en inglés con la historia AgentForge → Monday, alcance honesto, integraciones implementadas vs probadas y limitaciones; instrucciones operativas siguen en español.
- Nuevos `tests/release_check.sh` (contrato AC4, auditoría, versión, historial) y `tests/quickstart.sh` (README desde carpeta limpia).
- Evaluación de limitaciones (revisión independiente coincide): ninguna bloquea un release presentado como «primer harness»; `done` siempre reverifica. M-004 (alias de amend) candidato a 1.0.1.
- Decisiones humanas pendientes: publicar el commit con `.claude/scheduled_tasks.lock` (sessionId/pid, inocuo) o reescribir commits locales no publicados; publicar la guía en español que nombra a terceros; autorizar renombrado/push/release; enlaces globales a AgentForge.
