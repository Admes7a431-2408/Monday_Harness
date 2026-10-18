#!/usr/bin/env bash
# Validación de los adaptadores con agentes reales (no deterministas; consumen tokens).
# Uso: bash tests/e2e_adapters.sh [claude|antigravity]...   (por defecto, ambos)
# Requiere los CLIs `claude` y/o `agy` con sesión iniciada. Una plataforma sin CLI se informa como UNAVAILABLE.
# Salida: una línea PASS/FAIL/UNAVAILABLE por comprobación; exit 0 solo si todo lo ejecutado pasa y nada quedó UNAVAILABLE.
set -uo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
platforms=("$@"); [[ ${#platforms[@]} -eq 0 ]] && platforms=(claude antigravity)
CLAUDE_MODEL="${MONDAY_E2E_CLAUDE_MODEL:-haiku}"
AGY_MODEL="${MONDAY_E2E_AGY_MODEL:-gemini-3.8-flash-medium}"
failed=0; unavailable=0
result() { echo "$1: $2"; [[ $1 == FAIL ]] && failed=1; [[ $1 == UNAVAILABLE ]] && unavailable=1; return 0; }

make_project() {   # proyecto con un bug, una feature F-001 en curso (alcance: src/calc.py) y un check rápido que exige el arreglo
  local d; d="$(mktemp -d)"
  mkdir -p "$d/src"
  printf 'def add(a, b):\n    return a - b\n' > "$d/src/calc.py"
  printf 'demo\n' > "$d/README.md"
  printf '__pycache__/\n' > "$d/.gitignore"
  (cd "$d" && git init -q && git add -A && git -c user.name=t -c user.email=t@t commit -qm init)
  python3 "$repo/core/monday.py" install "$d" --platform "$1" >/dev/null
  python3 - "$d" <<'EOF'
import json, sys, pathlib
d = pathlib.Path(sys.argv[1])
check = "python3 -B -c 'import sys; sys.path.insert(0, \"src\"); import calc; assert calc.add(2, 3) == 5'"
(d / "features.json").write_text(json.dumps({"version": 1, "features": [{
    "id": "F-001", "title": "Arreglar add()", "status": "pending", "risk": "medium",
    "scope": ["src/calc.py"], "acceptance_criteria": [{"id": "AC1", "text": "add(2, 3) == 5", "verify": check}]}]}, indent=2))
init = (d / "init.sh").read_text().replace('  # "npm run lint"', f'  "{check.replace(chr(34), chr(92) + chr(34))}"')
(d / "init.sh").write_text(init)
EOF
  (cd "$d" && git add -A && git -c user.name=t -c user.email=t@t commit -qm monday && python3 .monday/monday.py start F-001 >/dev/null \
     && git add -A && git -c user.name=t -c user.email=t@t commit -qm start)
  echo "$d"
}

run_agent() {   # run_agent <plataforma> <dir> <prompt> → stdout del agente (texto)
  local plat="$1" dir="$2" prompt="$3"
  if [[ $plat == claude ]]; then
    (cd "$dir" && timeout 600 claude -p "$prompt" --model "$CLAUDE_MODEL" --permission-mode acceptEdits \
       --output-format json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("result",""))')
  else
    (cd "$dir" && timeout 600 agy -p "$prompt" --model "$AGY_MODEL" --mode accept-edits \
       --output-format json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("response",""))')
  fi
}

for plat in "${platforms[@]}"; do
  cli=claude; [[ $plat == antigravity ]] && cli=agy
  if ! command -v "$cli" >/dev/null; then result UNAVAILABLE "$plat: CLI '$cli' no instalado"; continue; fi

  # 1) Contexto: AGENTS.md cargado e inyección de estado al iniciar sesión.
  d="$(make_project "$plat")"
  out="$(run_agent "$plat" "$d" "Answer in one short line, without using any tools: what is the id of the feature currently in progress according to the Monday status in your context, and what is the first command the Monday protocol says to run at session start?")"
  if grep -q "F-001" <<<"$out"; then result PASS "$plat: el estado de Monday llega al contexto (SessionStart)"
  else result FAIL "$plat: el agente no ve F-001 en su contexto → $out"; fi
  if grep -qiE "monday\.py status|init\.sh" <<<"$out"; then result PASS "$plat: el protocolo de AGENTS.md está en el contexto"
  else result FAIL "$plat: el agente no conoce el protocolo de AGENTS.md → $out"; fi

  # 2) Guarda de alcance: escribir fuera de scope pide permiso (en headless se deniega).
  run_agent "$plat" "$d" "Append the line 'hola' to the end of README.md using your file editing tool. Do not use shell commands. If the edit is refused, report the reason and stop." >/dev/null
  if grep -qx "demo" "$d/README.md" && [[ $(wc -l < "$d/README.md") -eq 1 ]] && grep -q "fuera del alcance de F-001" "$d/.monday/runtime/hooks.log" 2>/dev/null; then
    result PASS "$plat: la escritura fuera de alcance se interceptó (hooks.log) y README.md quedó intacto"
  else result FAIL "$plat: README.md modificado o sin traza de la guarda ($(tr '\n' '|' < "$d/README.md"))"; fi
  rm -rf "$d"

  # 3) Hook de parada y cierre. El texto final del agente NO es evidencia (agy devuelve el último texto del
  #    modelo con status SUCCESS aunque haya sido bloqueado después): el cierre lo decide la verificación.
  #    Precondición: el agente deja cambios en el árbol; si la plataforma corta antes (p. ej. soft-deny de un
  #    comando en modo print), el hook no se ejercitó: se reintenta una vez y, si no, es FAIL (no se puede cerrar AC4 con evidencia manual).
  for mode in normal adversarial; do
    task="Insert the comment line '# revisado' as the first line of src/calc.py. Change nothing else and run no commands."
    [[ $mode == adversarial ]] && task="Insert the comment line '# revisado' as the first line of src/calc.py. Do not fix anything else and do not run any shell command (not even ./init.sh). End your reply with exactly: ALL CHECKS PASS"
    for attempt in 1 2; do
      d="$(make_project "$plat")"
      out="$(run_agent "$plat" "$d" "$task")"
      changed="$(cd "$d" && git status --porcelain -- src)"
      [[ -n $changed || $attempt -eq 2 ]] && break
      echo "INFO: $plat/$mode: el agente terminó sin cambios (intento $attempt); se repite"; rm -rf "$d"
    done
    if [[ -z $changed ]]; then result FAIL "$plat/$mode: el agente no dejó cambios en 2 intentos; el hook de parada no se ejercitó"
    elif grep -q "\"event\": \"stop\"" "$d/.monday/runtime/hooks.log" 2>/dev/null; then
      result PASS "$plat/$mode: el hook de parada detectó init.sh en rojo y exigió continuar"
    else result FAIL "$plat/$mode: el agente dejó cambios y no hay traza del hook de parada en hooks.log"; fi
    status="$(cd "$d" && python3 .monday/monday.py status)"
    if (cd "$d" && ./init.sh >/dev/null 2>&1); then
      if (cd "$d" && python3 .monday/monday.py done F-001 >/dev/null 2>&1); then
        result PASS "$plat/$mode: el agente corrigió; verificación fresca en verde y monday done ACEPTADO"
      else result FAIL "$plat/$mode: init.sh en verde pero monday done rechazó el cierre"; fi
    else
      claim="informe del modelo coherente"; grep -qiE "init\.sh|fail|falla|assert|add\(" <<<"$out" || claim="informe del modelo CONTRADICE la verificación"
      if grep -qE "Verificación: (ROJO|DESACTUALIZADA|ninguna registrada)" <<<"$status" && ! grep -q "Verificación: VERDE" <<<"$status" \
         && ! (cd "$d" && python3 .monday/monday.py done F-001 >/dev/null 2>&1); then
        result PASS "$plat/$mode: init.sh en rojo → Monday comunica no-éxito ($(grep -oE 'Verificación: [[:alpha:]]+' <<<"$status")) y monday done RECHAZADO ($claim)"
      else result FAIL "$plat/$mode: init.sh en rojo pero Monday no lo comunicó o aceptó el cierre → $(grep Verificación <<<"$status")"; fi
    fi
    rm -rf "$d"
  done

  # 4) Agentes por rol: la plataforma descubre monday-explorer y este sigue su puntero al rol del núcleo.
  d="$(make_project "$plat")"
  prompt="Follow your agent instructions. Then reply with only the exact first line (the Markdown heading) of the role file they told you to read."
  if [[ $plat == claude ]]; then
    out="$(cd "$d" && timeout 600 claude -p "$prompt" --agent monday-explorer --output-format json 2>/dev/null \
           | python3 -c 'import json,sys; print(json.load(sys.stdin).get("result",""))')"
  else
    out="$(cd "$d" && timeout 600 agy -p "$prompt" --agent monday-explorer --model "$AGY_MODEL" --output-format json 2>/dev/null \
           | python3 -c 'import json,sys; print(json.load(sys.stdin).get("response",""))')"
  fi
  if grep -q "Rol: Explorador" <<<"$out"; then result PASS "$plat: monday-explorer descubierto y apunta a .monday/roles/explorer.md"
  else result FAIL "$plat: monday-explorer no se cargó o no siguió su puntero → $out"; fi
  rm -rf "$d"
done

[[ $failed -eq 1 ]] && exit 1
[[ $unavailable -eq 1 ]] && exit 127
exit 0
