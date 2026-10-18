#!/usr/bin/env python3
"""Monday helper: deterministic checks and tooling for the Monday AI engineering harness.

  monday.py tier <TIER> --platform <claude-code|antigravity>   model/effort for a tier
  monday.py role <executor|reviewer|orchestrator> --platform P  tier + model/effort for a role (active posture)
  monday.py validate [--contract C] [--strict-schema] <contract|report|agent.yaml>...
                                                             structural check by kind; --contract also checks report gates
  monday.py check-scope <contract.yaml> [--base REF] [--allow-untracked-contract] [--include-ignored] [--no-include-ignored]
                                                             gate G5: changes since REF (default HEAD) vs contract scope
  monday.py cap status [NAME] [--active NAME] [--authorized CAP1,CAP2] [--contract C]
                                                             inspect 4 capability lifecycle states (Disponible, Autorizada, Preparada, Activa)
  monday.py init [PROJECT_DIR]                               create .monday/ with CONTEXT.md, contracts/ and reports/

Exit codes: 0 ok, 1 check failed, 2 usage/config error. Requires PyYAML.
"""
import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys

def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


try:
    import yaml
except ImportError:
    die("monday.py: PyYAML is required (pip install pyyaml)")

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
PROFILES = os.path.join(ROOT, "routing", "profiles.yaml")

LEVELS = ["L0", "L1", "L2", "L3", "L4", "L5"]
RISKS = ["low", "medium", "high", "critical"]
TIERS = ["FAST", "STANDARD", "DEEP", "MAX"]
# Single status vocabulary for delegated answers and reports (methodology/routing.md §4).
STATUS = ["DONE", "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED", "ESCALATE", "FAILED"]
DELEGATION = ["none", "down", "any"]
GATE_RESULTS = ["pass", "fail", "not_run"]
TASK_REQUIRED = {
    "L2": ["id", "level", "risk", "objective", "scope", "acceptance_criteria", "verification"],
    "L3": ["context", "routing"],
}

TASK_ALLOWED_KEYS = {
    "id", "parent", "level", "risk", "objective", "context", "interfaces",
    "role", "scope", "permissions", "constraints", "dependencies",
    "acceptance_criteria", "verification", "human_gates", "deliverables",
    "routing", "escalation_rules", "schema"
}
SCOPE_ALLOWED_KEYS = {"allowed_files", "allowed_directories", "excluded_areas", "capabilities"}
PERMISSIONS_ALLOWED_KEYS = {"commands", "network", "write_memory"}
PERMISSIONS_COMMANDS_KEYS = {"allow", "ask", "deny"}
VERIFICATION_ALLOWED_KEYS = {"commands", "gates", "seams"}
ROUTING_ALLOWED_KEYS = {
    "mode", "preferred_tier", "preferred_effort", "preferred_model",
    "allow_delegation", "reviewer_tier", "escalation_policy"
}
CONTEXT_ALLOWED_KEYS = {"read_first", "background", "interfaces"}

REPORT_ALLOWED_KEYS = {
    "contract", "task", "status", "verified", "route", "delegations",
    "what_changed", "files_affected", "interface_changes", "tests_executed",
    "verification_results", "rulings", "contract_deviations",
    "unexpected_findings", "remaining_risks", "follow_up_recommendations",
    "learnings", "schema"
}
REPORT_TEST_KEYS = {"command", "result"}
REPORT_GATE_KEYS = {"gate", "result", "evidence"}
TRIVIAL_EVIDENCE = {"ok", "pass", "passed", "done", "true", "yes", "verified", "-", "..."}

AGENT_ALLOWED_KEYS = {
    "name", "role", "purpose", "default_tier", "capabilities",
    "authority", "returns", "escalates_when", "schema"
}
AGENT_CAPABILITIES_KEYS = {"tools"}
AGENT_AUTHORITY_KEYS = {"write", "delegate", "commands_allow", "commands_deny"}


