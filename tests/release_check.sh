#!/usr/bin/env bash
# Comprobaciones previas a publicar una versión de Monday.
# Uso: bash tests/release_check.sh [ac4-contract|audit|version|history]...   (sin argumentos: todas)
# Salida: una línea PASS/FAIL por comprobación; exit 0 solo si todas pasan.
set -uo pipefail
cd "$(dirname "$0")/.."
checks=("$@"); [[ ${#checks[@]} -eq 0 ]] && checks=(ac4-contract audit version history)
failed=0
result() { echo "$1: $2"; [[ $1 == FAIL ]] && failed=1; return 0; }

# Estado publicado del repositorio predecesor observado con `git ls-remote` (2026-10-19). Si estos ids cambian, se reescribió historia.
PREDECESSOR_MAIN=2f3554d19d4d0d23360f4ece5266020aa410a95b
declare -A TAGS=([v0.1.0]=0a49df03df1e0907d47d8a3bd9419e4f125dbbee [v0.9.0]=f9ccc0cd8266499678f16a3444d0ee56a338f855)

for check in "${checks[@]}"; do
  case $check in
  ac4-contract)   # los criterios de M-001 siguen idénticos a su primera versión commiteada
    first=$(git log --diff-filter=A --format=%H -- features.json | tail -1)
    if python3 - "$first" <<'EOF'
import json, subprocess, sys
crit = lambda data: next(f for f in data["features"] if f["id"] == "M-001")["acceptance_criteria"]
original = json.loads(subprocess.run(["git", "show", f"{sys.argv[1]}:features.json"], capture_output=True, text=True, check=True).stdout)
current = json.load(open("features.json"))
sys.exit(0 if crit(original) == crit(current) else 1)
EOF
    then result PASS "ac4-contract: los criterios de M-001 (incluido AC4) son idénticos a los de ${first:0:7}"
    else result FAIL "ac4-contract: los criterios de M-001 cambiaron desde ${first:0:7}"; fi ;;

  audit)          # lo que se publicaría (archivos rastreados) y lo que instala `install`
    hits=$(git grep -nIE '/home/[a-z_][a-z0-9_-]*|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.(com|org|net|io|dev)' -- ':!tests/release_check.sh' | grep -v 'noreply@anthropic.com' || true)
    [[ -z $hits ]] && result PASS "audit: sin rutas personales ni direcciones de correo en archivos rastreados" \
                   || result FAIL "audit: datos personales en archivos rastreados:"$'\n'"$hits"
    hits=$(git grep -nIE '(ghp_|github_pat_|gho_|sk-[A-Za-z0-9]{20}|AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY|xox[bp]-)' -- ':!tests/release_check.sh' || true)
    [[ -z $hits ]] && result PASS "audit: sin patrones de secretos" || result FAIL "audit: posibles secretos:"$'\n'"$hits"
    hits=$(git ls-files | grep -E '(^|/)(runtime|backups|__pycache__)/|\.pyc$|\.lock$|(^|/)\.env|\.monday/manifest\.json' || true)
    [[ -z $hits ]] && result PASS "audit: sin estado de runtime, backups, cachés ni archivos temporales rastreados" \
                   || result FAIL "audit: archivos que no deben publicarse:"$'\n'"$hits"
    tmp=$(mktemp -d); python3 core/monday.py install "$tmp" >/dev/null
    hits=$(python3 -c 'import json,sys; print("\n".join(p for p in json.load(open(sys.argv[1]))["files"] if any(s in p for s in ("/runtime/", "/backups/", "__pycache__"))))' "$tmp/.monday/manifest.json")
    rm -rf "$tmp"
    [[ -z $hits ]] && result PASS "audit: install no distribuye estado local de core/" || result FAIL "audit: install distribuye: $hits" ;;

  version)
    v=$(cat core/VERSION)
    top=$(grep -m1 -oE '^## \[[0-9]+\.[0-9]+\.[0-9]+\]' CHANGELOG.md | tr -d '#[] ')
    if [[ $v == "$top" ]] && grep -q "v$v" README.md && python3 core/monday.py --version | grep -q "$v"; then
      result PASS "version: $v en core/VERSION, CHANGELOG, README y CLI"
    else result FAIL "version: core/VERSION=$v, CHANGELOG=$top, README contiene v$v: $(grep -c "v$v" README.md)"; fi ;;

  history)
    ok=1
    git merge-base --is-ancestor "$PREDECESSOR_MAIN" HEAD 2>/dev/null || ok=0
    for t in "${!TAGS[@]}"; do [[ $(git rev-parse -q --verify "refs/tags/$t" 2>/dev/null) == "${TAGS[$t]}" ]] || ok=0; done
    [[ $ok -eq 1 ]] && result PASS "history: el main predecesor y los tags v0.1.0/v0.9.0 se conservan sin reescritura (push fast-forward)" \
                    || result FAIL "history: falta el main predecesor como ancestro o los tags difieren de los publicados" ;;

  *) result FAIL "comprobación desconocida: $check" ;;
  esac
done
exit $failed
