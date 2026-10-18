#!/usr/bin/env python3
"""Monday — comprobaciones deterministas del harness (solo biblioteca estándar).

Comandos de proyecto: status, check, start, verify, scope, review, done, block, guard.
Integración con plataformas: hook {session-start,pre,stop} --platform {claude,antigravity}.
Distribución (desde una copia del repositorio Monday): install, rollback.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent          # <proyecto>/.monday  o  <repo Monday>/core
VERSION = (HERE / "VERSION").read_text().strip() if (HERE / "VERSION").exists() else "dev"
STATUSES = ("pending", "in_progress", "blocked", "done")
RISKS = ("low", "medium", "high")
FEATURE_KEYS = {"id", "title", "description", "status", "risk", "scope", "acceptance_criteria",
                "review_required", "depends_on", "notes",
                # escritos por el CLI
                "base", "preexisting", "started_at", "done_at", "blocked_reason", "review", "contract"}
CONTRACT_KEYS = ("risk", "scope", "acceptance_criteria", "review_required", "depends_on")
CRITERION_KEYS = {"id", "text", "verify"}
BLOCK_BEGIN, BLOCK_END = "<!-- monday:begin", "<!-- monday:end -->"
REQUIRED_FILES = ("AGENTS.md", "init.sh", "features.json", "docs/architecture.md",
                  "progress/current.md", "progress/exploration_logs.md", "progress/history.md")
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


class MondayError(Exception):
    pass


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    return sha256(path.read_bytes()) if path.is_file() else "absent"


def load_policy():
    return json.loads((HERE / "policy.json").read_text())


# ---------------------------------------------------------------- proyecto y features

def find_root(start=None):
    env = os.environ.get("MONDAY_ROOT")
    p = Path(env or start or os.getcwd()).resolve()
    for d in (p, *p.parents):
        if (d / "features.json").is_file():
            return d
    raise MondayError(f"no se encontró features.json desde {p} (¿proyecto sin Monday? usa `install`)")


def load_features(root):
    try:
        data = json.loads((root / "features.json").read_text())
    except json.JSONDecodeError as e:
        raise MondayError(f"features.json no es JSON válido: {e}")
    return data


def save_features(root, data):
    tmp = root / "features.json.tmp"
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(root / "features.json")


def get_feature(data, fid):
    for f in data.get("features", []):
        if f.get("id") == fid:
            return f
    raise MondayError(f"no existe la feature {fid} en features.json")


def safe_pattern(p):
    return isinstance(p, str) and p.strip() == p and p and not p.startswith(("/", "~")) \
        and not re.match(r"^[A-Za-z]:", p) and ".." not in p.split("/")


def validate_features(data):
    errors = []
    if not isinstance(data, dict) or not isinstance(data.get("features"), list):
        return ["features.json debe ser un objeto con la lista 'features'"]
    seen, active = set(), []
    for i, f in enumerate(data["features"]):
        where = f"features[{i}]"
        if not isinstance(f, dict):
            errors.append(f"{where}: debe ser un objeto"); continue
        fid = f.get("id")
        where = f"{fid or where}"
        unknown = set(f) - FEATURE_KEYS
        if unknown:
            errors.append(f"{where}: claves desconocidas {sorted(unknown)} (¿errata? una clave mal escrita anula una restricción)")
        if not isinstance(fid, str) or not fid:
            errors.append(f"{where}: falta 'id'")
        elif fid in seen:
            errors.append(f"{where}: id duplicado")
        seen.add(fid)
        if not isinstance(f.get("title"), str) or not f.get("title"):
            errors.append(f"{where}: falta 'title'")
        if f.get("status") not in STATUSES:
            errors.append(f"{where}: status debe ser uno de {STATUSES}")
        if f.get("risk") not in RISKS:
            errors.append(f"{where}: risk debe ser uno de {RISKS}")
        scope = f.get("scope", [])
        if not isinstance(scope, list) or not all(safe_pattern(s) for s in scope):
            errors.append(f"{where}: scope debe ser una lista de globs relativos sin '..' ni rutas absolutas")
        crit = f.get("acceptance_criteria", [])
        if not isinstance(crit, list):
            errors.append(f"{where}: acceptance_criteria debe ser una lista"); crit = []
        cids = set()
        for c in crit:
            if not isinstance(c, dict) or not c.get("id") or not c.get("text"):
                errors.append(f"{where}: cada criterio necesita 'id' y 'text'"); continue
            if set(c) - CRITERION_KEYS:
                errors.append(f"{where}/{c['id']}: claves desconocidas {sorted(set(c) - CRITERION_KEYS)}")
            if c["id"] in cids:
                errors.append(f"{where}/{c['id']}: id de criterio duplicado")
            cids.add(c["id"])
            if "verify" in c and (not isinstance(c["verify"], str) or not c["verify"].strip()):
                errors.append(f"{where}/{c['id']}: 'verify' debe ser un comando no vacío (omítelo si el criterio es manual)")
        if f.get("status") in ("in_progress", "done"):
            if not scope:
                errors.append(f"{where}: una feature {f['status']} necesita 'scope'")
            if not crit:
                errors.append(f"{where}: una feature {f['status']} necesita acceptance_criteria")
        if f.get("status") == "in_progress":
            active.append(fid)
    if len(active) > 1:
        errors.append(f"hay más de una feature in_progress: {active}")
    return errors


def active_feature(data):
    return next((f for f in data.get("features", []) if f.get("status") == "in_progress"), None)


def contract_hash(f):
    """Huella de lo que autoriza y exige la feature; cambiarla tras `start` requiere `amend`."""
    return sha256(json.dumps({k: f.get(k) for k in CONTRACT_KEYS}, sort_keys=True, ensure_ascii=False).encode())


def review_required(f):
    return f.get("risk") == "high" or bool(f.get("review_required"))


# ---------------------------------------------------------------- globs y git

def glob_re(pattern):
    if pattern.endswith("/"):
        pattern += "**"
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"; i += 3
        elif pattern.startswith("**", i):
            out += ".*"; i += 2
        elif pattern[i] == "*":
            out += "[^/]*"; i += 1
        elif pattern[i] == "?":
            out += "[^/]"; i += 1
        else:
            out += re.escape(pattern[i]); i += 1
    return re.compile(out + r"\Z")


def matches(path, patterns):
    return any(glob_re(p).match(path) for p in patterns)


def git(root, *args):
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise MondayError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def git_available(root):
    if not shutil.which("git"):
        return False
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
                       capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "true"


def head_or_empty(root):
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "-q", "HEAD"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else EMPTY_TREE


def changed_files(root, base):
    """Archivos que difieren de `base` (commits posteriores + árbol de trabajo + no rastreados)."""
    diff = git(root, "diff", "--name-only", "--no-renames", "--relative", "-z", base, "--")
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "-z")
    return sorted({p for p in (diff + untracked).split("\0") if p})


def feature_changes(root, f, policy):
    """Cambios atribuibles a la feature: excluye memoria del harness y lo que ya estaba sucio al empezar sin tocar."""
    pre = f.get("preexisting", {})
    out = []
    for p in changed_files(root, f.get("base") or EMPTY_TREE):
        if matches(p, policy["always_writable"]):
            continue
        if p in pre and pre[p] == file_hash(root / p):
            continue
        out.append(p)
    return out


def fingerprint(root, paths):
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(f"{p}\0{file_hash(root / p)}\n".encode())
    return h.hexdigest()


# ---------------------------------------------------------------- comprobaciones

def run_cmd(cmd, root, timeout):
    shell = ["bash", "-c", cmd] if shutil.which("bash") else ["sh", "-c", cmd]
    try:
        r = subprocess.run(shell, cwd=root, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "FAIL", f"timeout tras {timeout}s"
    tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-15:])
    if r.returncode == 0:
        return "PASS", tail
    if r.returncode in (126, 127):
        return "UNAVAILABLE", f"exit {r.returncode} (comando o dependencia no disponible)\n{tail}"
    return "FAIL", f"exit {r.returncode}\n{tail}"


def verify_criteria(root, f, manual, timeout):
    results = []
    for c in f.get("acceptance_criteria", []):
        cid = c["id"]
        if "verify" in c:
            status, detail = run_cmd(c["verify"], root, timeout)
            if status == "UNAVAILABLE" and manual.get(cid):
                status, detail = "MANUAL", f"verificación automática no disponible; evidencia: {manual[cid]}"
            results.append((cid, status, c["verify"], detail))
        elif manual.get(cid):
            results.append((cid, "MANUAL", "", f"evidencia: {manual[cid]}"))
        else:
            results.append((cid, "PENDING_MANUAL", "", f"criterio manual sin evidencia: {c['text']}"))
    return results


def scope_result(root, f, policy, manual):
    if not git_available(root):
        if manual.get("scope"):
            return "MANUAL", [], f"git no disponible; evidencia: {manual['scope']}"
        return "UNAVAILABLE", [], "git no disponible: aporta --manual scope=\"<evidencia>\""
    changes = feature_changes(root, f, policy)
    allowed = f.get("scope", [])
    bad = [p for p in changes if not matches(p, allowed)]
    if bad:
        return "FAIL", changes, "fuera de alcance: " + ", ".join(bad)
    return "PASS", changes, f"{len(changes)} archivo(s) dentro del alcance"


def run_init(root, timeout, full=False):
    init = root / "init.sh"
    if not init.is_file():
        return "FAIL", "init.sh no existe"
    status, detail = run_cmd("./init.sh" + (" --full" if full else ""), root, timeout)
    return ("FAIL" if status == "UNAVAILABLE" else status), detail


def check_project(root):
    errors, warnings = [], []
    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            errors.append(f"falta {rel}")
    if (root / "init.sh").is_file() and not os.access(root / "init.sh", os.X_OK):
        errors.append("init.sh no es ejecutable (chmod +x init.sh)")
    agents = root / "AGENTS.md"
    if agents.is_file():
        text = agents.read_text()
        n = len(text.splitlines())
        if n > 200:
            errors.append(f"AGENTS.md tiene {n} líneas (máximo 200)")
        if BLOCK_BEGIN not in text:
            warnings.append("AGENTS.md no contiene el bloque gestionado de Monday")
    if (root / "features.json").is_file():
        try:
            errors += validate_features(load_features(root))
        except MondayError as e:
            errors.append(str(e))
    manifest = root / ".monday" / "manifest.json"
    if manifest.is_file():
        m = json.loads(manifest.read_text())
        for rel, digest in m.get("files", {}).items():
            actual = file_hash(root / rel)
            if actual == "absent":
                errors.append(f"falta el archivo gestionado {rel} (reinstala Monday)")
            elif actual != digest:
                errors.append(f"{rel} difiere de Monday {m.get('version')}: los archivos gestionados no se editan en el proyecto")
        for plat in m.get("platforms", []):
            if not ADAPTERS[plat]["registered"](root):
                errors.append(f"adaptador {plat}: hooks de Monday ausentes en {ADAPTERS[plat]['config']}")
    elif not (root / ".monday").is_symlink():
        warnings.append("sin .monday/manifest.json: no se puede comprobar la integridad de los archivos gestionados")
    return errors, warnings


# ---------------------------------------------------------------- guardas (usadas por hooks o a mano)

def guard_path(root, path):
    """Devuelve None si no hay objeción, o el motivo para pedir permiso."""
    policy = load_policy()
    p = Path(path)
    p = (p if p.is_absolute() else root / p)
    rel = os.path.relpath(os.path.realpath(p), root)
    if rel == ".." or rel.startswith(".." + os.sep):
        return f"{path} está fuera del proyecto"
    rel = rel.replace(os.sep, "/")
    f = None
    try:
        f = active_feature(load_features(root))
    except MondayError:
        pass
    if matches(rel, policy["protected_paths"]) and not (f and matches(rel, f.get("scope", []))):
        return f"{rel} es una ruta protegida del harness (control de seguridad o archivo gestionado)"
    if f and not matches(rel, f.get("scope", []) + policy["always_writable"]):
        return f"{rel} está fuera del alcance de {f['id']} ({', '.join(f.get('scope', []))})"
    return None


def guard_command(cmd):
    for pattern in load_policy()["ask_commands"]:
        if re.search(pattern, cmd):
            return f"comando que requiere autorización humana (irreversible o con efectos externos): coincide con /{pattern}/"
    return None


# ---------------------------------------------------------------- comandos de proyecto

def cmd_status(a, out=print):
    root = find_root()
    data = load_features(root)
    feats = data.get("features", [])
    counts = {s: sum(1 for f in feats if f.get("status") == s) for s in STATUSES}
    out(f"Monday {VERSION} · {root}")
    out("Features: " + " · ".join(f"{s} {n}" for s, n in counts.items()))
    act = active_feature(data)
    if act:
        crit = act.get("acceptance_criteria", [])
        auto = sum(1 for c in crit if "verify" in c)
        rev = "no requerida"
        if review_required(act):
            rev = (act.get("review") or {}).get("verdict", "pendiente")
        out(f"EN CURSO: {act['id']} — {act['title']} (risk {act['risk']}, desde {act.get('started_at', '?')}); "
            f"criterios {len(crit)} ({auto} automáticos); revisión: {rev}")
        out("  alcance: " + ", ".join(act.get("scope", [])))
    for f in feats:
        if f.get("status") == "blocked":
            out(f"BLOQUEADA: {f['id']} — {f['title']}: {f.get('blocked_reason', '')}")
    nxt = next((f for f in feats if f.get("status") == "pending"), None)
    if nxt:
        out(f"Siguiente pendiente: {nxt['id']} — {nxt['title']}")
    cur = root / "progress" / "current.md"
    if cur.is_file():
        lines = [l for l in cur.read_text().splitlines() if l.strip() and not l.startswith("<!--")]
        out("progress/current.md:")
        for l in lines[:25]:
            out("  " + l)
        if len(lines) > 25:
            out(f"  … ({len(lines) - 25} líneas más)")
    return 0


def cmd_check(a):
    root = find_root()
    errors, warnings = check_project(root)
    for w in warnings:
        print(f"AVISO: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    print("monday check: " + ("FAIL" if errors else "PASS"))
    return 1 if errors else 0


def cmd_start(a):
    root = find_root()
    data = load_features(root)
    errs = validate_features(data)
    if errs:
        raise MondayError("features.json inválido:\n  " + "\n  ".join(errs))
    f = get_feature(data, a.id)
    act = active_feature(data)
    if act and act["id"] != a.id:
        raise MondayError(f"ya hay una feature en curso ({act['id']}); termínala con `done` o `block` antes")
    if f["status"] == "done":
        raise MondayError(f"{a.id} ya está done")
    if not f.get("scope") or not f.get("acceptance_criteria"):
        raise MondayError(f"{a.id} necesita 'scope' y 'acceptance_criteria' antes de empezar")
    pending_deps = [d for d in f.get("depends_on", []) if get_feature(data, d)["status"] != "done"]
    if pending_deps:
        raise MondayError(f"{a.id} depende de features no terminadas: {pending_deps}")
    if f["status"] == "pending":
        f["started_at"] = now()
        f["contract"] = contract_hash(f)
        if git_available(root):
            f["base"] = head_or_empty(root)
            policy = load_policy()
            dirty = [p for p in changed_files(root, f["base"]) if not matches(p, policy["always_writable"])]
            f["preexisting"] = {p: file_hash(root / p) for p in dirty}
            if dirty:
                print(f"AVISO: {len(dirty)} archivo(s) ya modificados antes de empezar; no se atribuyen a {a.id} mientras no cambien")
    f["status"] = "in_progress"
    f.pop("blocked_reason", None)
    save_features(root, data)
    cur = root / "progress" / "current.md"
    if cur.is_file():
        text = cur.read_text()
        text = re.sub(r"^Feature:.*$", f"Feature: {f['id']} — {f['title']} (desde {f['started_at']})",
                      text, count=1, flags=re.M)
        cur.write_text(text)
    print(f"{a.id} in_progress. Escribe el plan en progress/current.md; alcance: {', '.join(f['scope'])}")
    return 0


def parse_manual(items):
    manual = {}
    for item in items or []:
        key, sep, val = item.partition("=")
        if not sep or not val.strip():
            raise MondayError(f"--manual espera CLAVE=evidencia, recibido: {item!r}")
        manual[key.strip()] = val.strip()
    return manual


def print_results(results):
    for cid, status, cmd, detail in results:
        print(f"  [{status}] {cid}" + (f" — `{cmd}`" if cmd else ""))
        if status not in ("PASS",):
            for l in detail.splitlines():
                print(f"      {l}")


def cmd_verify(a):
    root = find_root()
    f = get_feature(load_features(root), a.id)
    results = verify_criteria(root, f, parse_manual(a.manual), a.timeout)
    print(f"Verificación de {a.id}:")
    print_results(results)
    ok = all(r[1] in ("PASS", "MANUAL") for r in results)
    executed = sum(1 for r in results if r[1] in ("PASS", "FAIL"))
    passed = sum(1 for r in results if r[1] == "PASS")
    print(f"Ejecutadas {executed} · superadas {passed} · fallidas {sum(1 for r in results if r[1] == 'FAIL')} · "
          f"no disponibles {sum(1 for r in results if r[1] == 'UNAVAILABLE')} · manuales pendientes {sum(1 for r in results if r[1] == 'PENDING_MANUAL')}")
    return 0 if ok else 1


def cmd_scope(a):
    root = find_root()
    f = get_feature(load_features(root), a.id)
    status, changes, detail = scope_result(root, f, load_policy(), {})
    print(f"Alcance de {a.id}: {status} — {detail}")
    for p in changes:
        print(f"  {p}")
    return 0 if status == "PASS" else 1


def append_history(root, block):
    hist = root / "progress" / "history.md"
    text = hist.read_text() if hist.is_file() else "# Historial\n"
    hist.write_text(text.rstrip("\n") + "\n\n" + block.strip("\n") + "\n")


def cmd_review(a):
    root = find_root()
    data = load_features(root)
    f = get_feature(data, a.id)
    if f["status"] != "in_progress":
        raise MondayError(f"{a.id} no está in_progress")
    if not git_available(root):
        raise MondayError("la revisión se ancla al diff: requiere git")
    changes = feature_changes(root, f, load_policy())
    f["review"] = {"verdict": a.verdict, "by": a.by, "at": now(),
                   "fingerprint": fingerprint(root, changes), "files": len(changes)}
    if a.notes:
        f["review"]["notes"] = a.notes
    save_features(root, data)
    if a.verdict == "changes_required":
        append_history(root, f"## {now()[:10]} · {a.id} · REVISIÓN: changes_required ({a.by})\n- {a.notes or 'sin notas'}")
    print(f"Revisión de {a.id} registrada: {a.verdict} por {a.by} sobre {len(changes)} archivo(s)")
    return 0


def summary_section(text):
    m = re.search(r"^## Resumen[^\n]*\n(.*?)(?=^## |\Z)", text, flags=re.M | re.S)
    body = m.group(1).strip() if m else ""
    return "\n".join(l for l in body.splitlines() if not l.strip().startswith("<!--"))


def cmd_done(a):
    root = find_root()
    data = load_features(root)
    errs = validate_features(data)
    if errs:
        raise MondayError("features.json inválido:\n  " + "\n  ".join(errs))
    f = get_feature(data, a.id)
    if f["status"] != "in_progress":
        raise MondayError(f"{a.id} no está in_progress (estado: {f['status']})")
    manual = parse_manual(a.manual)
    policy = load_policy()
    checks = []                                   # (nombre, estado, detalle)

    if f.get("contract") != contract_hash(f):
        checks.append(("contract", "FAIL", "risk/scope/criterios cambiaron desde `start` sin `monday amend`"))
    init_status, init_detail = run_init(root, a.timeout, full=f["risk"] != "low")
    checks.append(("init.sh", init_status, init_detail))
    results = verify_criteria(root, f, manual, a.timeout)
    for cid, status, cmd, detail in results:
        checks.append((cid, status, (f"`{cmd}` " if cmd else "") + detail))
    s_status, changes, s_detail = scope_result(root, f, policy, manual)
    checks.append(("scope", s_status, s_detail))
    if review_required(f):
        rev = f.get("review") or {}
        if not git_available(root) and manual.get("review"):
            checks.append(("review", "MANUAL", f"sin git; evidencia: {manual['review']}"))
        elif rev.get("verdict") != "approve":
            checks.append(("review", "FAIL", f"risk {f['risk']}: se requiere revisión independiente aprobada (actual: {rev.get('verdict', 'ninguna')})"))
        elif git_available(root) and rev.get("fingerprint") != fingerprint(root, changes):
            checks.append(("review", "FAIL", "el diff cambió después de la revisión: hay que revisar de nuevo"))
        else:
            checks.append(("review", "PASS", f"approve por {rev.get('by')}"))

    ok = all(s in ("PASS", "MANUAL") for _, s, _ in checks)
    print(f"Cierre de {a.id}: {'ACEPTADO' if ok else 'RECHAZADO'}")
    for name, status, detail in checks:
        print(f"  [{status}] {name}")
        if status != "PASS":
            for l in detail.splitlines()[:15]:
                print(f"      {l}")
    evidence = " · ".join(f"{n} {s}" for n, s, _ in checks)
    date = now()[:10]
    if not ok:
        append_history(root, f"## {date} · {a.id} · RECHAZADO\n- {evidence}")
        print("No se marca como done. Corrige, o usa `block` y escala si no puedes resolverlo.")
        return 1
    cur = root / "progress" / "current.md"
    summary = summary_section(cur.read_text()) if cur.is_file() else ""
    f["status"] = "done"
    f["done_at"] = now()
    save_features(root, data)
    manual_notes = "\n".join(f"- Evidencia manual {n}: {d}" for n, s, d in checks if s == "MANUAL")
    block = f"## {date} · {a.id} · DONE — {f['title']}\n- Evidencia: {evidence}\n- Archivos: {', '.join(changes) or '(ninguno)'}"
    if manual_notes:
        block += "\n" + manual_notes
    if summary:
        block += "\n" + summary
    append_history(root, block)
    tpl = HERE / "templates" / "current.md"
    if tpl.is_file() and cur.is_file():
        shutil.copyfile(tpl, cur)
    print(f"{a.id} done. Resumen movido a progress/history.md y progress/current.md reiniciado.")
    return 0


def cmd_amend(a):
    root = find_root()
    data = load_features(root)
    f = get_feature(data, a.id)
    if f["status"] not in ("in_progress", "blocked"):
        raise MondayError(f"{a.id} no está en curso: edita features.json directamente")
    errs = validate_features(data)
    if errs:
        raise MondayError("features.json inválido:\n  " + "\n  ".join(errs))
    if f.get("contract") == contract_hash(f):
        print(f"{a.id}: el contrato no ha cambiado")
        return 0
    f["contract"] = contract_hash(f)
    dropped = f.pop("review", None)
    save_features(root, data)
    crit = ", ".join(c["id"] + ("" if "verify" in c else " (manual)") for c in f["acceptance_criteria"])
    append_history(root, f"## {now()[:10]} · {a.id} · CONTRATO MODIFICADO\n- Motivo: {a.reason}\n"
                         f"- Ahora: risk {f['risk']} · scope {', '.join(f['scope'])} · criterios {crit}"
                         + ("\n- La revisión previa queda invalidada" if dropped else ""))
    print(f"{a.id}: contrato actualizado y registrado en history.md" + (" (revisión invalidada)" if dropped else ""))
    return 0


def cmd_block(a):
    root = find_root()
    data = load_features(root)
    f = get_feature(data, a.id)
    if f["status"] == "done":
        raise MondayError(f"{a.id} ya está done")
    f["status"], f["blocked_reason"] = "blocked", a.reason
    save_features(root, data)
    append_history(root, f"## {now()[:10]} · {a.id} · BLOQUEADA\n- {a.reason}")
    print(f"{a.id} bloqueada: {a.reason}")
    return 0


def cmd_guard(a):
    root = find_root()
    reason = guard_command(a.cmd) if a.cmd is not None else guard_path(root, a.path)
    if reason:
        print(f"PEDIR PERMISO: {reason}")
        return 3
    print("OK")
    return 0


# ---------------------------------------------------------------- hooks de plataforma

WRITE_TOOLS = {
    "claude": {"Edit": "file_path", "Write": "file_path", "MultiEdit": "file_path", "NotebookEdit": "notebook_path"},
    "antigravity": {"write_to_file": "TargetFile", "replace_file_content": "TargetFile",
                    "multi_replace_file_content": "TargetFile"},
}
SHELL_TOOLS = {"claude": ("Bash", "command"), "antigravity": ("run_command", "CommandLine")}


def hook_root(platform, payload):
    if platform == "claude":
        start = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR")
    else:
        start = (payload.get("workspacePaths") or [None])[0]
    return find_root(start)


def hook_pre(platform, payload, root):
    if platform == "claude":
        tool, args = payload.get("tool_name", ""), payload.get("tool_input") or {}
    else:
        call = payload.get("toolCall") or {}
        tool, args = call.get("name", ""), call.get("args") or {}
    reason = None
    if tool in WRITE_TOOLS[platform] and args.get(WRITE_TOOLS[platform][tool]):
        reason = guard_path(root, args[WRITE_TOOLS[platform][tool]])
    elif tool == SHELL_TOOLS[platform][0] and args.get(SHELL_TOOLS[platform][1]):
        reason = guard_command(args[SHELL_TOOLS[platform][1]])
    if not reason:
        return None                                       # sin salida = sin objeción
    reason = "Monday: " + reason
    if platform == "claude":
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                       "permissionDecision": "ask", "permissionDecisionReason": reason}}
    # En agy, 'ask' y 'force_ask' se autoaprueban en modo accept-edits (verificado): solo 'deny' bloquea.
    return {"decision": "deny", "reason": reason + ". Pide al humano que lo autorice (ampliando el scope de la feature o ejecutándolo él)."}


def hook_stop(platform, payload, root):
    if platform == "claude" and payload.get("stop_hook_active"):
        return None
    if git_available(root):
        policy = load_policy()
        dirty = [p for p in changed_files(root, "HEAD" if head_or_empty(root) != EMPTY_TREE else EMPTY_TREE)
                 if not matches(p, policy["always_writable"])]
        if not dirty:
            return None                                   # solo cambió la memoria (o nada): nada pudo romperse
    status, detail = run_init(root, timeout=600)
    marker = root / ".monday" / "runtime" / "stop-block.json"
    if status == "PASS":
        marker.unlink(missing_ok=True)
        return None
    # Firma = qué comprobaciones fallan, no su salida (que incluye tiempos): el mismo fallo no bloquea dos veces.
    failing = sorted(l for l in detail.splitlines() if re.match(r"(FAIL|UNAVAILABLE|ERROR)\b", l))
    sig = sha256("\n".join(failing or [detail.splitlines()[0] if detail else ""]).encode())
    if marker.is_file() and json.loads(marker.read_text()).get("sig") == sig:
        marker.unlink()                                   # mismo fallo ya señalado: no bloquear en bucle
        return None
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"sig": sig, "at": now()}))
    reason = ("Monday: ./init.sh falla y el repositorio no debe quedar roto. Corrige el fallo o, si no puedes, "
              "explica al usuario qué falla y por qué (no declares éxito).\n" + detail)
    if platform == "claude":
        return {"decision": "block", "reason": reason}
    return {"decision": "continue", "reason": reason}


def hook_session_start(platform, payload, root):
    lines = []
    cmd_status(None, out=lines.append)
    text = ("Protocolo Monday activo (AGENTS.md). Estado del proyecto:\n" + "\n".join(lines)
            + "\nAntes de escribir código: ./init.sh; si falla, detente y repórtalo.")
    if platform == "claude":
        return text
    return {"injectSteps": [{"systemMessage": {"systemMessage": text}}]}


def cmd_hook(a):
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
        root = hook_root(a.platform, payload)
        os.chdir(root)
        result = {"pre": hook_pre, "stop": hook_stop, "session-start": hook_session_start}[a.event](a.platform, payload, root)
    except Exception as e:                                 # un hook roto no debe bloquear al agente
        print(f"monday hook {a.event}: {e}", file=sys.stderr)
        return 0
    if isinstance(result, dict):                          # traza de lo que Monday bloqueó o pidió confirmar
        log = root / ".monday" / "runtime" / "hooks.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a") as fh:
            fh.write(json.dumps({"at": now(), "platform": a.platform, "event": a.event, "result": result},
                                ensure_ascii=False) + "\n")
    if isinstance(result, str):
        print(result)
    elif result is not None:
        print(json.dumps(result, ensure_ascii=False))
    return 0


# ---------------------------------------------------------------- adaptadores e instalación

def _json(path):
    return json.loads(path.read_text()) if path.is_file() else {}


def claude_registered(root):
    hooks = _json(root / ".claude" / "settings.json").get("hooks", {})
    cmds = [h.get("command", "") for groups in hooks.values() for g in groups for h in g.get("hooks", [])]
    return all(any(f"hook {ev} --platform claude" in c for c in cmds) for ev in ("pre", "stop", "session-start"))


def agy_registered(root):
    return "monday" in _json(root / ".agents" / "hooks.json")


ADAPTERS = {
    "claude": {"dir": "claude-code", "config": ".claude/settings.json", "registered": claude_registered,
               "agents_to": ".claude/agents", "seeds": {"CLAUDE.md": "CLAUDE.md"}},
    "antigravity": {"dir": "antigravity", "config": ".agents/hooks.json", "registered": agy_registered,
                    "agents_to": ".agents/agents", "seeds": {}},
}
SEEDS = {"AGENTS.md": "AGENTS.md", "init.sh": "init.sh", "features.json": "features.json",
         "docs/architecture.md": "architecture.md", "progress/current.md": "current.md",
         "progress/exploration_logs.md": "exploration_logs.md", "progress/history.md": "history.md"}


def is_monday_hook(command):
    return re.search(r"monday\.py\"?\s+hook\s", command or "") is not None


def merge_claude_settings(existing, fragment):
    """Sustituye los hooks de Monday y conserva todo lo demás."""
    out = dict(existing)
    hooks = {ev: [g for g in groups if not any(is_monday_hook(h.get("command")) for h in g.get("hooks", []))]
             for ev, groups in existing.get("hooks", {}).items()}
    for ev, groups in fragment["hooks"].items():
        hooks.setdefault(ev, []).extend(groups)
    out["hooks"] = {ev: g for ev, g in hooks.items() if g}
    return out


def merge_agy_hooks(existing, fragment):
    out = {k: v for k, v in existing.items() if k != "monday"}
    out.update(fragment)
    return out


def agents_md_block(template_text):
    start, end = template_text.index(BLOCK_BEGIN), template_text.index(BLOCK_END) + len(BLOCK_END)
    return template_text[start:end]


def plan_install(src, target, platforms):
    """Calcula los escritos: lista de (ruta relativa, bytes, tipo). tipo: managed | seed | merged."""
    core = src / "core"
    writes = []
    for p in sorted(core.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            writes.append((f".monday/{p.relative_to(core).as_posix()}", p.read_bytes(), "managed"))
    tpl = core / "templates"
    for rel, name in SEEDS.items():
        dest = target / rel
        if rel == "AGENTS.md" and dest.is_file():
            text, block = dest.read_text(), agents_md_block((tpl / name).read_text())
            if BLOCK_BEGIN in text and BLOCK_END in text:
                new = text[:text.index(BLOCK_BEGIN)] + block + text[text.index(BLOCK_END) + len(BLOCK_END):]
            else:
                lines = text.split("\n", 1)
                new = lines[0] + "\n\n" + block + "\n" + (lines[1] if len(lines) > 1 else "")
            if new != text:
                writes.append((rel, new.encode(), "merged"))
        elif not dest.exists():
            writes.append((rel, (tpl / name).read_bytes(), "seed"))
    for plat in platforms:
        ad = src / "adapters" / ADAPTERS[plat]["dir"]
        for p in sorted((ad / "agents").glob("*.md")):
            writes.append((f"{ADAPTERS[plat]['agents_to']}/{p.name}", p.read_bytes(), "managed"))
        for rel, name in ADAPTERS[plat]["seeds"].items():
            dest = target / rel
            if not dest.exists():
                writes.append((rel, (ad / name).read_bytes(), "seed"))
            elif "@AGENTS.md" not in dest.read_text():
                writes.append((rel, (dest.read_text().rstrip("\n") + "\n\n@AGENTS.md\n").encode(), "merged"))
        cfg = target / ADAPTERS[plat]["config"]
        if plat == "claude":
            merged = merge_claude_settings(_json(cfg), _json(ad / "settings.json"))
        else:
            merged = merge_agy_hooks(_json(cfg), _json(ad / "hooks.json"))
        new = (json.dumps(merged, indent=2, ensure_ascii=False) + "\n").encode()
        if not cfg.is_file() or cfg.read_bytes() != new:
            writes.append((ADAPTERS[plat]["config"], new, "merged"))
    return writes


def cmd_install(a):
    src = HERE.parent
    if not (src / "adapters").is_dir() or HERE.name != "core":
        raise MondayError("install se ejecuta desde una copia del repositorio Monday: python3 <Monday>/core/monday.py install <proyecto>")
    target = Path(a.target).resolve()
    if not target.is_dir():
        raise MondayError(f"{target} no es un directorio")
    if target == src:
        raise MondayError("no se instala Monday sobre su propio repositorio (usa .monday -> core)")
    old = _json(target / ".monday" / "manifest.json")
    platforms = sorted(set(a.platform or old.get("platforms", ["claude", "antigravity"])))
    diverged = [rel for rel, h in old.get("files", {}).items()
                if (target / rel).is_file() and file_hash(target / rel) != h]
    if diverged and not a.force:
        raise MondayError("archivos gestionados modificados en el proyecto (se perderían): " + ", ".join(diverged)
                          + "\nLleva esos cambios al repositorio Monday o repite con --force.")
    writes = plan_install(src, target, platforms)
    new_managed = {rel for rel, _, kind in writes if kind == "managed"}
    stale = [rel for rel in old.get("files", {}) if rel not in new_managed and (target / rel).is_file()]
    changes = [(rel, data, kind) for rel, data, kind in writes
               if not (target / rel).is_file() or (target / rel).read_bytes() != data]
    verb = "Actualizar" if old else "Instalar"
    print(f"{verb} Monday {VERSION} en {target} (plataformas: {', '.join(platforms)})")
    for rel, _, kind in changes:
        print(f"  {'crear' if not (target / rel).exists() else 'actualizar'} [{kind}] {rel}")
    for rel in stale:
        print(f"  eliminar [obsoleto] {rel}")
    if not changes and not stale and old.get("version") == VERSION and old.get("platforms") == platforms:
        print("  sin cambios")
        return 0
    if a.dry_run:
        print("(dry-run: no se ha escrito nada)")
        return 0
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    bdir = target / ".monday" / "backups" / stamp
    journal = {"version": VERSION, "at": now(), "created": {}, "modified": {}}
    for rel, data, kind in changes:
        dest = target / rel
        if dest.exists():
            (bdir / "files" / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, bdir / "files" / rel)
            journal["modified"][rel] = sha256(data)       # hash tras instalar: si cambia, rollback no lo pisa
        else:
            journal["created"][rel] = sha256(data)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        if rel in ("init.sh", ".monday/monday.py"):
            dest.chmod(0o755)
    for rel in stale:
        (bdir / "files" / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(target / rel), bdir / "files" / rel)
        journal["modified"][rel] = "absent"
    manifest = {"version": VERSION, "installed_at": now(), "platforms": platforms,
                "files": {rel: file_hash(target / rel) for rel in sorted(new_managed)}}
    mpath = target / ".monday" / "manifest.json"
    if mpath.is_file():
        (bdir / "files" / ".monday").mkdir(parents=True, exist_ok=True)
        shutil.copy2(mpath, bdir / "files" / ".monday" / "manifest.json")
        journal["modified"][".monday/manifest.json"] = None
    else:
        journal["created"][".monday/manifest.json"] = None
    mpath.write_text(json.dumps(manifest, indent=2) + "\n")
    bdir.mkdir(parents=True, exist_ok=True)
    (bdir / "journal.json").write_text(json.dumps(journal, indent=2, ensure_ascii=False) + "\n")
    print(f"Hecho. Backup para revertir: .monday/backups/{stamp} (`python3 .monday/monday.py rollback`)")
    print("Siguiente: edita el mapa de AGENTS.md y los checks de init.sh; después ./init.sh")
    return 0


def cmd_rollback(a):
    target = Path(a.target).resolve()
    broot = target / ".monday" / "backups"
    stamps = sorted(p.name for p in broot.iterdir() if (p / "journal.json").is_file()) if broot.is_dir() else []
    if not stamps:
        raise MondayError("no hay backups de Monday que revertir")
    for stamp in reversed(stamps if a.all else stamps[-1:]):
        bdir = broot / stamp
        journal = json.loads((bdir / "journal.json").read_text())
        print(f"Revertir instalación {stamp} (Monday {journal['version']})")
        kept = []
        for rel, digest in journal["created"].items():
            dest = target / rel
            if not dest.is_file():
                continue
            if digest and file_hash(dest) != digest and not a.force:
                kept.append(rel)
                print(f"  conservar {rel} (modificado después de instalar; --force para borrarlo)")
                continue
            print(f"  borrar {rel}")
            if not a.dry_run:
                dest.unlink()
        for rel, digest in journal["modified"].items():
            if digest and file_hash(target / rel) != digest and not a.force:
                kept.append(rel)
                print(f"  conservar {rel} (modificado después de instalar; original en {bdir.relative_to(target)}/files; --force para restaurarlo)")
                continue
            print(f"  restaurar {rel}")
            if not a.dry_run:
                (target / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(bdir / "files" / rel, target / rel)
        if a.dry_run:
            print("(dry-run: no se ha cambiado nada)")
            continue
        if kept:                                          # el backup se conserva mientras haga falta para --force
            print("Revertido parcialmente; conservados: " + ", ".join(kept) + ". Para terminar: `python3 <repo Monday>/core/monday.py rollback <proyecto> --force`.")
            continue
        shutil.rmtree(bdir)
        for rel in journal["created"]:                    # limpia directorios que quedaron vacíos
            d = (target / rel).parent
            while d != target and d.is_dir() and not any(d.iterdir()):
                d.rmdir()
                d = d.parent
    if not a.dry_run and broot.is_dir() and not any(broot.iterdir()):
        broot.rmdir()
        mon = target / ".monday"
        if mon.is_dir() and {p.name for p in mon.iterdir()} <= {"runtime"}:
            shutil.rmtree(mon)                            # solo quedaba estado efímero (hooks.log, marcadores)
    return 0


# ---------------------------------------------------------------- CLI

def main(argv=None):
    p = argparse.ArgumentParser(prog="monday", description="Harness Monday: estado, verificación y gobierno de tareas.")
    p.add_argument("--version", action="version", version=f"Monday {VERSION}")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="estado actual y siguiente paso").set_defaults(f=cmd_status)
    sub.add_parser("check", help="integridad del harness (lo usa init.sh)").set_defaults(f=cmd_check)
    s = sub.add_parser("start", help="pasa una feature a in_progress y fija la base del diff")
    s.add_argument("id"); s.set_defaults(f=cmd_start)
    for name, fn, hlp in (("verify", cmd_verify, "ejecuta los criterios de aceptación"),
                          ("done", cmd_done, "cierra una feature solo si toda la evidencia lo respalda")):
        s = sub.add_parser(name, help=hlp)
        s.add_argument("id")
        s.add_argument("--manual", action="append", metavar="CLAVE=EVIDENCIA",
                       help="evidencia para un criterio manual o no disponible (o scope sin git)")
        s.add_argument("--timeout", type=int, default=900)
        s.set_defaults(f=fn)
    s = sub.add_parser("scope", help="compara el diff con el alcance de la feature")
    s.add_argument("id"); s.set_defaults(f=cmd_scope)
    s = sub.add_parser("review", help="registra el veredicto de la revisión independiente")
    s.add_argument("id"); s.add_argument("--verdict", required=True, choices=["approve", "changes_required"])
    s.add_argument("--by", required=True); s.add_argument("--notes"); s.set_defaults(f=cmd_review)
    s = sub.add_parser("amend", help="registra un cambio de contrato (risk/scope/criterios) de una feature en curso")
    s.add_argument("id"); s.add_argument("--reason", required=True); s.set_defaults(f=cmd_amend)
    s = sub.add_parser("block", help="bloquea una feature y registra el motivo (escalado)")
    s.add_argument("id"); s.add_argument("--reason", required=True); s.set_defaults(f=cmd_block)
    s = sub.add_parser("guard", help="¿puedo escribir esta ruta / ejecutar este comando sin pedir permiso?")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("path", nargs="?"); g.add_argument("--cmd")
    s.set_defaults(f=cmd_guard)
    s = sub.add_parser("hook", help="entrada para hooks de plataforma (lee JSON por stdin)")
    s.add_argument("event", choices=["pre", "stop", "session-start"])
    s.add_argument("--platform", required=True, choices=list(ADAPTERS)); s.set_defaults(f=cmd_hook)
    s = sub.add_parser("install", help="instala o actualiza Monday en un proyecto")
    s.add_argument("target"); s.add_argument("--platform", action="append", choices=list(ADAPTERS))
    s.add_argument("--dry-run", action="store_true"); s.add_argument("--force", action="store_true")
    s.set_defaults(f=cmd_install)
    s = sub.add_parser("rollback", help="revierte la última instalación/actualización")
    s.add_argument("target", nargs="?", default=".")
    s.add_argument("--all", action="store_true", help="revierte todas (desinstalación completa)")
    s.add_argument("--dry-run", action="store_true"); s.add_argument("--force", action="store_true")
    s.set_defaults(f=cmd_rollback)
    a = p.parse_args(argv)
    try:
        return a.f(a)
    except MondayError as e:
        print(f"monday: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
