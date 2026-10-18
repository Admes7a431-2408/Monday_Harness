# Historial

Registro de cierres (`DONE`), rechazos, bloqueos y revisiones con su evidencia. Lo escribe `monday`; no se reescriben entradas pasadas.

## 2026-10-18 · M-001 · REVISIÓN: changes_required (monday-reviewer)
- important: (1) rollback restaura AGENTS.md/CLAUDE.md/settings.json sin comprobar hash y borra el backup: pierde ediciones posteriores a install (reproducido); (2) features.json es always_writable sin guarda y done no compara risk/scope/criterios/base con la base: done ACEPTADO con bug sin arreglar, README fuera de alcance y risk high->low (reproducido); (3) hook stop firma el tail de init.sh con tiempos variables: en agy (sin stop_hook_active) bloquea en cada parada (3 continue seguidos reproducidos). minor: rollback --all deja .monday/runtime; SubagentStop exige corregir a roles de solo lectura; init.sh en cada Stop con árbol sucio; docs (32 vs 33 tests, force_ask obsoleto en exploration_logs, claim 'nunca sobrescribe/se conservan'); --relative ignora cambios fuera de root en monorepo.

## 2026-10-18 · M-001 · CONTRATO MODIFICADO
- Motivo: La huella de contrato (D-010) se introdujo tras start a raíz de la revisión; el contrato de M-001 no ha cambiado desde su definición. En el arranque se ajustó 'preexisting' a mano (solo la guía), ver ruling en current.md.
- Ahora: risk high · scope core/**, adapters/**, tests/**, docs/**, AGENTS.md, CLAUDE.md, README.md, CHANGELOG.md, LICENSE, init.sh, install.sh, .gitignore, .monday, .claude/**, .agents/** · criterios AC1, AC2, AC3, AC4, AC5 (manual)
- La revisión previa queda invalidada
