# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); versionado semántico.

## [1.0.0] - 2026-10-18

Primera versión definitiva de Monday. Reconstrucción completa: no comparte código con AgentForge `v0.1.0`/`v0.9.0`, que se conservan como testigos de la evolución del proyecto.

### Añadido

- Núcleo agnóstico (`core/`) que se instala como copia versionada en `<proyecto>/.monday/`, con manifiesto de hashes para detectar divergencias.
- `AGENTS.md` como punto de entrada (<200 líneas) con bloque gestionado; método con tres modos (directo, registrado, orquestado) y riesgo low/medium/high.
- Memoria del proyecto según la guía: `features.json` (contrato ejecutable), `progress/current.md`, `progress/exploration_logs.md`, `progress/history.md`, `docs/architecture.md`.
- CLI `monday.py` (Python 3 stdlib): `status`, `check`, `start`, `verify`, `scope`, `review`, `done`, `block`, `guard`, `hook`, `install`, `rollback`.
- `monday done`: cierre solo con `init.sh`, criterios ejecutables, alcance contra git y revisión anclada al diff en verde; estados `PASS`/`FAIL`/`UNAVAILABLE`/`MANUAL`; rechazos registrados en el historial.
- Roles explorador, implementador y revisor neutrales a la plataforma.
- Adaptador Claude Code: `CLAUDE.md` → `@AGENTS.md`, hooks `SessionStart`/`PreToolUse`/`Stop`/`SubagentStop`, agentes `monday-explorer|implementer|reviewer`.
- Adaptador Antigravity: `.agents/hooks.json` (`SessionStart`/`PreToolUse`/`Stop`) y agentes en `.agents/agents/`.
- Instalación que fusiona en vez de sobrescribir, actualización que se detiene ante ediciones locales y `rollback` (`--all` para desinstalar).
- 32 pruebas deterministas (escenarios S1–S8, distribución, integridad del diseño), `tests/install_roundtrip.sh` y validación con agentes reales `tests/e2e_adapters.sh`.

### Cambiado respecto a AgentForge

- Contratos YAML + reportes autodeclarados → entradas de `features.json` cuyos criterios ejecuta `monday`.
- Levels L0–L5 × tiers × gates G1–G8 → tres modos; el tier lo fija el rol y su modelo vive solo en el adaptador.
- Skill global enlazada por symlink → copia por proyecto («el repositorio es el sistema»).
- Sin hooks → tres hooks finos con la lógica en el CLI.
- PyYAML → solo biblioteca estándar.

### Eliminado

- `routing/profiles.yaml` y posturas, `capabilities/catalog.yaml` y `cap status`, Interface Integrity Gate como mecanismo propio, `--purge-legacy`, `af.py` y la migración `.agentforge/`.