def check_unknown_keys(mapping, allowed, context_name):
    if not isinstance(mapping, dict):
        return []
    errs = []
    for k in sorted(mapping.keys()):
        if k not in allowed:
            suggestion = ""
            if k in ("exclude_areas", "excluded_area", "excluded_file", "excluded_files"):
                suggestion = " (did you mean 'excluded_areas'?)"
            elif k in ("allowed_file", "allowed_dir", "allowed_dirs"):
                suggestion = f" (did you mean '{k}s'?)"
            elif k in ("command", "cmd", "cmds"):
                suggestion = " (did you mean 'commands'?)"
            elif k == "interface":
                suggestion = " (did you mean 'interfaces'?)"
            elif k == "human_gate":
                suggestion = " (did you mean 'human_gates'?)"
            elif k == "acceptance_criterion":
                suggestion = " (did you mean 'acceptance_criteria'?)"
            errs.append(f"unknown key in {context_name}: '{k}'{suggestion}")
    return errs


def load_yaml(path):
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as e:
        die(f"monday.py: cannot read {path}: {e}")


def platform_cfg(platform):
    prof = load_yaml(PROFILES)
    plat = prof.get("platforms", {}).get(platform)
    if not plat:
        die(f"monday.py: unknown platform '{platform}' (see routing/profiles.yaml)")
    return prof, plat


def print_tier(plat, tier):
    t = plat.get("tiers", {}).get(tier)
    if not t:
        die(f"monday.py: unknown tier '{tier}' (expected one of {TIERS})")
    # Shell-safe assignments: `eval "$(monday.py tier DEEP --platform claude-code)"` sets $model and $effort.
    print(f"tier={tier} model={shlex.quote(t['model'])} effort={shlex.quote(t['effort'])}")
    if t.get("alternative"):
        print(f"alternative={shlex.quote(t['alternative'])}")


def cmd_tier(a):
    _, plat = platform_cfg(a.platform)
    print_tier(plat, a.tier.upper())


def cmd_role(a):
    prof, plat = platform_cfg(a.platform)
    posture = prof.get("postures", {}).get(prof.get("active_posture", "default"), {})
    tier = posture.get(a.role)
    if not tier:
        die(f"monday.py: role '{a.role}' not in active posture")
    print_tier(plat, tier)


def is_safe_rel_path(path):
    """Ensure path does not escape repo root via traversal (..), absolute path, drive letter or UNC.
    Checks the raw string and its stripped form (glob_re strips patterns), so padding cannot hide an escape."""
    if not isinstance(path, str) or not path.strip():
        return False
    for p in (path, path.strip()):
        # POSIX absolute, UNC (// or \\), Windows drive letter (C:, C:\, C:/)
        if p.startswith(("/", "\\")) or os.path.isabs(p) or re.match(r"[a-zA-Z]:", p):
            return False
        # Any '..' segment, with either separator, even padded: never normalized away first
        if any(seg.strip() == ".." for seg in re.split(r"[/\\]+", p)):
            return False
    return True


SCOPE_KEYS = ("allowed_files", "allowed_directories", "excluded_areas")


def scope_lists(d):
    """Scope patterns by key plus type errors: scope must be a mapping, each key absent or a list of non-empty strings."""
    scope = d.get("scope")
    if scope is None or scope == "":
        scope = {}
    if not isinstance(scope, dict):
        return {k: [] for k in SCOPE_KEYS}, ["scope must be a mapping"]
    out, errs = {}, []
    errs += check_unknown_keys(scope, SCOPE_ALLOWED_KEYS, "scope")
    for k in SCOPE_KEYS:
        v = scope.get(k)
        if v is None:
            v = []
        if not isinstance(v, list) or not all(isinstance(p, str) and p.strip() for p in v):
            errs.append(f"scope.{k} must be a list of non-empty strings")
            v = [p for p in v if isinstance(p, str) and p.strip()] if isinstance(v, list) else []
        out[k] = v
    caps = scope.get("capabilities")
    if caps is not None:
        if not isinstance(caps, list) or not all(isinstance(p, str) and p.strip() for p in caps):
            errs.append("scope.capabilities must be a list of non-empty strings")
            caps = [p for p in caps if isinstance(p, str) and p.strip()] if isinstance(caps, list) else []
        out["capabilities"] = caps
    else:
        out["capabilities"] = []
    return out, errs


