#!/usr/bin/env bash
# Instala Monday como skill enlazada (una sola fuente de verdad: este directorio).
#   ./install.sh [--claude] [--antigravity] [--agents] [--check] [--purge-legacy] [--uninstall] [--dry-run] [-h|--help]
# Sin flags de plataforma actúa sobre ambas. Nunca sobrescribe: si el destino existe y no es
# un enlace a este directorio, lo informa y lo deja intacto. --uninstall elimina únicamente
# los enlaces que apuntan a Monday (y enlaces heredados que apunten a este repo).
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"  # ruta física, comparable con readlink -f
claude=0; agy=0; agents=0; dry=0; uninstall=0; check=0; purge_legacy=0

usage() {
  cat <<EOF
uso: $0 [--claude] [--antigravity] [--agents] [--check] [--purge-legacy] [--uninstall] [--dry-run] [-h|--help]

  --claude        enlaza la skill en ~/.claude/skills/monday
  --antigravity   enlaza la skill en ~/.gemini/config/skills/monday
  --agents        enlaza adapters/claude-code/agents/*.md en ~/.claude/agents/
  --check         audita el estado de enlaces y detecta residuos obsoletos (sin efectos secundarios)
  --purge-legacy  respalda y retira los agentes obsoletos (reviewer, scout, worker, af-*) de ~/.claude/agents/
  --uninstall     elimina solo los enlaces que apuntan a este directorio
  --dry-run       muestra lo que haría sin modificar nada
  -h, --help      muestra esta ayuda

Sin --claude ni --antigravity se actúa sobre ambas plataformas.
Las opciones --check, --purge-legacy y --uninstall son mutuamente excluyentes;
--check y --purge-legacy actúan sobre todo y no admiten --claude, --antigravity ni --agents.
EOF
}

for a in "$@"; do
  case "$a" in
    --claude) claude=1 ;;
    --antigravity) agy=1 ;;
    --agents) agents=1 ;;
    --check) check=1 ;;
    --purge-legacy) purge_legacy=1 ;;
    --uninstall) uninstall=1 ;;
    --dry-run) dry=1 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done

# Validación estricta de opciones mutuamente excluyentes
action_modes=$(( check + purge_legacy + uninstall ))
if (( action_modes > 1 )); then
  echo "error: las opciones --check, --purge-legacy y --uninstall son mutuamente excluyentes." >&2
  exit 2
fi
# --check y --purge-legacy actúan siempre sobre todo; aceptar flags de plataforma haría creer que se instaló algo.
if (( (check || purge_legacy) && (claude || agy || agents) )); then
  echo "error: --check y --purge-legacy no se combinan con --claude, --antigravity ni --agents." >&2
  exit 2
fi

run() { if (( dry )); then echo "[dry-run] $*"; else "$@"; fi; }

# Lista cerrada de definiciones obsoletas que --purge-legacy puede retirar de ~/.claude/agents/.
LEGACY_AGENTS=(reviewer.md scout.md worker.md af-reviewer.md af-scout.md af-worker.md)

# agent_ok <destino> <origen>: el destino es un enlace a <origen>, este es un archivo regular legible y su
# frontmatter declara `name:` igual al nombre del archivo, que es lo que Claude Code usa para registrar el agente.
agent_ok() {
  local dst="$1" src="$2" name
  [[ -L "$dst" && "$(readlink -f "$dst")" == "$src" && -f "$src" && -r "$src" ]] || return 1
  name="$(awk 'NR == 1 && $0 != "---" { exit } NR > 1 && $0 == "---" { exit }
               NR > 1 && /^name:/ { sub(/^name:[ \t]*/, ""); sub(/[ \t\r]+$/, ""); print; exit }' "$src")"
  [[ "$name" == "$(basename "$src" .md)" ]]
}

