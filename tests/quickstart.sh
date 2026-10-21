#!/usr/bin/env bash
# Sigue los pasos de "Getting started" y "Everyday use" del README desde una carpeta limpia.
# Mantenlo sincronizado con el README: si cambia un comando allí, cambia aquí.
# Uso: bash tests/quickstart.sh [url-del-repositorio [rama-o-tag]]   (por defecto: clon de este repositorio local, HEAD)
#   p. ej. bash tests/quickstart.sh https://github.com/Admes7a431-2408/Monday_Harness.git v1.0.0
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
src="${1:-file://$repo}"; ref="${2:-}"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
cd "$work"
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@example.invalid GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@example.invalid
step() { echo "· $*"; }

step "clonar Monday fuera del proyecto (copia limpia, sin estado local): $src ${ref:-HEAD}"
git clone -q --depth 1 ${ref:+--branch "$ref"} "$src" monday
test ! -e monday/core/runtime -a ! -e monday/core/backups
step "Monday $(cat monday/core/VERSION) · commit $(git -C monday rev-parse HEAD)"

step "proyecto de ejemplo con un bug"
mkdir -p project/src && cd project && git init -q
printf 'def add(a, b):\n    return a - b\n' > src/calc.py
printf '__pycache__/\n' > .gitignore
git add -A && git commit -qm init && cd ..

step "install --dry-run no escribe nada"
python3 monday/core/monday.py install "$work/project" --dry-run >/dev/null
test ! -e project/.monday

step "install (ambas plataformas) e init.sh"
python3 monday/core/monday.py install "$work/project" >/dev/null
cd project
./init.sh >/dev/null
python3 .monday/monday.py check >/dev/null                # comprobar la instalación
python3 .monday/monday.py status | grep -q "Monday $(cat ../monday/core/VERSION)"
git add -A && git commit -qm monday

step "feature con un criterio ejecutable"
python3 - <<'EOF'
import json
d = json.load(open("features.json"))
d["features"].append({"id": "F-001", "title": "Fix add()", "status": "pending", "risk": "medium",
    "scope": ["src/calc.py"],
    "acceptance_criteria": [{"id": "AC1", "text": "add(2, 3) == 5",
        "verify": "python3 -B -c 'import sys; sys.path.insert(0, \"src\"); import calc; assert calc.add(2, 3) == 5'"}]})
json.dump(d, open("features.json", "w"), indent=2)
EOF
git add -A && git commit -qm feature
M="python3 .monday/monday.py"
$M start F-001 >/dev/null

step "verify falla antes del arreglo y done lo rechaza"
if $M verify F-001 >/dev/null; then echo "FAIL: verify pasó antes del arreglo"; exit 1; fi
if $M done F-001 >/dev/null; then echo "FAIL: done aceptó antes del arreglo"; exit 1; fi
$M status | grep -q "EN CURSO: F-001"                 # sigue abierta: el rechazo no se pierde

step "arreglo → verify y done aceptan"
printf 'def add(a, b):\n    return a + b\n' > src/calc.py
$M verify F-001 >/dev/null
$M done F-001 | grep -q ACEPTADO
$M status | grep -q "Verificación: VERDE"

step "rollback --all conserva el trabajo del proyecto y retira Monday"
$M rollback --all >/dev/null
test ! -e .monday/monday.py -a ! -e .claude/settings.json -a -e features.json -a -e src/calc.py

echo "PASS: quick start del README reproducido desde una carpeta limpia"
