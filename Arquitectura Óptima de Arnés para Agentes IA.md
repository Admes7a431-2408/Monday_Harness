# Guía de Implementación: Arquitectura Óptima de Arnés para Agentes IA

Este documento unifica los principios de *Harness Engineering* expuestos por Benjamín Cordero y BettaTech, consolidando los consensos estratégicos e integrando las mejores prácticas técnicas de ambos para mejorar tu propio arnés.

---

## 1. Núcleo Común: Los Cimientos Innegociables

Ambos análisis coinciden en cinco principios que deben regir cualquier sistema de agentes:

* **El repositorio es el sistema (agnóstico al modelo):** El modelo de IA es una pieza intercambiable ("el caballo"); el arnés (archivos, reglas, flujos y validaciones en tu repositorio) es tu activo permanente. No ates tu flujo de trabajo a un proveedor específico.
* **Minimalismo de herramientas (Regla Vercel D0):** Sobrecargar al agente con herramientas hiperespecializadas degrada su razonamiento. Prioriza herramientas nativas del sistema (Bash, `grep`, `cat`, `ls`) sobre wrappers complejos. Menos herramientas = menor latencia, menor gasto de tokens y mayor tasa de acierto.
* **Mitigación de la degradación temprana:** El rendimiento de los modelos cae a partir del 20%–40% de ocupación de su ventana de contexto. La memoria no debe vivir en el historial del chat, sino en archivos físicos dentro del proyecto.
* **Orquestación multiagente de contextos limpios:** Un agente monolítico fracasa en tareas largas. Se requiere un agente líder que delegue tareas específicas a subagentes con contextos nuevos y aislados.
* **Verificación empírica y automejora (*Self-improving Loop*):** Nunca confíes en la confirmación verbal del agente. El cierre de una tarea exige pasar pruebas automatizadas, y los errores recurrentes deben traducirse en actualizaciones a las reglas del propio arnés.

---

## 2. Síntesis de Diferencias: Lo Mejor de Cada Enfoque

Para construir un arnés superior, combinamos la **visión estratégica y de costes** del Informe 1 con la **estructura táctica de archivos y automatización** del Informe 2:

| Componente | Aporte Clave de Benjamín Cordero (Informe 1) | Aporte Clave de BettaTech (Informe 2) | Estándar Unificado para tu Arnés |
| --- | --- | --- | --- |
| **Punto de entrada (`agents.md`)** | Uso del estándar abierto `agents.md` (en vez de `claude.md`) y **límite estricto de menos de 200 líneas** para no quemar tokens al arrancar. | Inclusión de un **mapa del repositorio** dentro del archivo para evitar escaneos ciegos del directorio. | Archivo `agents.md` menor a 200 líneas con protocolo de inicio y mapa de rutas clave. |
| **Roles y Costes Multiagente** | **Arbitraje de modelos:** usar modelos económicos/rápidos para implementar y modelos potentes (más caros) para auditar y orquestar. | **Rol de Explorador:** separar la investigación previa del código respecto a la escritura para no ensuciar el contexto del implementador. | 4 roles (Líder, Explorador, Implementador, Revisor) asignando el modelo según la exigencia cognitiva de cada rol. |
| **Memoria y Estado (`progress/`)** | Registro sistemático de decisiones fuera del chat para que cualquier agente retome el hilo al instante. | Separación física entre estado efímero (**`current.md`**) y registro permanente (**`history.md`**), más tareas estructuradas en **`features.json`**. | Carpeta `progress/` dividida en estado activo e historial, vinculada a un `features.json` con criterios de aceptación. |
| **Sistema de Verificación** | Verificación visual y funcional de extremo a extremo en interfaz usando **Playwright**. | Validación de entorno previa/posterior mediante **`init.sh`** (tests unitarios, linters) y **hooks de cierre** en el IDE/CLI. | Doble capa: `init.sh` + hooks para integridad de código y Playwright para validación de UI/flujos. |
| **Calidad del Código Base** | Enfoque en la estructura de archivos del arnés. | Énfasis en la **consistencia arquitectónica del proyecto**: código modular y predecible para que la IA replique buenos patrones. | Estandarizar convenciones en un archivo `architecture.md` de lectura obligatoria según la tarea. |

