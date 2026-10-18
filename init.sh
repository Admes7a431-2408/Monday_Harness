#!/usr/bin/env bash
# init.sh — validación del proyecto (Monday). Uso: ./init.sh [--full]
# Ejecútalo antes de escribir código y antes de cerrar una tarea. Si falla, detente y reporta.
# Este archivo pertenece al proyecto: configura aquí tus comprobaciones.
set -uo pipefail
cd "$(dirname "$0")"

# Comprobaciones rápidas (cada `./init.sh`): linter, type-check, tests unitarios rápidos.
QUICK_CHECKS=(
  "python3 -m py_compile core/monday.py"
  "bash -n init.sh"
  "bash -n core/templates/init.sh"
  "python3 -m unittest discover -s tests -q"
)
# Comprobaciones completas (`./init.sh --full`): suite completa, e2e/UI (p. ej. "npx playwright test").
FULL_CHECKS=(
  "bash tests/e2e_adapters.sh"   # agentes reales: requiere claude/agy con sesión; consume tokens
)

if ! command -v python3 >/dev/null 2>&1; then
  echo "FAIL: python3 no está disponible; Monday no puede verificar el proyecto." >&2
  exit 1
fi
python3 .monday/monday.py check || exit 1

checks=("${QUICK_CHECKS[@]}")
[[ "${1:-}" == "--full" ]] && checks+=("${FULL_CHECKS[@]}")
if [[ ${#checks[@]} -eq 0 ]]; then
  echo "UNAVAILABLE: no hay comprobaciones del proyecto configuradas en init.sh (solo se verificó el harness)."
  exit 0
fi

failed=0
for c in "${checks[@]}"; do
  out=$(bash -c "$c" 2>&1); rc=$?
  if [[ $rc -eq 0 ]]; then echo "PASS: $c"
  elif [[ $rc -eq 126 || $rc -eq 127 ]]; then echo "UNAVAILABLE: $c (exit $rc)"; echo "$out" | tail -n 5; failed=1
  else echo "FAIL: $c (exit $rc)"; echo "$out" | tail -n 20; failed=1
  fi
done
exit $failed
