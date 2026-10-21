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
- e2e 16/16 PASS (claude 2.1.301, agy 1.4.3). Revisión independiente: ronda 1 changes_required (install.sh 0.9 necesita `--uninstall --agents`; faltaba AgentForge 0.1) → corregido y reproducido con los install.sh reales en HOME temporal; rondas 2–3 approve.
- Verificación final sobre 0c62a1a (2026-10-20): init.sh, release_check 7/7, quickstart, unittest 51 OK, init.sh --full (e2e) — todo PASS.
- Pendiente tras desbloquear: `git push origin main` (fast-forward desde 2f3554d) → `bash tests/quickstart.sh https://github.com/Admes7a431-2408/Monday_Harness.git main` → `monday done M-006 --manual AC6=… --manual AC7=…` → commit de cierre → push → `git tag -a v1.0.0` en ese commit → `git push origin v1.0.0` → quickstart con `v1.0.0` desde la URL pública.

## Bloqueos y errores

- 2026-10-20: `git push origin main` falla: «could not read Username for 'https://github.com'». Sin credential helper, sin clave SSH aceptada (`Permission denied (publickey)`), sin `gh`. El push vía GitKraken falla igual. Configurar credenciales es puerta humana (secretos). Nada publicado: el remoto sigue en 2f3554d.

## Resumen para el historial

<!-- Qué se hizo, decisiones tomadas y hallazgos fuera de alcance. Breve. -->
