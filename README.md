# Monday

Metodología y tooling para que agentes de IA produzcan software correcto y verificable: cada trabajo recibe el proceso, la autoridad y la capacidad cognitiva justos.

## El problema

Los agentes delegan sin límites claros, amplían el alcance, declaran éxito sin evidencia y esconden errores tras otros agentes. Monday impone contratos explícitos, verificación determinista y reportes honestos.

## Arquitectura y Coordinación

```text
Human (Product / Intent)
  ↓
Orchestrator (Antigravity / Architect / Quality Owner)
  ↓
Contracts (.monday/contracts/<id>.yaml)
  ↓
Workers (Claude Code / Implementation)
  ↓
Verification (Deterministic Tools: scripts/monday.py + tests)
  ↓
Review (Independent Reviewer: monday-reviewer)
  ↓
Human Acceptance
```

- `SKILL.md` — punto de entrada de la skill.
- `methodology/` — principios, routing, roles, gobernanza, quality gates, conocimiento.
- `capabilities/catalog.yaml` — catálogo de capacidades y pruebas de salud ambiental.
- `contracts/` — plantillas (`templates/`) y ejemplos (`examples/`) de contratos y reportes.
- `routing/profiles.yaml` — mapeo tier → modelo/esfuerzo por plataforma.
- `scripts/monday.py` — comprobaciones deterministas (`tier`, `role`, `validate`, `check-scope`, `cap status`, `init`).
- `adapters/` — diferencias de plataforma (Claude Code, Antigravity).
- `install.sh` — instalación reversible por symlinks (una sola fuente de verdad).

## Ciclo de Vida y Niveles

```text
Intent → Discovery → Research → Architecture → Decomposition → Contract → Execution → Verification → Review → Report
```

| Nivel | Nombre | Uso |
|---|---|---|
| L0 | DIRECT | Pregunta o edición trivial, sin burocracia |
| L1 | LIGHT | Cambio pequeño: «qué cambió + cómo se verificó» |
| L2 | STANDARD | Contrato de tarea escrito con scope y acceptance criteria |
| L3 | ORCHESTRATED | Orquestación con contexto desacoplado y routing dinámico |
| L4 | MULTI-STREAM | Orquestación multi-agente en streams paralelos |
| L5 | CRITICAL | Trabajo crítico de alto riesgo con human gates obligatorios |

Tiers de capacidad cognitiva: `FAST`, `STANDARD`, `DEEP`, `MAX`.
Dimensiones de riesgo: `low`, `medium`, `high`, `critical`.
Detalle completo en `methodology/routing.md` y `methodology/quality-gates.md`.

## Flujo de Trabajo

1. **Clasificar**: nivel (L0–L5), tier cognitivo, riesgo y decisión de ejecutar o delegar.
2. **Contratar**: escribir el contrato (`.monday/contracts/<id>.yaml`) y validar con `monday.py validate`.
3. **Ejecutar**: el ejecutor opera dentro del alcance (`allowed_files`), sin tocar `excluded_areas`.
4. **Verificar**: comprobar gates (G1…G8), incluyendo `monday.py check-scope` (G5) e Interface Integrity (P7).
5. **Revisar**: revisión independiente de calidad y contrato (`monday-reviewer`).
6. **Reportar**: generar `.monday/reports/<id>.yaml` con evidencia verificable (status: DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, BLOCKED, ESCALATE, FAILED).

## Instalación

```bash
git clone https://github.com/Admes7a431-2408/AgentForge.git && cd AgentForge
bash install.sh --dry-run          # ver qué haría
bash install.sh                    # enlaza la skill en ~/.claude y ~/.gemini
bash install.sh --claude --agents  # solo Claude Code + subagentes monday-*
bash install.sh --check            # audita enlaces, agentes monday-* y residuos legacy (solo lectura)
bash install.sh --help
```

Nunca sobrescribe: si el destino existe y no es un enlace a este repositorio, lo omite.

### Purga de agentes obsoletos

```bash
bash install.sh --purge-legacy --dry-run
bash install.sh --purge-legacy
```

Retira de forma segura las definiciones obsoletas de `~/.claude/agents/` respaldando los archivos regulares y desvinculando enlaces heredados.

## Quickstart

```bash
python3 scripts/monday.py init /ruta/a/mi/proyecto      # crea .monday/{CONTEXT.md,contracts,reports}
python3 scripts/monday.py cap status
python3 scripts/monday.py tier DEEP --platform claude-code
python3 scripts/monday.py validate .monday/contracts/mi-tarea.yaml
python3 scripts/monday.py check-scope .monday/contracts/mi-tarea.yaml
```

## Reversibilidad

```bash
bash install.sh --uninstall --dry-run
bash install.sh --uninstall
```

Solo elimina enlaces simbólicos que apuntan a este repositorio; cualquier otro archivo se deja intacto. Instalar y desinstalar son idempotentes.

## Requisitos

- Python 3 y PyYAML (`pip install pyyaml`)
- bash, git
- Claude Code y/o Antigravity

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Limitaciones conocidas

- La instalación usa symlinks: requiere un sistema de archivos que los soporte (Linux/macOS).
- `check-scope` depende de git y de que el contrato esté commiteado.
- El Interface Integrity Gate valida declaraciones en contratos y reportes, no analiza código.
- Una skill no puede cambiar el modelo de la sesión en curso; se delega mediante subagentes.

## Acknowledgements & Technical References

Monday fue diseñado e implementado de forma independiente (evolucionado a partir de la base de AgentForge), inspirándose en patrones conceptuales y arquitecturas de proyectos pioneros del ecosistema open-source:

### Metodología y Calidad de Ingeniería
- [obra/superpowers](https://github.com/obra/superpowers) (por Jesse Vincent — MIT): inspiración en el estándar de evidencia fresca antes de declarar éxito, revisión independiente en dos ejes (contrato vs calidad) y gobierno de tareas.
- [mattpocock/skills](https://github.com/mattpocock/skills) (por Matt Pocock — MIT): inspiración en el feedback loop temprano con comandos red-capable, debugging sistemático por hipótesis y restricciones de vocabulario en glosario.
- [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) (por Multica AI — MIT): inspiración en los principios fundamentales de simplicidad, cambios quirúrgicos y rigor proporcional a la tarea.

### Enrutamiento de Modelos y Delegación
- [nobodyohm-web/claude-code-model-router](https://github.com/nobodyohm-web/claude-code-model-router) (por nobodyohm-web — MIT): inspiración en la jerarquía abstracta de tiers cognitivos (`FAST`, `STANDARD`, `DEEP`, `MAX`), esfuerzo como palanca independiente y perfiles de postura.
- [BearGare/claude-skills](https://github.com/BearGare/claude-skills) (por BearGare): estudio conceptual de límites de profundidad de delegación, contención de desvío de alcance y reporte honesto de estados no verificados.
- [shaaz1000/claude-router](https://github.com/shaaz1000/claude-router) (por shaaz1000 — MIT): inspiración en la distinción entre complejidad real de la tarea y volumen de texto pegado, y vías de escalamiento explícito (`ESCALATE`).

*Nota: Todo el código fuente, scripts, plantillas de contratos y documentación de Monday fueron redactados e implementados originalmente. La mención de estos proyectos constituye reconocimiento técnico e intelectual, y no implica patrocinio, respaldo, afiliación ni autoría compartida.*

## Licencia

Distribuido bajo los términos de la [Licencia MIT](LICENSE).  
Copyright (c) 2026 Admes.