def is_empty(v):
    return v is None or v == "" or v == [] or v == {} or (isinstance(v, str) and v.strip() in ("...", "-"))


IFACE_RISKS = ["medium", "high", "critical"]
NONE_MODIFIED = "none_modified"


def get_interfaces(d):
    """Interface declaration: context.interfaces (template location) or top-level interfaces."""
    ctx = d.get("context")
    if isinstance(ctx, dict) and "interfaces" in ctx:
        return ctx["interfaces"]
    return d.get("interfaces")


def interface_errors(d):
    """Interface Integrity Gate (contract side): L2+ with risk >= medium must declare interfaces explicitly."""
    ifc = get_interfaces(d)
    if ifc == NONE_MODIFIED:
        return []
    if isinstance(ifc, dict) and (ifc.get("consumes") or ifc.get("produces")):
        return []
    if ifc is None:
        why = "missing"
    elif isinstance(ifc, dict):
        why = "ambiguously empty"
    else:
        why = "invalid"
    return [f"interfaces {why} (required at L2+ with risk medium/high/critical): "
            f"declare 'interfaces: {NONE_MODIFIED}' or a dict with non-empty consumes/produces"]


def validate_task(d):
    errs = []
    errs += check_unknown_keys(d, TASK_ALLOWED_KEYS, "task")
    if "context" in d and isinstance(d["context"], dict):
        errs += check_unknown_keys(d["context"], CONTEXT_ALLOWED_KEYS, "context")
    if "permissions" in d and isinstance(d["permissions"], dict):
        errs += check_unknown_keys(d["permissions"], PERMISSIONS_ALLOWED_KEYS, "permissions")
        cmds = d["permissions"].get("commands")
        if isinstance(cmds, dict):
            errs += check_unknown_keys(cmds, PERMISSIONS_COMMANDS_KEYS, "permissions.commands")
    if "verification" in d and isinstance(d["verification"], dict):
        errs += check_unknown_keys(d["verification"], VERIFICATION_ALLOWED_KEYS, "verification")
    if "routing" in d and isinstance(d["routing"], dict):
        errs += check_unknown_keys(d["routing"], ROUTING_ALLOWED_KEYS, "routing")
    if d.get("schema") is not None and d.get("schema") != 1:
        errs.append(f"unsupported schema version '{d.get('schema')}' (expected 1)")
    level = d.get("level")
    if level not in LEVELS:
        errs.append(f"level must be one of {LEVELS}")
        level = "L2"  # keep checking as the lightest written contract, so every error is reported at once
    required = []
    for lv, fields in TASK_REQUIRED.items():
        if LEVELS.index(level) >= LEVELS.index(lv):
            required += fields
    errs += [f"missing or empty field '{k}' (required at {level})" for k in required if is_empty(d.get(k))]
    if d.get("risk") is not None and d["risk"] not in RISKS:
        errs.append(f"risk must be one of {RISKS}")
    crit = d.get("acceptance_criteria") or []
    if any(is_empty(c) for c in crit):
        errs.append("acceptance_criteria contains placeholder entries")
    r = d.get("routing") or {}
    if r.get("preferred_tier") not in (None, *TIERS):
        errs.append(f"routing.preferred_tier must be one of {TIERS}")
    if r.get("allow_delegation") not in (None, *DELEGATION):
        errs.append(f"routing.allow_delegation must be one of {DELEGATION}")
    if LEVELS.index(level) >= LEVELS.index("L2") and d.get("risk") in IFACE_RISKS:
        errs += interface_errors(d)
    if d.get("risk") == "critical" and is_empty(d.get("human_gates")):
        errs.append("risk critical requires explicit human_gates")
    scope, scope_errs = scope_lists(d)
    errs += scope_errs
    if "scope" in required and not (scope["allowed_files"] or scope["allowed_directories"]):
        errs.append("scope needs allowed_files or allowed_directories")
    for p in scope["allowed_files"] + scope["allowed_directories"] + scope["excluded_areas"]:
        if not is_safe_rel_path(p):
            errs.append(f"scope path '{p}' escapes repository (path traversal or absolute path)")
    if "verification" in required and is_empty((d.get("verification") or {}).get("commands")):
        errs.append("verification.commands is empty: name at least one real, red-capable command")
    return errs


