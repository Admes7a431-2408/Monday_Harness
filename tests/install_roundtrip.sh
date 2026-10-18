#!/usr/bin/env bash
# Instala Monday en un directorio vacío, comprueba init.sh y revierte con rollback --all.
# Éxito solo si el directorio queda exactamente como estaba (vacío).
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
dir="$(mktemp -d)"
trap 'rm -rf "$dir"' EXIT

python3 "$repo/core/monday.py" install "$dir" >/dev/null
(cd "$dir" && ./init.sh >/dev/null)
python3 "$repo/core/monday.py" install "$dir" | grep -q "sin cambios"
python3 "$dir/.monday/monday.py" rollback "$dir" --all >/dev/null
left="$(find "$dir" -mindepth 1 | head -5)"
if [[ -n "$left" ]]; then
  echo "FAIL: quedan restos tras rollback --all:"; echo "$left"; exit 1
fi
echo "PASS: install → init.sh → reinstall idempotente → rollback --all deja el directorio vacío"
