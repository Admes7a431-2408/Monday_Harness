# Tarea en curso

<!-- Lo mantiene el líder. `monday done` mueve «Resumen» a history.md y reinicia este archivo. -->

Feature: M-006 — distribución pública desde Monday_Harness (modo orquestado, riesgo high)

## Plan

<!-- paso → cómo se verifica -->

1. Auditoría (hecha): remoto `main` = 2f3554d (v0.9, `install.sh` con symlinks globales, URL `AgentForge.git`); local 18 commits por delante, 0 detrás (fast-forward). Tags v0.1.0/v0.9.0 idénticos en local y remoto. Sin `gh`.
2. `install` avisa (sin tocar nada) de: `init.sh` propio que no ejecuta `monday check`; restos de 0.9/AgentForge en el proyecto (`.monday/CONTEXT.md`, `contracts/`, `reports/`, `.agentforge/`) y enlaces globales de `install.sh` 0.9 → tests en `Distribution`.
3. README: clon fuera del proyecto y fijado a `v1.0.0`, comprobar instalación (`check`/`status`), desinstalar, pedirlo a un agente, migración desde 0.9 → AC7 manual + quickstart.
4. `tests/quickstart.sh [url] [ref]`: misma secuencia contra la URL pública → AC3 local, AC6 remoto.
5. `./init.sh --full`, release_check, e2e; revisión independiente; `monday done`.
6. Commit; push fast-forward de `main`; quickstart desde la URL pública; tag `v1.0.0` sobre el commit final; verificación en GitHub.

## Estado y próximos pasos

- Pasos 2–4 hechos: `install_notices` + test `Distribution` (51 OK); README «Getting started» reescrito; D-013; quickstart local PASS; release_check 7/7 PASS.
- Ensayo con agentes reales en proyecto existente (AGENTS.md propio, cambio sin commitear, archivo sin rastrear), desde core local: claude (haiku) y agy 1.4.3 recitan protocolo y regla propia; `rm -rf` → ask (claude), `.monday/policy.json` → ask (claude) / deny (agy), archivos intactos (sha256); rollback --all deja solo los cambios del usuario.
- Quickstart contra el main publicado actual (2f3554d) falla: no existe core/monday.py (esperado, D1).
- Pendiente: e2e completo (en curso), revisión independiente, commit, push, quickstart remoto, done, tag.

## Bloqueos y errores

## Resumen para el historial

<!-- Qué se hizo, decisiones tomadas y hallazgos fuera de alcance. Breve. -->