def task_warnings(d, path):
    warns = []
    scope, _ = scope_lists(d)
    for p in scope["allowed_files"] + scope["allowed_directories"]:
        if p.strip().rstrip("/*").count("/") == 0 and ("*" in p or p.endswith("/")):
            warns.append(f"broad scope '{p}': prefer concrete paths and list nearby sensitive areas in excluded_areas")
    folder = os.path.dirname(os.path.abspath(path))
    if d.get("id") and os.path.basename(folder) == "contracts":
        for f in sorted(os.listdir(folder)):
            other = os.path.join(folder, f)
            if f.endswith((".yaml", ".yml")) and other != os.path.abspath(path):
                if (load_yaml(other) or {}).get("id") == d["id"]:
                    warns.append(f"id '{d['id']}' already used by {f}")
    return warns


AGENT_REQUIRED = ["name", "role", "purpose", "default_tier", "returns"]
AGENT_ROLES = ["executor", "specialist", "reviewer"]


def validate_agent(d):
    errs = []
    errs += check_unknown_keys(d, AGENT_ALLOWED_KEYS, "agent")
    if "capabilities" in d and isinstance(d["capabilities"], dict):
        errs += check_unknown_keys(d["capabilities"], AGENT_CAPABILITIES_KEYS, "capabilities")
    if "authority" in d and isinstance(d["authority"], dict):
        errs += check_unknown_keys(d["authority"], AGENT_AUTHORITY_KEYS, "authority")
    if d.get("schema") is not None and d.get("schema") != 1:
        errs.append(f"unsupported schema version '{d.get('schema')}' (expected 1)")
    errs += [f"missing or empty field '{k}'" for k in AGENT_REQUIRED if is_empty(d.get(k))]
    if d.get("role") is not None and d["role"] not in AGENT_ROLES:
        errs.append(f"role must be one of {AGENT_ROLES}")
    if d.get("default_tier") is not None and d["default_tier"] not in TIERS:
        errs.append(f"default_tier must be one of {TIERS}")
    if (d.get("authority") or {}).get("delegate") not in (None, *DELEGATION):
        errs.append(f"authority.delegate must be one of {DELEGATION}")
    return errs


def classify(d):
    if "status" in d and "objective" not in d:
        return "report"
    if "objective" not in d and "level" not in d and ("default_tier" in d or "authority" in d):
        return "agent"
    return "task"


