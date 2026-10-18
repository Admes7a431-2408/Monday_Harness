# Historial

Registro de cierres (`DONE`), rechazos, bloqueos y revisiones con su evidencia. Lo escribe `monday`; no se reescriben entradas pasadas.

## 2026-10-18 · M-001 · REVISIÓN: changes_required (monday-reviewer)
- important: (1) rollback restaura AGENTS.md/CLAUDE.md/settings.json sin comprobar hash y borra el backup: pierde ediciones posteriores a install (reproducido); (2) features.json es always_writable sin guarda y done no compara risk/scope/criterios/base con la base: done ACEPTADO con bug sin arreglar, README fuera de alcance y risk high->low (reproducido); (3) hook stop firma el tail de init.sh con tiempos variables: en agy (sin stop_hook_active) bloquea en cada parada (3 continue seguidos reproducidos). minor: rollback --all deja .monday/runtime; SubagentStop exige corregir a roles de solo lectura; init.sh en cada Stop con árbol sucio; docs (32 vs 33 tests, force_ask obsoleto en exploration_logs, claim 'nunca sobrescribe/se conservan'); --relative ignora cambios fuera de root en monorepo.

## 2026-10-18 · M-001 · CONTRATO MODIFICADO
- Motivo: La huella de contrato (D-010) se introdujo tras start a raíz de la revisión; el contrato de M-001 no ha cambiado desde su definición. En el arranque se ajustó 'preexisting' a mano (solo la guía), ver ruling en current.md.
- Ahora: risk high · scope core/**, adapters/**, tests/**, docs/**, AGENTS.md, CLAUDE.md, README.md, CHANGELOG.md, LICENSE, init.sh, install.sh, .gitignore, .monday, .claude/**, .agents/** · criterios AC1, AC2, AC3, AC4, AC5 (manual)
- La revisión previa queda invalidada

## 2026-10-18 · M-001 · REVISIÓN: changes_required (monday-reviewer)
- Re-revisión 080a5af..b1735d9: (1) rollback addressed; (3) firma Stop addressed (alterna block/allow, reproducido); (4)(5)(6)(7)(8) addressed. (2) parcial, important: CONTRACT_KEYS no incluye base ni preexisting y la huella se calcula antes de fijar base (monday.py:417); reproducido: commit con README fuera de alcance + editar solo 'base'=HEAD en features.json -> review sobre 0 archivos y done ACEPTADO, sin recalcular huella. minor: 'amend' no está en ask_commands (guard --cmd OK), así que rebajar risk/ampliar scope no pasa por el humano aunque method.md lo exige.

## 2026-10-18 · M-001 · CONTRATO MODIFICADO
- Motivo: La huella ahora incluye base/preexisting (2.ª ronda de revisión); contrato de M-001 sin cambios.
- Ahora: risk high · scope core/**, adapters/**, tests/**, docs/**, AGENTS.md, CLAUDE.md, README.md, CHANGELOG.md, LICENSE, init.sh, install.sh, .gitignore, .monday, .claude/**, .agents/** · criterios AC1, AC2, AC3, AC4, AC5 (manual)
- La revisión previa queda invalidada

## 2026-10-18 · M-001 · RECHAZADO
- init.sh PASS · AC1 PASS · AC2 PASS · AC3 PASS · AC4 FAIL · AC5 MANUAL · scope PASS · review PASS

## 2026-10-18 · M-001 · BLOQUEADA
- AC4 FAIL no determinista: en una de dos tandas e2e, el agente de Antigravity (gemini-3.8-flash-medium), tras el bloqueo del hook Stop, terminó con init.sh en rojo afirmando éxito. El hook funcionó (bloqueó); la honestidad del informe final depende del modelo. Opciones: (1) amend AC4 separando garantía determinista del comportamiento del modelo y documentarlo como limitación de agy; (2) reforzar el adaptador agy (p. ej. segundo bloqueo o PostInvocation) y revalidar; (3) usar un modelo más capaz en e2e. Recomendación: (1)+(documentar), decisión humana porque rebaja un criterio.