check_status() {
  local ok=1
  echo "=== Auditoría de instalación de Monday ==="

  # Comprobación de skill en Claude
  local cs="$HOME/.claude/skills/monday"
  if [[ -L "$cs" && "$(readlink -f "$cs")" == "$SRC" ]]; then
    echo "ok      skill claude: $cs -> $SRC"
  elif [[ -e "$cs" || -L "$cs" ]]; then
    echo "aviso   skill claude: $cs existe pero no apunta a $SRC"
    ok=0
  else
    echo "falta   skill claude: $cs no está enlazado"
    ok=0
  fi

  # Residuos legacy de AgentForge en Claude
  local legacy_cs="$HOME/.claude/skills/agentforge"
  if [[ -e "$legacy_cs" || -L "$legacy_cs" ]]; then
    echo "alerta  skill legacy detectada: $legacy_cs (retirar con --uninstall en AgentForge o manualmente)"
    ok=0
  fi

  # Comprobación de skill en Antigravity
  local as="$HOME/.gemini/config/skills/monday"
  if [[ -L "$as" && "$(readlink -f "$as")" == "$SRC" ]]; then
    echo "ok      skill antigravity: $as -> $SRC"
  elif [[ -e "$as" || -L "$as" ]]; then
    echo "aviso   skill antigravity: $as existe pero no apunta a $SRC"
    ok=0
  else
    echo "falta   skill antigravity: $as no está enlazado"
    ok=0
  fi

  # Residuos legacy de AgentForge en Antigravity
  local legacy_as="$HOME/.gemini/config/skills/agentforge"
  if [[ -e "$legacy_as" || -L "$legacy_as" ]]; then
    echo "alerta  skill legacy detectada: $legacy_as (retirar con --uninstall en AgentForge o manualmente)"
    ok=0
  fi

  # Comprobación de agentes monday-*
  for f in "$SRC"/adapters/claude-code/agents/*.md; do
    local base; base="$(basename "$f")"
    local dst="$HOME/.claude/agents/$base"
    if agent_ok "$dst" "$f"; then
      echo "ok      agente: $dst -> $f"
    elif [[ -L "$dst" && "$(readlink -f "$dst")" == "$f" ]]; then
      echo "aviso   agente: $dst enlaza bien, pero $f es ilegible o su frontmatter no declara name: ${base%.md}"
      ok=0
    elif [[ -e "$dst" || -L "$dst" ]]; then
      echo "aviso   agente: $dst existe pero no apunta a $f"
      ok=0
    else
      echo "falta   agente: $dst no está enlazado"
      ok=0
    fi
  done

  # Detección de agentes legacy en ~/.claude/agents/
  local legacy_found=0
  for name in "${LEGACY_AGENTS[@]}"; do
    local leg="$HOME/.claude/agents/$name"
    if [[ -e "$leg" || -L "$leg" ]]; then
      echo "alerta  agente legacy detectado: $leg (retirar con --purge-legacy)"
      legacy_found=1
      ok=0
    fi
  done
  if (( ! legacy_found )); then
    echo "ok      agentes legacy: ausentes (limpio)"
  fi

  # Comprobación de PyYAML (-B: no escribir bytecode; --check es de solo lectura)
  if python3 -B -c 'import yaml' 2>/dev/null; then
    echo "ok      entorno: python3 + PyYAML disponible"
  else
    echo "aviso   entorno: PyYAML no disponible (pip install pyyaml)"
    ok=0
  fi

  if (( ok )); then
    echo "Estado global: COMPLETO Y SALUDABLE"
    return 0
  else
    echo "Estado global: CON DISCREPANCIAS O RESIDUOS DETECTADOS"
    return 1
  fi
}

do_purge_legacy() {
  echo "=== Purga segura de agentes legacy ==="
  local agents_dir="$HOME/.claude/agents" f t b name
  # Fase 1 — precondiciones, sin tocar nada. Cualquier fallo aborta antes de crear o borrar archivos.
  if [[ -L "$agents_dir" || ! -d "$agents_dir" ]]; then
    echo "error: $agents_dir no es un directorio real (enlace simbólico o ausente). No se ha modificado nada." >&2
    return 1
  fi
  for f in "$SRC"/adapters/claude-code/agents/*.md; do
    if ! agent_ok "$agents_dir/$(basename "$f")" "$f"; then
      echo "error: agente oficial $agents_dir/$(basename "$f") ausente o no saludable. Abortando purga por seguridad; no se ha modificado nada." >&2
      return 1
    fi
  done
  local -a targets=()
  local -a symlink_targets=()
  for name in "${LEGACY_AGENTS[@]}"; do
    t="$agents_dir/$name"
    if [[ -L "$t" ]]; then
      local link_dest real_src
      link_dest="$(readlink -f "$t")"
      real_src="$(readlink -f "$SRC")"
      if [[ "$link_dest" == "$real_src"/* ]]; then
        symlink_targets+=("$t")
      else
        echo "error: $t es un enlace simbólico que no apunta a $SRC. Se rechaza para evitar desreferenciación accidental; no se ha modificado nada." >&2
        return 1
      fi
    elif [[ -e "$t" && ! -f "$t" ]]; then
      echo "error: $t no es un archivo regular. Abortando; no se ha modificado nada." >&2
      return 1
    elif [[ -f "$t" && ! -r "$t" ]]; then
      echo "error: $t no es legible; no se podría respaldar. Abortando; no se ha modificado nada." >&2
      return 1
    elif [[ -f "$t" ]]; then
      targets+=("$t")
    else
      echo "ok         $t (no existe)"
    fi
  done
  if (( ${#targets[@]} == 0 && ${#symlink_targets[@]} == 0 )); then
    echo "No se encontraron agentes legacy para purgar."
    return 0
  fi

  local backup_dir="$HOME/.claude/backups/legacy-agents-$(date +%Y%m%d-%H%M%S)"
  if (( dry )); then
    for t in "${targets[@]}"; do
      echo "[dry-run] respaldaría $t -> $backup_dir/$(basename "$t") (sujeto a verificación cmp)"
      echo "[dry-run] purgaría    $t"
    done
    for s in "${symlink_targets[@]}"; do
      echo "[dry-run] retiraría enlace legacy $s -> $(readlink "$s")"
    done
    echo "[dry-run] Simulación completada. Ningún archivo fue modificado ni eliminado."
    return 0
  fi

  # Fase 2 — respaldo verificado de todos los archivos regulares antes de borrar ninguno.
  if (( ${#targets[@]} > 0 )); then
    if [[ -e "$backup_dir" || -L "$backup_dir" ]]; then
      echo "error: el directorio de respaldo $backup_dir ya existe. Abortando para evitar sobrescrituras; no se ha modificado nada." >&2
      return 1
    fi
    if ! mkdir -p -- "$(dirname "$backup_dir")" || ! mkdir -- "$backup_dir"; then
      echo "error: no se pudo crear el directorio de respaldo nuevo $backup_dir (ya existe o sin permisos). No se ha modificado nada." >&2
      return 1
    fi
    for t in "${targets[@]}"; do
      b="$backup_dir/$(basename "$t")"
      if ! cp -P -p -- "$t" "$b" || ! cmp -s -- "$t" "$b"; then
        echo "error: no se pudo respaldar o verificar $t -> $b. No se ha borrado ningún original; respaldo parcial en $backup_dir." >&2
        return 1
      fi
      echo "respaldado $t -> $b (integridad verificada con cmp)"
    done
  fi

  # Fase 3 — borrado.
  local failed=0
  for t in "${targets[@]}"; do
    b="$backup_dir/$(basename "$t")"
    if [[ -f "$t" && ! -L "$t" ]] && cmp -s -- "$t" "$b" && rm -f -- "$t" && [[ ! -e "$t" && ! -L "$t" ]]; then
      echo "purgado    $t"
    else
      echo "error: no se pudo purgar $t (cambió tras el respaldo o falló el borrado); se conserva." >&2
      failed=1
    fi
  done
  for s in "${symlink_targets[@]}"; do
    if rm -f -- "$s"; then
      echo "retirado enlace legacy $s"
    else
      echo "error: no se pudo retirar el enlace legacy $s" >&2
      failed=1
    fi
  done
  if (( failed )); then
    echo "Purga legacy INCOMPLETA." >&2
    return 1
  fi
  if (( ${#targets[@]} > 0 )); then
    echo "Purga legacy completada con éxito. Respaldo conservado en: $backup_dir"
  else
    echo "Purga legacy completada con éxito (enlaces obsoletos retirados)."
  fi
}

if (( check )); then
  check_status
  exit $?
fi

if (( purge_legacy )); then
  do_purge_legacy
  exit $?
fi

(( claude || agy )) || { claude=1; agy=1; }

link() {  # link <destino> <origen>
  local dst="$1" target="$2"
  if [[ -L "$dst" && "$(readlink -f "$dst")" == "$(readlink -f "$target")" ]]; then
    echo "ok      $dst (ya enlazado)"
  elif [[ -e "$dst" || -L "$dst" ]]; then
    echo "omitido $dst existe y no apunta a $target; revísalo a mano" >&2
  else
    run mkdir -p "$(dirname "$dst")"
    run ln -s "$target" "$dst"
    echo "enlazado $dst -> $target"
  fi
}

unlink_ours() {  # unlink_ours <destino> <origen>: solo borra si es un enlace a <origen>
  local dst="$1" target="$2"
  if [[ -L "$dst" && "$(readlink -f "$dst")" == "$(readlink -f "$target")" ]]; then
    run rm "$dst"
    echo "eliminado $dst"
  elif [[ -e "$dst" || -L "$dst" ]]; then
    echo "omitido $dst no apunta a $target; no se toca" >&2
  else
    echo "ok      $dst (no existe)"
  fi
}

if (( uninstall )); then
  act=unlink_ours
  # Cuando se desinstala, también retira enlaces heredados de agentforge si apuntaban a este repo
  "$act" "$HOME/.claude/skills/agentforge" "$SRC"
  "$act" "$HOME/.gemini/config/skills/agentforge" "$SRC"
else
  act=link
fi

(( claude )) && "$act" "$HOME/.claude/skills/monday" "$SRC"
(( agy )) && "$act" "$HOME/.gemini/config/skills/monday" "$SRC"

if (( agents )); then
  (( uninstall )) || run mkdir -p "$HOME/.claude/agents"
  for f in "$SRC"/adapters/claude-code/agents/*.md; do
    "$act" "$HOME/.claude/agents/$(basename "$f")" "$f"
  done
  if (( uninstall )); then
    real_src="$(readlink -f "$SRC")"
    for old_agent in af-reviewer.md af-scout.md af-worker.md; do
      old_dst="$HOME/.claude/agents/$old_agent"
      if [[ -L "$old_dst" ]]; then
        old_target="$(readlink -f "$old_dst")"
        if [[ "$old_target" == "$real_src"/* ]]; then
          run rm "$old_dst"
          echo "eliminado enlace legacy $old_dst"
        fi
      fi
    done
  fi
fi

if (( ! uninstall )); then
  python3 -c 'import yaml' 2>/dev/null || echo "aviso: scripts/monday.py necesita PyYAML (pip install pyyaml)" >&2
fi
