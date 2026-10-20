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

## 2026-10-18 · M-001 · REVISIÓN: changes_required (monday-reviewer)
- Ronda 4 (c932b6f..17fd6c5): el escenario 3 no debilita AC4 frente al requisito: la traza del hook sigue siendo obligatoria si hay cambios y deja de contar el texto del modelo. important: worktree_fingerprint (monday.py:284) solo cubre lo que difiere de HEAD, sin HEAD; un VERDE registrado con árbol limpio sigue como 'VERDE (árbol actual)' después de hacer commit de código roto (reproducido: status VERDE con init.sh en rojo). Solución: incluir HEAD en la huella. minor: con 'sin cambios en 2 intentos' e2e sale con 127 y AC4 pasa a UNAVAILABLE, que se puede cerrar con --manual (antes era FAIL); en Claude, terminar en rojo tras el bloqueo no deja entrada en history.md (stop_hook_active sale antes), al contrario de lo que dice la tabla de architecture.md; la huella excluye features.json y los archivos ignorados.

## 2026-10-18 · M-001 · RECHAZADO
- init.sh PASS · AC1 FAIL · AC2 PASS · AC3 PASS · AC4 PASS · AC5 MANUAL · scope PASS · review PASS

## 2026-10-18 · M-001 · DONE — Monday 1.0.0: núcleo agnóstico, adaptadores Claude Code y Antigravity, distribución reversible y validación
- Evidencia: init.sh PASS · AC1 PASS · AC2 PASS · AC3 PASS · AC4 PASS · AC5 MANUAL · scope PASS · review PASS
- Archivos: .gitignore, .monday, AGENTS.md, CHANGELOG.md, CLAUDE.md, LICENSE, README.md, adapters/antigravity/agents/monday-explorer.md, adapters/antigravity/agents/monday-implementer.md, adapters/antigravity/agents/monday-reviewer.md, adapters/antigravity/hooks.json, adapters/claude-code/CLAUDE.md, adapters/claude-code/agents/monday-explorer.md, adapters/claude-code/agents/monday-implementer.md, adapters/claude-code/agents/monday-reviewer.md, adapters/claude-code/settings.json, core/.gitignore, core/VERSION, core/method.md, core/monday.py, core/policy.json, core/roles/explorer.md, core/roles/implementer.md, core/roles/reviewer.md, core/templates/AGENTS.md, core/templates/architecture.md, core/templates/current.md, core/templates/exploration_logs.md, core/templates/features.json, core/templates/history.md, core/templates/init.sh, docs/architecture.md, init.sh, tests/e2e_adapters.sh, tests/install_roundtrip.sh, tests/test_monday.py
- Evidencia manual AC5: evidencia: README, CHANGELOG y docs/architecture.md revisados contra lo implementado tras la corrección de AC4 y del empaquetado: recuentos (49 tests, 16 controles e2e), D-011, tabla de compatibilidad, límites (response de agy no controlable, allowlist global para ./init.sh) y reglas aprendidas coinciden con resultados ejecutados; revisión independiente rondas 1–6
- Monday 1.0.0 construido desde la guía normativa; AgentForge auditado como evidencia histórica (exploration_logs). Decisiones D-001…D-010 en docs/architecture.md.
- La revisión independiente encontró 3 defectos importantes reales (rollback pisaba archivos fusionados; contrato de features.json manipulable sin rastro; anti-bucle del Stop roto por salidas variables) y uno en la 2.ª ronda (base del diff fuera de la huella); todos con test de regresión.
- Hallazgos de plataforma: en agy `{}` deniega y `ask`/`force_ask` se autoaprueban en accept-edits → Monday usa `deny`.
- Revisión ronda 3: approve (monday-reviewer). Minor diferido a M-004 (guarda de `amend` vía alias).
- AC4: la causa raíz fue que `agy -p` devuelve el último texto del modelo (incluso anterior a un bloqueo) con SUCCESS, y ningún hook lo cambia. Ahora el cierre lo decide la verificación persistida (D-011); la e2e incluye un escenario adversarial. Revisión rondas 4–5.
- `done` (2.º intento) rechazó AC1: `install` distribuía `core/runtime/` (estado del repo vía `.monday -> core`); corregido con test (ronda 6 approve).
- Minor diferido (ronda 5): `stop_hook_active` también es true si bloqueó otro Stop hook del usuario; Monday entonces solo registra.
- Requiere decisión humana: skills globales `monday` que aún enlazan a AgentForge (~/.claude/skills, ~/.gemini/config/skills); `command(./init.sh)` en la allowlist global de agy para que el agente pueda autoverificarse en headless.
- Pendiente fuera de alcance: M-002 (Codex), M-003 (Antigravity IDE), validación interactiva del diálogo `ask` en Claude Code.

## 2026-10-19 · M-005 · RECHAZADO
- init.sh FAIL · AC1 PASS · AC2 FAIL · AC3 PASS · AC4 PASS · AC5 PASS · AC6 PASS · AC7 MANUAL · scope PASS · review PASS

## 2026-10-19 · M-005 · CONTRATO MODIFICADO
- Motivo: Corrección indispensable autorizada por el humano en la misión de release (§6 'correcciones indispensables'): AC2/AC4 falló porque agy ofreció edit_file/Path, que la guarda no conocía; se amplía el alcance a core/monday.py y adapters/antigravity/** solo para ese arreglo.
- Ahora: risk high · scope README.md, CHANGELOG.md, docs/**, tests/**, AGENTS.md, core/templates/AGENTS.md, .gitignore, core/monday.py, adapters/antigravity/** · criterios AC1, AC2, AC3, AC4, AC5, AC6, AC7 (manual)
- La revisión previa queda invalidada