def validate_report(d, contract=None):
    errs = []
    errs += check_unknown_keys(d, REPORT_ALLOWED_KEYS, "report")
    for idx, t in enumerate(d.get("tests_executed") or []):
        if isinstance(t, dict):
            errs += check_unknown_keys(t, REPORT_TEST_KEYS, f"tests_executed[{idx}]")
            if d.get("schema") == 1:
                cmd = t.get("command")
                res = t.get("result")
                if is_empty(cmd) or (isinstance(cmd, str) and (len(cmd.strip()) < 2 or cmd.strip() == "...")):
                    errs.append(f"tests_executed[{idx}]: 'command' is empty or placeholder (schema: 1 requires substantive command)")
                if is_empty(res) or (isinstance(res, str) and (len(res.strip()) < 2 or res.strip().lower() in TRIVIAL_EVIDENCE)):
                    errs.append(f"tests_executed[{idx}]: 'result' is empty or trivial placeholder (schema: 1 requires substantive observed result)")
        elif d.get("schema") == 1:
            errs.append(f"tests_executed[{idx}] must be a mapping with 'command' and 'result' (schema: 1)")
    for idx, v in enumerate(d.get("verification_results") or []):
        if isinstance(v, dict):
            errs += check_unknown_keys(v, REPORT_GATE_KEYS, f"verification_results[{idx}]")
    if d.get("schema") is not None and d.get("schema") != 1:
        errs.append(f"unsupported schema version '{d.get('schema')}' (expected 1)")
    if d.get("status") not in STATUS:
        errs.append(f"status must be one of {STATUS}")
    if is_empty(d.get("task")):
        errs.append("missing 'task'")
    results = d.get("verification_results") or []
    for v in results:
        if v.get("result") not in GATE_RESULTS:
            errs.append(f"gate {v.get('gate')}: result must be one of {GATE_RESULTS}")
        if v.get("result") == "pass":
            ev = v.get("evidence")
            if is_empty(ev):
                errs.append(f"gate {v.get('gate')}: pass without evidence")
            elif isinstance(ev, str) and (len(ev.strip()) < 3 or ev.strip().lower() in TRIVIAL_EVIDENCE):
                if d.get("schema") == 1:
                    errs.append(f"gate {v.get('gate')}: pass with trivial placeholder evidence '{ev}' (schema: 1 requires substantive evidence)")
    if d.get("status") in ("DONE", "DONE_WITH_CONCERNS"):
        if not results:
            errs.append("status DONE without verification_results")
        if any(v.get("result") == "fail" for v in results):
            errs.append("status DONE with a failed gate")
        if d.get("status") == "DONE":
            if d.get("verified") is not True:
                errs.append("status DONE requires verified: true")
            errs += [f"status DONE with gate {v.get('gate')} {v.get('result')}" for v in results if v.get("result") == "not_run"]
        elif d.get("verified") is True and any(v.get("result") == "not_run" for v in results):
            errs.append("verified: true but some gate is not_run")
    ic = d.get("interface_changes")
    if is_empty(ic):
        errs.append("missing 'interface_changes' (use 'none' or a non-empty list of changes)")
    elif ic != "none" and not (isinstance(ic, list) and all(not is_empty(c) for c in ic)):
        errs.append("interface_changes must be 'none' or a non-empty list of changes")
    if contract is not None:
        if get_interfaces(contract) == NONE_MODIFIED and not is_empty(ic) and ic != "none":
            errs.append("interface_changes declares changes but the contract declared 'interfaces: none_modified'")
        reported = {str(v.get("gate")) for v in results}
        errs += [f"contract gate {g} missing from verification_results"
                 for g in (contract.get("verification") or {}).get("gates") or [] if str(g) not in reported]
        contract_cmds = (contract.get("verification") or {}).get("commands") or []
        if contract_cmds and is_empty(d.get("tests_executed")):
            if d.get("schema") == 1:
                errs.append("contract requires verification.commands but report has empty 'tests_executed' (schema: 1)")
    return errs


def cmd_validate(a):
    failed = False
    contract = load_yaml(a.contract) if a.contract else None
    for path in a.files:
        d = load_yaml(path)
        kind = classify(d)
        schema_version = d.get("schema")
        schema_errs = []
        if schema_version is None:
            if getattr(a, "strict_schema", False):
                schema_errs.append("missing 'schema: 1' (required under --strict-schema)")
            else:
                print(f"{path}: warning: missing 'schema: 1'; unversioned contracts are deprecated and will require explicit schema in Monday v1.0", file=sys.stderr)
        errs = schema_errs + (validate_report(d, contract) if kind == "report" else validate_agent(d) if kind == "agent" else validate_task(d))
        for e in errs:
            print(f"{path}: {e}")
        for w in (task_warnings(d, path) if kind == "task" else []):
            print(f"{path}: warning: {w}")
        if not errs:
            print(f"{path}: ok ({kind})")
        failed |= bool(errs)
    sys.exit(1 if failed else 0)