---

## 3. Estructura de Archivos Recomendada

Implementa este árbol en la raíz de tu proyecto para materializar el arnés:

```text
proyecto/
├── agents.md                # Punto de entrada (< 200 líneas): protocolo, reglas y mapa del repo
├── init.sh                  # Script de validación: entorno, linters, type-check y tests unitarios
├── features.json            # Backlog estructurado: id, descripción, criterios de aceptación y estado
├── docs/
│   └── architecture.md      # Convenciones de código y patrones de diseño del proyecto
├── progress/
│   ├── current.md           # Estado de la tarea en curso (evita el "teléfono descompuesto")
│   ├── exploration_logs.md  # Hallazgos del agente explorador (dependencias, archivos afectados)
│   └── history.md           # Changelog de tareas completadas y decisiones arquitectónicas
└── .agents/ (o .claude/)    # Definiciones de subagentes y hooks
    ├── leader.md            # Orquestador (Modelo de alto razonamiento)
    ├── explorer.md          # Investigador de lectura exclusiva (Modelo rápido/económico)
    ├── implementer.md       # Escritor de código y tests (Modelo intermedio/rápido)
    └── reviewer.md          # Auditor de calidad y actualizador del arnés (Modelo de alto razonamiento)

```

---

## 4. Plan de Implementación Paso a Paso

### Fase 1: Gobernanza y Punto de Entrada

1. **Redacta `agents.md` (máximo 200 líneas):**
* Define el mapa básico del repositorio (dónde está la lógica, dónde van los tests, dónde está la documentación).
* Establece la regla de oro: *"Antes de escribir cualquier línea de código, ejecuta `./init.sh`. Si falla, detente y reporta el error"*.
* Prohíbe dar una tarea por terminada (`done`) sin haber pasado `./init.sh` y la revisión del agente auditor.



### Fase 2: Script de Control y Automatización (`init.sh` + Hooks)

1. **Construye `init.sh`:**
* Verifica que existan `agents.md`, `features.json` y la carpeta `progress/`.
* Ejecuta el linter, el verificador de tipos y la batería de tests rápidos.


2. **Configura un Hook de salida:**
* Añade un hook en tu herramienta (ej. Claude Code) que dispare `./init.sh` al cerrar la sesión o al finalizar un subagente, garantizando que el repositorio nunca quede en un estado roto.



### Fase 3: Flujo de Memoria Externa

1. **Estandariza `features.json`:** Define cada tarea con `id`, `title`, `status` (`pending`, `in_progress`, `done`) y `acceptance_criteria` claros y verificables.
2. **Aplica el protocolo de traspaso en `progress/`:**
* Al tomar una tarea, el agente pasa su estado a `in_progress` y documenta el plan en `progress/current.md`.
* Al terminar y validar, mueve el resumen técnico a `progress/history.md` y limpia `current.md`.



### Fase 4: Despliegue de Subagentes y Verificación Avanzada

1. **Configura los 4 roles con asignación eficiente de modelos:**
* **Líder:** Lee `features.json` y `progress/current.md`, decide qué subagente invocar y mantiene su propio contexto libre de código fuente.
* **Explorador:** Busca con herramientas Unix (`grep`/`find`) qué archivos tocar y deja el reporte en `progress/exploration_logs.md`.
* **Implementador:** Lee solo el reporte de exploración y `docs/architecture.md`, escribe el código/tests y corre `./init.sh`.
* **Revisor:** Audita el *diff* contra las convenciones, ejecuta `init.sh` (y Playwright si hay cambios en UI) y aprueba o rechaza.


2. **Cierra el ciclo de automejora:** Incluye en el prompt del **Revisor** la instrucción: *"Si detectas que el Implementador cometió un error de patrón repetitivo, añade una regla preventiva concisa en `docs/architecture.md` o `agents.md`"*.
