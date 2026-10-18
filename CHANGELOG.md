# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); versionado semántico.

## [0.9.0] - 2026-10-18

### Added
- Transmutación integral de la identidad operativa y arquitectura del producto a **Monday**.
- `scripts/monday.py`: CLI canónico de Monday implementando `tier`, `role`, `validate`, `check-scope`, `cap status` e `init` (con `--migrate-legacy` no destructivo).
- Subagentes oficiales para Claude Code en `adapters/claude-code/agents/`: `monday-reviewer.md` (revisor G8 independiente en DEEP/Opus), `monday-scout.md` (exploración FAST/Haiku) y `monday-worker.md` (ejecución STANDARD/Sonnet).
- Directorio canónico de proyectos `.monday/` con glosario (`CONTEXT.md`), contratos (`contracts/`) y reportes (`reports/`), con retrocompatibilidad de solo lectura para `.agentforge/`.
- `capabilities/catalog.yaml`: catálogo formal de capacidades base con pruebas de humo deterministas ejecutadas en `cwd=ROOT` sin evaluación de shell.
- Contrato canónico `MON-0025-agentforge-to-monday-transmutation` y reporte formal de cierre en `.monday/`.
- Soporte para contratos y reportes con `schema: 1`: validación estricta de evidencia sustantiva en gates, obligatoriedad de `tests_executed` cuando el contrato define `verification.commands`, y validación sustantiva de comandos y resultados observados en `tests_executed` (rechazo de placeholders triviales).
- Flag `monday.py validate --strict-schema`: validación estricta que exige `schema: 1`.
- `install.sh --check` y `--purge-legacy`: auditoría completa de enlaces de Monday y retirada segura en tres fases de residuos de agentes legacy con respaldo verificado (`cmp`).
- Suite de pruebas determinista en `tests/test_monday.py` con 123 pruebas unitarias distintas cubriendo todas las capacidades, aislamiento y migraciones.

### Changed
- `install.sh`: enlaces canónicos de skill para Claude Code (`~/.claude/skills/monday`) y Antigravity (`~/.gemini/config/skills/monday`), con desinstalación y purga auditada mediante `readlink -f`.
- `SKILL.md`: actualizado para Monday (nombre, disparadores y referencias operativas).
- Documentación y metodología (`README.md`, `methodology/*.md`, `docs/*.md`): unificadas bajo la arquitectura Monday.
- `routing/profiles.yaml`: perfiles actualizados con los subagentes oficiales `monday-*`.
- `methodology/governance.md`: Matriz de Enforcement Real de 5 niveles, unificación de los 3 modos de gestión (Manual, Recomendado, Gestionado) bajo gobernanza común, ciclo de vida de capacidades y aislamiento estricto de memoria por proyecto.
- `adapters/claude-code/README.md` y `adapters/antigravity/README.md`: documentación de límites de enforcement mecánico vs conductual por plataforma, autoridad limitada del modo Gestionado y aislamiento estricto de memoria local.
- `scripts/af.py`: convertido en forwarder shim ejecutor hacia `scripts/monday.py` con advertencia de deprecación en `stderr` (retiro programado en v1.0.0).
- `scripts/monday.py validate`: contratos no versionados emiten una advertencia de obsolescencia por `stderr` manteniendo retrocompatibilidad salvo que se pase `--strict-schema`.

### Security
- Inyección de catálogo CWD prevenida: `monday.py cap status` ejecuta checks desde el contexto seguro `ROOT` sin `shell=True`, ignorando catálogos hostiles en CWD.
- Migración no destructiva y segura: `init --migrate-legacy` valida que ningún enlace simbólico escape del directorio origen antes de copiar, y usa `symlinks=True` para evitar la desreferenciación accidental de archivos enlazados fuera del repositorio.
- `monday.py validate`: rechazo estricto de claves desconocidas (`check_unknown_keys`) en tareas, scopes, permisos, verificación, routing, contexto, reportes y agentes, con sugerencias automáticas para typos comunes.
- `monday.py validate` y `check-scope`: rechazo de reglas de alcance absolutas (POSIX, unidad Windows, UNC) o con segmentos `..` y validación de relleno con espacios.
- `check-scope`: marca como violación todo enlace simbólico que escape del repositorio o cuyo destino real quede fuera del alcance o en un área excluida. En contratos `schema: 1` audita automáticamente rutas ignoradas por `.gitignore`, y en cualquier contrato audita si rutas ignoradas invaden un área excluida (`excluded_areas`).
- `install.sh --purge-legacy`: borra con `rm -f` y da por purgado un archivo solo si ya no existe; en otro caso informa `INCOMPLETA` con código 1.
- `scope` mal tipado se maneja como error de configuración (código 2 en `check-scope`, error en `validate`) en lugar de traza de Python.

## [0.1.0] - 2026-10-07

### Added
- Metodología AgentForge: principios, routing L0-L5, roles, gobernanza, quality gates y gestión de conocimiento.
- Contratos de tarea y reportes YAML con plantillas y ejemplos.
- `scripts/af.py`: `tier`, `role`, `validate`, `check-scope` (G5) e `init` (crea `.agentforge/` con `CONTEXT.md`, `contracts/` y `reports/`).
- Interface Integrity Gate (I1-I9).
- Adaptadores para Claude Code y Antigravity.
- `install.sh` por symlinks (SSOT) con `--dry-run`, `--uninstall` y `--help`, idempotente.
- Suite de tests (`python3 -m unittest discover -s tests -v`).
- Licencia MIT (`LICENSE`) y sección de referencias técnicas y agradecimientos en `README.md`.