def git(*args, check=True):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    if r.returncode != 0:
        if not check:
            return None
        die(f"monday.py: git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def git_paths(*args):
    # -z: raw paths, no quoting of non-ASCII names.
    return [p for p in git(*args, "-z").split("\0") if p]


def glob_re(pattern):
    """Path glob: `*` and `?` stay inside one segment, `**` crosses segments, a trailing `/` means the whole directory."""
    p = pattern.strip()
    if p.endswith("/"):
        p += "**"
    out, i = "", 0
    while i < len(p):
        if p.startswith("**/", i):
            out += "(?:.*/)?"; i += 3
        elif p.startswith("**", i):
            out += ".*"; i += 2
        elif p[i] == "*":
            out += "[^/]*"; i += 1
        elif p[i] == "?":
            out += "[^/]"; i += 1
        else:
            out += re.escape(p[i]); i += 1
    return re.compile(out + r"(?:/.*)?\Z")  # a pattern naming a directory also covers its contents


def matches(path, patterns):
    return any(glob_re(p).match(path) for p in patterns)


def is_bytecache(path):
    p = path.replace("\\", "/")
    return (
        "/__pycache__/" in p
        or p.startswith("__pycache__/")
        or p.endswith((".pyc", ".pyo"))
        or p == ".coverage"
        or "/.pytest_cache/" in p
        or p.startswith(".pytest_cache/")
    )


def cmd_check_scope(a):
    top = git("rev-parse", "--show-toplevel").strip()
    contract_rel = os.path.relpath(os.path.abspath(a.contract), top)
    d = load_yaml(a.contract)
    problems = []
    # Read the scope from the base revision when the contract is tracked, so editing it cannot widen it.
    at_base = git("-C", top, "show", f"{a.base}:{contract_rel}", check=False)
    if at_base is not None:
        try:
            base_d = yaml.safe_load(at_base) or {}
        except yaml.YAMLError as e:
            die(f"monday.py: cannot parse {contract_rel} at {a.base}: {e}")
        if base_d != d:
            problems.append(f"CONTRACT MODIFIED since {a.base}: {contract_rel}")
        d = base_d
    elif a.allow_untracked_contract:
        print(f"warning: {contract_rel} is not tracked at {a.base}; scope edits to it cannot be detected", file=sys.stderr)
    else:
        problems.append(f"CONTRACT NOT TRACKED at {a.base}: {contract_rel} (commit it before delegating, or pass --allow-untracked-contract)")
    scope, scope_errs = scope_lists(d)
    if scope_errs:
        die("monday.py: invalid contract scope: " + "; ".join(scope_errs))
    allowed = scope["allowed_files"] + scope["allowed_directories"]
    excluded = scope["excluded_areas"]
    if not allowed:
        die("monday.py: contract has no allowed_files/allowed_directories")
    real_top = os.path.realpath(top)
    for p in allowed + excluded:
        if not is_safe_rel_path(p):
            problems.append(f"SECURITY VIOLATION (scope rule escapes repo): {p}")
    # Always-allowed deliverables: this contract's report (in .monday or legacy .agentforge)
    c_id = d.get('id', '')
    exempt = [f".monday/reports/{c_id}.yaml", f".agentforge/reports/{c_id}.yaml"]
    if (d.get("permissions") or {}).get("write_memory"):
        exempt += [
            ".monday/CONTEXT.md", ".monday/decisions.md", ".monday/learnings.md",
            ".agentforge/CONTEXT.md", ".agentforge/decisions.md", ".agentforge/learnings.md",
        ]
    changed = set(git_paths("-C", top, "diff", "--name-only", "--no-renames", a.base))
    changed |= set(git_paths("-C", top, "ls-files", "--others", "--exclude-standard"))
    raw_ignored = git_paths("-C", top, "ls-files", "--others", "--ignored", "--exclude-standard")
    ignored_files = [p for p in raw_ignored if not is_bytecache(p)]

    # Ignored non-bytecache files in excluded_areas are ALWAYS flagged (prevents stealth breaches in ignored paths)
    for f in ignored_files:
        if matches(f, excluded):
            changed.add(f)

    # In schema: 1 contracts, audit all non-bytecache ignored files by default (opt-out with --no-include-ignored).
    # In legacy contracts, audit them if --include-ignored is explicitly passed.
    auto_include = (d.get("schema") == 1 and not getattr(a, "no_include_ignored", False))
    if getattr(a, "include_ignored", False) or auto_include:
        changed |= set(ignored_files)
    # The contract (reported above as CONTRACT MODIFIED if it changed) and the exempt deliverables skip the
    # scope match, but not the security checks: neither may be a symlink that leads somewhere else.
    skip = set(exempt) | {contract_rel}
    security_violators = set()
    for c in sorted(changed):
        if not is_safe_rel_path(c):
            problems.append(f"SECURITY VIOLATION (path traversal outside repo): {c}")
            security_violators.add(c)
            continue
        full_path = os.path.join(top, c)
        try:
            real_c = os.path.realpath(full_path)
            rel_to_top = os.path.relpath(real_c, real_top).replace(os.sep, "/")  # git paths always use '/'
            if rel_to_top == ".." or rel_to_top.startswith("../") or os.path.isabs(rel_to_top):
                problems.append(f"SECURITY VIOLATION (symlink escape outside repo): {c} -> {real_c}")
                security_violators.add(c)
            elif rel_to_top != c and (c in skip or matches(rel_to_top, excluded) or not matches(rel_to_top, allowed)):
                # A symlink (or symlinked parent) whose effective target is outside the contract scope.
                problems.append(f"SECURITY VIOLATION (symlink resolves out of scope): {c} -> {rel_to_top}")
                security_violators.add(c)
        except Exception as e:
            problems.append(f"SECURITY VIOLATION (cannot resolve path {c}): {e}")
            security_violators.add(c)
    changed = {c for c in changed if c in security_violators or c not in skip}
    out = sorted({c for c in changed if c in security_violators or matches(c, excluded) or not matches(c, allowed)})
    for c in out:
        if c in security_violators:
            reason = "security_violation"
        elif matches(c, excluded):
            reason = "excluded_area"
        else:
            reason = "not in scope"
        problems.append(f"OUT OF SCOPE ({reason}): {c}")
    for p in problems:
        print(p)
    if not changed:
        print(f"warning: no changes against {a.base}; if the executor committed, pass --base <start commit>", file=sys.stderr)
    print(f"G5 scope: {'fail' if problems else 'pass'} — {len(changed)} changed, {len(out)} out of scope (base {a.base})")
    sys.exit(1 if problems else 0)


def cmd_cap(a):
    cat_path = getattr(a, "catalog", None) or os.path.join(ROOT, "capabilities", "catalog.yaml")
    if not os.path.exists(cat_path):
        die(f"monday.py: capabilities catalog not found at {cat_path}")
    catalog = load_yaml(cat_path).get("capabilities", {})
    if a.name:
        if a.name not in catalog:
            die(f"monday.py: unknown capability '{a.name}' (available: {', '.join(sorted(catalog.keys()))})")
        targets = {a.name: catalog[a.name]}
    else:
        targets = catalog

    authorized_set = set()
    has_auth_filter = False
    if getattr(a, "contract", None):
        has_auth_filter = True
        c_data = load_yaml(a.contract)
        c_scope, _ = scope_lists(c_data) if isinstance(c_data, dict) else ({}, [])
        for cap in c_scope.get("capabilities", []):
            authorized_set.add(cap)
    if getattr(a, "authorized", None):
        has_auth_filter = True
        for cap in a.authorized.split(","):
            if cap.strip():
                authorized_set.add(cap.strip())

    failed = False
    for name, item in sorted(targets.items()):
        cmd = item.get("check_cmd")
        prepared = False
        if cmd:
            try:
                parts = [os.path.expanduser(p) for p in shlex.split(cmd)]
                r = subprocess.run(parts, capture_output=True, text=True, cwd=ROOT)
                prepared = (r.returncode == 0)
            except (OSError, ValueError):
                prepared = False
        else:
            prepared = True

        is_authorized = (name in authorized_set) if has_auth_filter else True
        is_active = (getattr(a, "active", None) == name)

        if is_active and prepared and is_authorized:
            state = "Activa"
        elif prepared:
            if has_auth_filter and not is_authorized:
                state = "Disponible"
            else:
                state = "Preparada"
        elif is_authorized and has_auth_filter:
            state = "Autorizada"
        else:
            state = "Disponible"

        prep_str = "ok" if prepared else "failed"
        print(f"capability={name} state={state} prepared={prep_str} category={item.get('category', 'custom')} tier={item.get('tier', 'FAST')}")
        if not prepared and a.name:
            failed = True
    if failed:
        sys.exit(1)


def check_safe_migration_tree(src_dir, base_proj):
    """Audit legacy directory before migration to ensure no symlink escapes."""
    real_proj = os.path.realpath(base_proj)
    if os.path.islink(src_dir):
        target = os.path.realpath(src_dir)
        if target == real_proj or not target.startswith(real_proj + os.sep):
            return False, f"legacy directory itself is an external symlink: {src_dir} -> {target}"
    real_src = os.path.realpath(src_dir)
    for root, dirs, files in os.walk(src_dir):
        for name in dirs + files:
            p = os.path.join(root, name)
            if os.path.islink(p):
                target = os.path.realpath(p)
                if not (target == real_src or target.startswith(real_src + os.sep)):
                    return False, f"unsafe symlink escapes legacy directory: {os.path.relpath(p, src_dir)} -> {target}"
    return True, None


def cmd_init(a):
    target = os.path.join(a.project, ".monday")
    legacy = os.path.join(a.project, ".agentforge")

    if getattr(a, "migrate_legacy", False):
        if not os.path.isdir(legacy):
            die(f"monday init: no legacy directory found at {legacy}")
        if os.path.exists(target):
            die(f"monday init: target {target} already exists; aborting migration to prevent overwriting existing Monday project")
        safe, reason = check_safe_migration_tree(legacy, a.project)
        if not safe:
            die(f"monday init: cannot migrate legacy directory: {reason}")
        shutil.copytree(legacy, target, symlinks=True)
        print(f"migrated {legacy} -> {target} (original preserved at {legacy})")
        return

    if os.path.exists(target) and not os.path.isdir(target):
        die(f"monday init: target {target} exists and is not a directory")

    if not os.path.exists(target) and os.path.isdir(legacy):
        print(f"notice: legacy directory '.agentforge' exists in {a.project}; run 'monday init --migrate-legacy' to migrate historical data to '.monday'", file=sys.stderr)

    for sub in ("contracts", "reports"):
        os.makedirs(os.path.join(target, sub), exist_ok=True)
    ctx = os.path.join(target, "CONTEXT.md")
    if os.path.exists(ctx):
        print(f"{ctx} already exists; left untouched")
        return
    tmpl = os.path.join(ROOT, "contracts", "templates", "CONTEXT.md")
    if os.path.exists(tmpl):
        with open(tmpl) as src, open(ctx, "w") as dst:
            dst.write(src.read())
    else:
        with open(ctx, "w") as dst:
            dst.write("# Monday — Context\n\nFuente de verdad del lenguaje y restricciones del proyecto.\n")
    print(f"created {ctx}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("tier"); s.add_argument("tier"); s.add_argument("--platform", required=True); s.set_defaults(f=cmd_tier)
    s = sub.add_parser("role"); s.add_argument("role"); s.add_argument("--platform", required=True); s.set_defaults(f=cmd_role)
    s = sub.add_parser("validate"); s.add_argument("files", nargs="+"); s.add_argument("--contract"); s.add_argument("--strict-schema", action="store_true"); s.set_defaults(f=cmd_validate)
    s = sub.add_parser("check-scope"); s.add_argument("contract"); s.add_argument("--base", default="HEAD"); s.add_argument("--allow-untracked-contract", action="store_true"); s.add_argument("--include-ignored", action="store_true"); s.add_argument("--no-include-ignored", action="store_true"); s.set_defaults(f=cmd_check_scope)
    s = sub.add_parser("cap")
    cap_sub = s.add_subparsers(dest="cap_cmd", required=True)
    c_status = cap_sub.add_parser("status")
    c_status.add_argument("name", nargs="?", default=None)
    c_status.add_argument("--active", default=None)
    c_status.add_argument("--authorized", default=None)
    c_status.add_argument("--contract", default=None)
    c_status.add_argument("--catalog", default=None, help="Explicit path to capabilities catalog")
    c_status.set_defaults(f=cmd_cap)
    s = sub.add_parser("init"); s.add_argument("project", nargs="?", default="."); s.add_argument("--migrate-legacy", action="store_true", help="Migrate existing .agentforge directory to .monday safely preserving original"); s.set_defaults(f=cmd_init)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
