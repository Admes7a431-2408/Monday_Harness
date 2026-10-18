#!/usr/bin/env python3
"""Monday regression suite: Interface Integrity Gate (I1-I9), capability lifecycle, scripts/monday.py / install.sh tooling.

Run: python3 tests/test_monday.py   (or: python3 -m unittest tests/test_monday.py)
Requires PyYAML. Deterministic: no network, temp dirs only, HOME redirected for install.sh.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
MONDAY = os.path.join(ROOT, "scripts", "monday.py")
AF = os.path.join(ROOT, "scripts", "af.py")
INSTALL = os.path.join(ROOT, "install.sh")


def run(args, cwd=None, env=None):
    return subprocess.run(args, capture_output=True, text=True, cwd=cwd, env=env)


def monday(*args, cwd=None):
    return run([sys.executable, MONDAY, *args], cwd=cwd)



class TempDirCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="monday-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def write(self, name, data, base=None):
        path = os.path.join(base or self.tmp, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            if isinstance(data, str):
                f.write(data)
            else:
                yaml.safe_dump(data, f, sort_keys=False)
        return path


def contract(**over):
    d = {
        "id": "T-1",
        "level": "L2",
        "risk": "medium",
        "objective": "do a thing",
        "context": {"interfaces": "none_modified"},
        "scope": {"allowed_files": ["src/a.py"]},
        "acceptance_criteria": ["works"],
        "verification": {"commands": ["python3 -m unittest"], "gates": ["G1", "G5"]},
    }
    d.update(over)
    for k in [k for k, v in d.items() if v is ...]:
        del d[k]
    return d


def report(**over):
    d = {
        "contract": "T-1",
        "task": "do a thing",
        "status": "DONE",
        "verified": True,
        "interface_changes": "none",
        "verification_results": [
            {"gate": "G1", "result": "pass", "evidence": "ok"},
            {"gate": "G5", "result": "pass", "evidence": "ok"},
        ],
    }
    d.update(over)
    return d


class InterfaceIntegrityGate(TempDirCase):
    """Batería I1-I9."""

    def validate(self, d, *extra):
        p = self.write("c.yaml", d)
        return monday("validate", p, *extra)

    def assertRejectedForInterfaces(self, d):
        r = self.validate(d)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("interfaces", r.stdout)

    def test_i1_none_modified_passes(self):
        r = self.validate(contract())
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("ok (task)", r.stdout)

    def test_i1_top_level_none_modified_passes(self):
        r = self.validate(contract(context=..., interfaces="none_modified"))
        self.assertEqual(r.returncode, 0, r.stdout)

    # I2..I7: a task that mutates an interface must declare it; omitting or emptying the declaration fails.
    MUTATIONS = {
        "i2_add_field": {"produces": ["Order.discount (new field)"]},
        "i3_remove_field": {"produces": ["Order.legacy_id (removed)"]},
        "i4_rename_field": {"produces": ["Order.qty -> Order.quantity"]},
        "i5_change_type": {"produces": ["Order.price: int -> Decimal"]},
        "i6_signature": {"consumes": ["pricing.compute(order, tax) -> pricing.compute(order)"]},
        "i7_api_schema": {"produces": ["POST /orders response schema v2"]},
    }

    def test_i2_to_i7_mutation_without_declaration_fails(self):
        for name in self.MUTATIONS:
            with self.subTest(name):
                self.assertRejectedForInterfaces(contract(context=...))

    def test_i2_to_i7_mutation_with_empty_declaration_fails(self):
        for name in self.MUTATIONS:
            for empty in ({}, {"consumes": [], "produces": []}, None, ""):
                with self.subTest(name=name, empty=empty):
                    self.assertRejectedForInterfaces(contract(context={"interfaces": empty}))

    def test_i2_to_i7_mutation_with_declaration_passes(self):
        for name, decl in self.MUTATIONS.items():
            with self.subTest(name):
                r = self.validate(contract(context={"interfaces": decl}))
                self.assertEqual(r.returncode, 0, r.stdout)

    def test_i8_consumes_produces_declared_passes(self):
        d = contract(context={"interfaces": {"consumes": ["db.users"], "produces": ["GET /users"]}})
        r = self.validate(d)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_i9_l2_medium_missing_fails(self):
        self.assertRejectedForInterfaces(contract(context=...))
        self.assertIn("missing", self.validate(contract(context=...)).stdout)

    def test_i9_l2_medium_ambiguously_empty_fails(self):
        d = contract(context={"interfaces": {"consumes": [], "produces": []}})
        self.assertRejectedForInterfaces(d)
        self.assertIn("ambiguously empty", self.validate(d).stdout)

    def test_i9_applies_to_higher_risks(self):
        for risk, extra in (("high", {}), ("critical", {"human_gates": ["merge"]})):
            with self.subTest(risk):
                self.assertRejectedForInterfaces(contract(context=..., risk=risk, **extra))

    def test_i9_low_risk_not_required(self):
        r = self.validate(contract(context=..., risk="low"))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_cross_report_changes_vs_none_modified_fails(self):
        c = self.write("contract.yaml", contract())
        rep = self.write("report.yaml", report(interface_changes=["Order.discount added"]))
        r = monday("validate", rep, "--contract", c)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("none_modified", r.stdout)

    def test_cross_report_none_vs_none_modified_passes(self):
        c = self.write("contract.yaml", contract())
        rep = self.write("report.yaml", report())
        r = monday("validate", rep, "--contract", c)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_cross_report_changes_with_declared_interfaces_passes(self):
        c = self.write("contract.yaml", contract(context={"interfaces": {"produces": ["Order"]}}))
        rep = self.write("report.yaml", report(interface_changes=["Order.discount added"]))
        r = monday("validate", rep, "--contract", c)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_report_without_interface_changes_fails(self):
        d = report()
        del d["interface_changes"]
        r = monday("validate", self.write("r.yaml", d))
        self.assertEqual(r.returncode, 1)
        self.assertIn("interface_changes", r.stdout)


class TierResolution(unittest.TestCase):
    EXPECTED = {
        "claude-code": {
            "FAST": ("haiku", "low"), "STANDARD": ("sonnet", "medium"),
            "DEEP": ("opus", "high"), "MAX": ("fable", "xhigh"),
        },
        "antigravity": {
            "FAST": ("gemini-3.8-flash-low", "low"), "STANDARD": ("gemini-3.8-flash-medium", "medium"),
            "DEEP": ("gemini-3.1-pro-high", "high"), "MAX": ("gemini-3.1-pro-high", "xhigh"),
        },
    }

    def test_all_tiers_both_platforms(self):
        for platform, tiers in self.EXPECTED.items():
            for tier, (model, effort) in tiers.items():
                with self.subTest(platform=platform, tier=tier):
                    r = monday("tier", tier, "--platform", platform)
                    self.assertEqual(r.returncode, 0, r.stderr)
                    self.assertIn(f"tier={tier} model={model} effort={effort}", r.stdout)

    def test_tier_is_case_insensitive(self):
        r = monday("tier", "fast", "--platform", "claude-code")
        self.assertEqual(r.returncode, 0)
        self.assertIn("tier=FAST", r.stdout)

    def test_unknown_tier_and_platform(self):
        self.assertEqual(monday("tier", "ULTRA", "--platform", "claude-code").returncode, 2)
        self.assertEqual(monday("tier", "FAST", "--platform", "nope").returncode, 2)

    def test_role_resolves_to_posture_tier(self):
        r = monday("role", "executor", "--platform", "claude-code")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("tier=", r.stdout)
        self.assertEqual(monday("role", "bogus", "--platform", "claude-code").returncode, 2)


class AgentValidation(TempDirCase):
    def agent(self, **over):
        d = {"name": "monday-x", "role": "executor", "purpose": "does x", "default_tier": "STANDARD", "returns": "report"}
        d.update(over)
        return d

    def test_real_agent_files_are_not_yaml_but_valid_yaml_agent_is_ok(self):
        r = monday("validate", self.write("agent.yaml", self.agent()))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("ok (agent)", r.stdout)

    def test_invalid_agent_rejected(self):
        for name, d in {
            "missing_field": {k: v for k, v in self.agent().items() if k != "purpose"},
            "bad_role": self.agent(role="wizard"),
            "bad_tier": self.agent(default_tier="HUGE"),
            "bad_delegate": self.agent(authority={"delegate": "everywhere"}),
        }.items():
            with self.subTest(name):
                r = monday("validate", self.write(f"{name}.yaml", d))
                self.assertEqual(r.returncode, 1, r.stdout)


class ReportValidation(TempDirCase):
    def check(self, d, *extra):
        return monday("validate", self.write("r.yaml", d), *extra)

    def test_valid_done_passes(self):
        r = self.check(report())
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("ok (report)", r.stdout)

    def test_done_with_verified_false_rejected(self):
        r = self.check(report(verified=False))
        self.assertEqual(r.returncode, 1)
        self.assertIn("verified: true", r.stdout)

    def test_done_with_not_run_rejected(self):
        res = [{"gate": "G1", "result": "pass", "evidence": "ok"}, {"gate": "G5", "result": "not_run"}]
        r = self.check(report(verification_results=res))
        self.assertEqual(r.returncode, 1)
        self.assertIn("not_run", r.stdout)

    def test_done_with_failed_gate_rejected(self):
        res = [{"gate": "G1", "result": "fail"}]
        self.assertEqual(self.check(report(verification_results=res)).returncode, 1)

    def test_pass_without_evidence_rejected(self):
        res = [{"gate": "G1", "result": "pass"}]
        self.assertEqual(self.check(report(verification_results=res)).returncode, 1)

    def test_done_with_concerns_accepts_not_run(self):
        res = [{"gate": "G1", "result": "pass", "evidence": "ok"}, {"gate": "G5", "result": "not_run"}]
        r = self.check(report(status="DONE_WITH_CONCERNS", verified=False, verification_results=res))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_invalid_status_rejected(self):
        self.assertEqual(self.check(report(status="WIN")).returncode, 1)

    def test_contract_cross_check_missing_gate(self):
        c = self.write("c.yaml", contract())
        res = [{"gate": "G1", "result": "pass", "evidence": "ok"}]
        r = self.check(report(verification_results=res), "--contract", c)
        self.assertEqual(r.returncode, 1)
        self.assertIn("contract gate G5 missing", r.stdout)

    def test_contract_cross_check_ok(self):
        c = self.write("c.yaml", contract())
        self.assertEqual(self.check(report(), "--contract", c).returncode, 0)


def git(cwd, *args):
    r = run(["git", *args], cwd=cwd)
    assert r.returncode == 0, f"git {args}: {r.stderr}"
    return r.stdout


class CheckScopeBase(TempDirCase):
    CONTRACT_REL = ".monday/contracts/T-1.yaml"

    def setUp(self):
        super().setUp()
        self.repo = os.path.join(self.tmp, "repo")
        os.makedirs(self.repo)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        git(self.repo, "config", "commit.gpgsign", "false")
        self.write("src/a.py", "a = 1\n", base=self.repo)
        self.write("src/b.py", "b = 1\n", base=self.repo)
        self.contract_path = self.write(self.CONTRACT_REL, contract(scope={
            "allowed_files": ["src/a.py"], "excluded_areas": ["src/secret/"]}), base=self.repo)

    def commit_all(self, msg="c"):
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", msg)

    def scope(self, *extra):
        return monday("check-scope", self.contract_path, *extra, cwd=self.repo)


class CheckScope(CheckScopeBase):

    def test_untracked_contract_rejected(self):
        git(self.repo, "add", "src")
        git(self.repo, "commit", "-q", "-m", "base")
        r = self.scope()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("CONTRACT NOT TRACKED", r.stdout)

    def test_untracked_contract_allowed_with_flag(self):
        git(self.repo, "add", "src")
        git(self.repo, "commit", "-q", "-m", "base")
        self.write("src/a.py", "a = 2\n", base=self.repo)
        r = self.scope("--allow-untracked-contract")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("not tracked", r.stderr)

    def test_in_scope_change_passes(self):
        self.commit_all()
        self.write("src/a.py", "a = 2\n", base=self.repo)
        r = self.scope()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("G5 scope: pass", r.stdout)

    def test_contract_modification_rejected(self):
        self.commit_all()
        wider = contract(scope={"allowed_files": ["src/a.py", "src/b.py"]})
        self.write(self.CONTRACT_REL, wider, base=self.repo)
        self.write("src/b.py", "b = 2\n", base=self.repo)
        r = self.scope()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("CONTRACT MODIFIED", r.stdout)
        # scope is read from the base revision, so widening does not legalise src/b.py
        self.assertIn("OUT OF SCOPE (not in scope): src/b.py", r.stdout)

    def test_out_of_scope_modified_and_new_files_detected(self):
        self.commit_all()
        self.write("src/b.py", "b = 2\n", base=self.repo)
        self.write("src/new.py", "n = 1\n", base=self.repo)
        r = self.scope()
        self.assertEqual(r.returncode, 1)
        self.assertIn("OUT OF SCOPE (not in scope): src/b.py", r.stdout)
        self.assertIn("OUT OF SCOPE (not in scope): src/new.py", r.stdout)

    def test_excluded_area_detected(self):
        self.commit_all()
        c = contract(scope={"allowed_directories": ["src/"], "excluded_areas": ["src/secret/"]})
        self.write(self.CONTRACT_REL, c, base=self.repo)
        self.commit_all("widen")
        self.write("src/secret/k.py", "k = 1\n", base=self.repo)
        r = self.scope()
        self.assertEqual(r.returncode, 1)
        self.assertIn("OUT OF SCOPE (excluded_area): src/secret/k.py", r.stdout)

    def test_own_report_is_exempt(self):
        self.commit_all()
        self.write(".monday/reports/T-1.yaml", report(), base=self.repo)
        self.write("src/a.py", "a = 3\n", base=self.repo)
        self.assertEqual(self.scope().returncode, 0)

    def test_own_report_is_exempt_legacy_fallback(self):
        self.commit_all()
        self.write(".agentforge/reports/T-1.yaml", report(), base=self.repo)
        self.write("src/a.py", "a = 3\n", base=self.repo)
        self.assertEqual(self.scope().returncode, 0)



    def test_adversarial_scope_traversal_in_contract(self):
        self.write(self.CONTRACT_REL, contract(scope={"allowed_files": ["../outside.py"]}), base=self.repo)
        self.commit_all("contract with traversal")
        r = self.scope()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("SECURITY VIOLATION (scope rule escapes repo)", r.stdout)

    def test_adversarial_scope_absolute_path_in_contract(self):
        for bad in ("/etc/passwd", "C:/windows/win.ini", "C:\\windows\\win.ini", "//server/share/file.py", "\\\\server\\share\\file.py"):
            with self.subTest(bad=bad):
                self.write(self.CONTRACT_REL, contract(scope={"allowed_files": [bad]}), base=self.repo)
                self.commit_all("contract with absolute/UNC path")
                r = self.scope()
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("SECURITY VIOLATION (scope rule escapes repo)", r.stdout)

    def test_adversarial_scope_wildcard_and_internal_traversal(self):
        for bad in ("src/../*", "src/sub/../a.py", "foo\\..\\bar"):
            with self.subTest(bad=bad):
                self.write(self.CONTRACT_REL, contract(scope={"allowed_files": [bad]}), base=self.repo)
                self.commit_all("contract with internal traversal")
                r = self.scope()
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("SECURITY VIOLATION (scope rule escapes repo)", r.stdout)

    def test_legitimate_scope_patterns_accepted(self):
        c_path = self.write("good-contract.yaml", contract(scope={"allowed_files": ["src/a.py", "src/*.py", "tests/**"]}))
        r = monday("validate", c_path)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("ok (task)", r.stdout)

    def test_adversarial_symlink_escape(self):
        outside = os.path.join(self.tmp, "outside.txt")
        with open(outside, "w") as f:
            f.write("sensitive data\n")
        self.contract_path = self.write(self.CONTRACT_REL, contract(scope={"allowed_files": ["src/escape_link.py"]}), base=self.repo)
        self.commit_all("base commit with contract")
        # Executor creates symlink inside repo pointing outside
        link_target = os.path.join(self.repo, "src", "escape_link.py")
        os.symlink(outside, link_target)
        r = self.scope()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("SECURITY VIOLATION (symlink escape outside repo)", r.stdout)
        # Verify accounting: must not report 0 out of scope when there is a security violation
        self.assertNotIn("0 out of scope", r.stdout)
        self.assertIn("1 out of scope", r.stdout)
        self.assertIn("OUT OF SCOPE (security_violation): src/escape_link.py", r.stdout)

    def test_task_validation_rejects_traversal_scope(self):
        for bad in ("../secret.txt", "src/../*", "C:/foo", "//server/share"):
            with self.subTest(bad=bad):
                c_path = self.write(f"bad-contract-{abs(hash(bad))}.yaml", contract(scope={"allowed_files": [bad]}))
                r = monday("validate", c_path)
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("escapes repository (path traversal or absolute path)", r.stdout)

    def test_padded_scope_rule_cannot_hide_escape(self):
        # glob_re strips patterns, so " ../x" acts as "../x": both forms must be validated.
        for bad in (" /etc/passwd", " ../outside.py", "\t..\\x", "src/ .. /x"):
            with self.subTest(bad=bad):
                self.write(self.CONTRACT_REL, contract(scope={"allowed_files": ["src/a.py", bad]}), base=self.repo)
                self.commit_all("padded rule")
                r = self.scope()
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("SECURITY VIOLATION (scope rule escapes repo)", r.stdout)

    def test_malformed_scope_is_config_error_not_crash(self):
        for scope in ({"allowed_files": "src/a.py"}, {"allowed_files": [123]}, {"allowed_files": ["src/a.py", None]}, ["src/a.py"]):
            with self.subTest(scope=scope):
                self.write(self.CONTRACT_REL, contract(scope=scope), base=self.repo)
                self.commit_all("malformed scope")
                r = self.scope()
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertIn("invalid contract scope", r.stderr)
                self.assertNotIn("Traceback", r.stderr)

    def test_symlink_resolving_into_excluded_area_is_violation(self):
        self.write("src/secret/key.txt", "k\n", base=self.repo)
        self.write(self.CONTRACT_REL, contract(scope={
            "allowed_files": ["src/a.py", "src/link.py"], "excluded_areas": ["src/secret/"]}), base=self.repo)
        self.commit_all("base")
        os.symlink("secret/key.txt", os.path.join(self.repo, "src", "link.py"))
        r = self.scope()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("SECURITY VIOLATION (symlink resolves out of scope): src/link.py -> src/secret/key.txt", r.stdout)
        self.assertIn("OUT OF SCOPE (security_violation): src/link.py", r.stdout)
        self.assertIn("1 changed, 1 out of scope", r.stdout)

    def test_symlink_within_scope_is_not_flagged(self):
        self.write(self.CONTRACT_REL, contract(scope={"allowed_files": ["src/a.py", "src/link.py"]}), base=self.repo)
        self.commit_all("base")
        os.symlink("a.py", os.path.join(self.repo, "src", "link.py"))
        r = self.scope()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("1 changed, 0 out of scope", r.stdout)

    def test_directory_symlink_escape_is_violation(self):
        outside = os.path.join(self.tmp, "outside_dir")
        os.makedirs(outside)
        self.write(self.CONTRACT_REL, contract(scope={"allowed_directories": ["src/"]}), base=self.repo)
        self.commit_all("base")
        os.symlink(outside, os.path.join(self.repo, "src", "sub"))
        r = self.scope()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("SECURITY VIOLATION (symlink escape outside repo): src/sub", r.stdout)
        self.assertIn("1 changed, 1 out of scope", r.stdout)

    def test_exempt_report_symlink_escape_is_violation(self):
        outside = os.path.join(self.tmp, "outside_report.yaml")
        with open(outside, "w") as f:
            f.write("x: 1\n")
        self.commit_all("base")
        os.makedirs(os.path.join(self.repo, ".monday", "reports"), exist_ok=True)
        os.symlink(outside, os.path.join(self.repo, ".monday", "reports", "T-1.yaml"))
        r = self.scope()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("SECURITY VIOLATION (symlink escape outside repo): .monday/reports/T-1.yaml", r.stdout)
        self.assertIn("1 out of scope", r.stdout)

    def test_contract_replaced_by_outside_symlink_is_violation(self):
        self.commit_all("base")
        outside = os.path.join(self.tmp, "contract_copy.yaml")
        shutil.copy(self.contract_path, outside)
        os.remove(self.contract_path)
        os.symlink(outside, self.contract_path)
        r = self.scope()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("SECURITY VIOLATION (symlink escape outside repo): " + self.CONTRACT_REL, r.stdout)

    def test_dotdot_prefixed_name_is_not_an_escape(self):
        # "..notes/x.md" is a legitimate in-repo name, not traversal.
        self.write(self.CONTRACT_REL, contract(scope={"allowed_files": ["..notes/x.md"]}), base=self.repo)
        self.commit_all("base")
        self.write("..notes/x.md", "n\n", base=self.repo)
        r = self.scope()
        self.assertEqual(r.returncode, 0, r.stdout)


class InstallScript(TempDirCase):
    def test_agents_dry_run_uses_symlinks(self):
        home = os.path.join(self.tmp, "home")
        os.makedirs(home)
        env = {**os.environ, "HOME": home}
        r = run(["bash", INSTALL, "--agents", "--dry-run"], env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        agent_lines = [l for l in r.stdout.splitlines() if l.startswith("[dry-run] ln -s") and "/agents/" in l]
        names = sorted(f for f in os.listdir(os.path.join(ROOT, "adapters", "claude-code", "agents")) if f.endswith(".md"))
        self.assertTrue(names)
        for n in names:
            with self.subTest(agent=n):
                self.assertTrue(any(l.endswith(os.path.join(home, ".claude", "agents", n)) and f"/{n} " in l for l in agent_lines), r.stdout)
        # dry-run must not touch the filesystem
        self.assertEqual(os.listdir(home), [])

    def test_unknown_flag_is_usage_error(self):
        self.assertEqual(run(["bash", INSTALL, "--bogus"]).returncode, 2)

    def make_home(self):
        home = os.path.join(self.tmp, "home")
        os.makedirs(home)
        return home, {**os.environ, "HOME": home}

    def test_help(self):
        for flag in ("--help", "-h"):
            with self.subTest(flag=flag):
                r = run(["bash", INSTALL, flag])
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn("--uninstall", r.stdout)

    def test_install_then_uninstall_roundtrip_and_idempotent(self):
        home, env = self.make_home()
        skill = os.path.join(home, ".claude", "skills", "monday")
        for _ in range(2):  # idempotent
            self.assertEqual(run(["bash", INSTALL, "--claude", "--agents"], env=env).returncode, 0)
        self.assertEqual(os.path.realpath(skill), ROOT)
        agents = os.listdir(os.path.join(home, ".claude", "agents"))
        self.assertTrue(agents)
        for _ in range(2):
            self.assertEqual(run(["bash", INSTALL, "--uninstall", "--claude", "--agents"], env=env).returncode, 0)
        self.assertFalse(os.path.lexists(skill))
        self.assertEqual(os.listdir(os.path.join(home, ".claude", "agents")), [])

    def test_uninstall_preserves_foreign_files(self):
        home, env = self.make_home()
        foreign = os.path.join(home, ".claude", "skills", "monday")
        os.makedirs(foreign)
        other = os.path.join(home, ".claude", "agents", "monday-scout.md")
        os.makedirs(os.path.dirname(other))
        with open(other, "w") as f:
            f.write("mine")
        r = run(["bash", INSTALL, "--uninstall", "--claude", "--agents"], env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isdir(foreign) and not os.path.islink(foreign))
        self.assertTrue(os.path.isfile(other))

    def test_uninstall_dry_run_keeps_links(self):
        home, env = self.make_home()
        skill = os.path.join(home, ".claude", "skills", "monday")
        run(["bash", INSTALL, "--claude"], env=env)
        r = run(["bash", INSTALL, "--uninstall", "--dry-run", "--claude"], env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("[dry-run] rm", r.stdout)
        self.assertTrue(os.path.islink(skill))



    def test_cli_mutually_exclusive_flags(self):
        for combo in (["--check", "--purge-legacy"], ["--check", "--uninstall"], ["--purge-legacy", "--uninstall"]):
            with self.subTest(combo=combo):
                r = run(["bash", INSTALL, *combo])
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertIn("mutuamente excluyentes", r.stderr)

    def test_purge_legacy_dry_run_does_not_modify_anything(self):
        home, env = self.make_home()
        run(["bash", INSTALL, "--claude", "--agents"], env=env)
        leg = os.path.join(home, ".claude", "agents", "worker.md")
        with open(leg, "w") as f:
            f.write("legacy worker content\n")
        r = run(["bash", INSTALL, "--purge-legacy", "--dry-run"], env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("[dry-run] Simulación completada", r.stdout)
        # Original file remains untouched
        self.assertTrue(os.path.exists(leg))
        # No backup directory created
        self.assertFalse(os.path.exists(os.path.join(home, ".claude", "backups")))

    def test_purge_legacy_rejects_symlinks(self):
        home, env = self.make_home()
        run(["bash", INSTALL, "--claude", "--agents"], env=env)
        target = os.path.join(self.tmp, "external_worker.txt")
        with open(target, "w") as f:
            f.write("external content\n")
        leg = os.path.join(home, ".claude", "agents", "worker.md")
        os.symlink(target, leg)
        r = run(["bash", INSTALL, "--purge-legacy"], env=env)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("es un enlace simbólico", r.stderr)
        # Symlink and external target are preserved untouched
        self.assertTrue(os.path.islink(leg))
        self.assertTrue(os.path.exists(target))

    def test_install_check_and_purge_legacy(self):
        home, env = self.make_home()
        # 1. Check in empty home fails (missing links)
        r_check1 = run(["bash", INSTALL, "--check"], env=env)
        self.assertEqual(r_check1.returncode, 1)
        self.assertIn("no está enlazado", r_check1.stdout)

        # 2. Install all
        r_inst = run(["bash", INSTALL, "--claude", "--antigravity", "--agents"], env=env)
        self.assertEqual(r_inst.returncode, 0, r_inst.stderr)

        # 3. Add legacy files
        leg = os.path.join(home, ".claude", "agents", "worker.md")
        with open(leg, "w") as f:
            f.write("legacy worker content\n")
        r_check2 = run(["bash", INSTALL, "--check"], env=env)
        self.assertEqual(r_check2.returncode, 1)
        self.assertIn("agente legacy detectado", r_check2.stdout)

        # 4. Purge legacy with cmp verification
        r_purge = run(["bash", INSTALL, "--purge-legacy"], env=env)
        self.assertEqual(r_purge.returncode, 0, r_purge.stderr)
        self.assertFalse(os.path.exists(leg))
        self.assertIn("integridad verificada con cmp", r_purge.stdout)

        # Check backup exists and content matches bit-for-bit
        backups = [d for d in os.listdir(os.path.join(home, ".claude", "backups")) if d.startswith("legacy-agents-")]
        self.assertTrue(backups)
        backup_file = os.path.join(home, ".claude", "backups", backups[0], "worker.md")
        self.assertTrue(os.path.exists(backup_file))
        with open(backup_file) as f:
            self.assertEqual(f.read(), "legacy worker content\n")

        # 5. Check is now clean and healthy
        r_check3 = run(["bash", INSTALL, "--check"], env=env)
        self.assertEqual(r_check3.returncode, 0, r_check3.stdout)
        self.assertIn("COMPLETO Y SALUDABLE", r_check3.stdout)


class InitCommand(TempDirCase):
    def test_init_creates_full_structure(self):
        r = monday("init", self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        base = os.path.join(self.tmp, ".monday")
        self.assertTrue(os.path.isfile(os.path.join(base, "CONTEXT.md")))
        self.assertTrue(os.path.isdir(os.path.join(base, "contracts")))
        self.assertTrue(os.path.isdir(os.path.join(base, "reports")))

    def test_init_is_idempotent_and_keeps_context(self):
        monday("init", self.tmp)
        ctx = os.path.join(self.tmp, ".monday", "CONTEXT.md")
        with open(ctx, "w") as f:
            f.write("custom")
        self.assertEqual(monday("init", self.tmp).returncode, 0)
        with open(ctx) as f:
            self.assertEqual(f.read(), "custom")

    def test_init_creates_monday_and_notices_legacy_agentforge_dir(self):
        # If .agentforge exists, init creates canonical .monday/ and notices user
        legacy_base = os.path.join(self.tmp, ".agentforge")
        os.makedirs(legacy_base, exist_ok=True)
        r = monday("init", self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        monday_base = os.path.join(self.tmp, ".monday")
        self.assertTrue(os.path.isfile(os.path.join(monday_base, "CONTEXT.md")))
        self.assertFalse(os.path.exists(os.path.join(legacy_base, "CONTEXT.md")))
        self.assertIn("notice: legacy directory '.agentforge' exists", r.stderr)

    def test_init_precedence_when_both_dirs_exist(self):
        # When both .monday and .agentforge exist, .monday takes strict precedence
        monday_base = os.path.join(self.tmp, ".monday")
        legacy_base = os.path.join(self.tmp, ".agentforge")
        os.makedirs(monday_base, exist_ok=True)
        os.makedirs(legacy_base, exist_ok=True)
        r = monday("init", self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(monday_base, "CONTEXT.md")))
        self.assertFalse(os.path.exists(os.path.join(legacy_base, "CONTEXT.md")))
        self.assertNotIn("notice: legacy directory '.agentforge' exists", r.stderr)

    def test_init_rejects_file_target(self):
        file_target = os.path.join(self.tmp, ".monday")
        with open(file_target, "w") as f:
            f.write("not a directory")
        r = monday("init", self.tmp)
        self.assertEqual(r.returncode, 2)
        self.assertIn("exists and is not a directory", r.stderr)

    def test_init_migrate_legacy_copies_and_preserves_original(self):
        legacy_base = os.path.join(self.tmp, ".agentforge")
        os.makedirs(os.path.join(legacy_base, "contracts"), exist_ok=True)
        with open(os.path.join(legacy_base, "CONTEXT.md"), "w") as f:
            f.write("legacy context")
        with open(os.path.join(legacy_base, "contracts", "T-1.yaml"), "w") as f:
            f.write("task: dummy")
        r = monday("init", "--migrate-legacy", self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("migrated", r.stdout)
        # Verify target .monday has the copied files
        monday_base = os.path.join(self.tmp, ".monday")
        with open(os.path.join(monday_base, "CONTEXT.md")) as f:
            self.assertEqual(f.read(), "legacy context")
        self.assertTrue(os.path.isfile(os.path.join(monday_base, "contracts", "T-1.yaml")))
        # Verify legacy .agentforge is fully preserved (non-destructive)
        self.assertTrue(os.path.isfile(os.path.join(legacy_base, "CONTEXT.md")))
        self.assertTrue(os.path.isfile(os.path.join(legacy_base, "contracts", "T-1.yaml")))

    def test_init_migrate_legacy_aborts_if_target_exists(self):
        monday_base = os.path.join(self.tmp, ".monday")
        legacy_base = os.path.join(self.tmp, ".agentforge")
        os.makedirs(monday_base, exist_ok=True)
        os.makedirs(legacy_base, exist_ok=True)
        r = monday("init", "--migrate-legacy", self.tmp)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("already exists", r.stderr)

    def test_init_migrate_legacy_rejects_escaping_symlink(self):
        legacy_base = os.path.join(self.tmp, ".agentforge")
        os.makedirs(os.path.join(legacy_base, "contracts"), exist_ok=True)
        outside_file = os.path.join(self.tmp, "secret.txt")
        with open(outside_file, "w") as f:
            f.write("secret data")
        os.symlink(outside_file, os.path.join(legacy_base, "contracts", "leak.yaml"))
        r = monday("init", "--migrate-legacy", self.tmp)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unsafe symlink escapes legacy directory", r.stderr)

    def test_init_migrate_legacy_preserves_internal_symlinks(self):
        legacy_base = os.path.join(self.tmp, ".agentforge")
        os.makedirs(os.path.join(legacy_base, "contracts"), exist_ok=True)
        with open(os.path.join(legacy_base, "CONTEXT.md"), "w") as f:
            f.write("context text")
        os.symlink("../CONTEXT.md", os.path.join(legacy_base, "contracts", "ref.md"))
        r = monday("init", "--migrate-legacy", self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        target_link = os.path.join(self.tmp, ".monday", "contracts", "ref.md")
        self.assertTrue(os.path.islink(target_link), "Symlink was dereferenced instead of preserved!")

    def test_init_migrate_legacy_rejects_root_directory_symlink_escaping(self):
        outside_dir = os.path.join(self.tmp, "outside_legacy")
        os.makedirs(outside_dir, exist_ok=True)
        proj_dir = os.path.join(self.tmp, "proj")
        os.makedirs(proj_dir, exist_ok=True)
        os.symlink(outside_dir, os.path.join(proj_dir, ".agentforge"))
        r = monday("init", "--migrate-legacy", proj_dir)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("legacy directory itself is an external symlink", r.stderr)


class ConfigIntegrity(unittest.TestCase):
    def test_no_legacy_existing_in_profiles(self):
        prof_path = os.path.join(ROOT, "routing", "profiles.yaml")
        with open(prof_path) as f:
            data = yaml.safe_load(f)
        agents = data.get("platforms", {}).get("claude-code", {}).get("agents", {})
        for name, spec in agents.items():
            self.assertNotIn("existing", spec, f"agent '{name}' still has legacy 'existing' key")

    def test_no_legacy_references_in_claude_adapter_docs(self):
        doc_path = os.path.join(ROOT, "adapters", "claude-code", "README.md")
        with open(doc_path) as f:
            content = f.read()
        self.assertNotIn("(o scout)", content)
        self.assertNotIn("(o worker)", content)
        self.assertNotIn("(o reviewer)", content)
        self.assertNotIn("profiles.yaml los reconoce como equivalentes", content)

    def test_no_legacy_agent_names_as_install_alternatives(self):
        with open(os.path.join(ROOT, "docs", "usage.md")) as f:
            self.assertNotIn("af-scout, af-worker, af-reviewer", f.read())
        with open(os.path.join(ROOT, "contracts", "templates", "report.yaml")) as f:
            self.assertNotIn('"af-scout FAST', f.read())


class ForwarderCompatibility(unittest.TestCase):
    def test_af_script_forwards_to_monday(self):
        r = run([sys.executable, AF, "tier", "STANDARD", "--platform", "claude-code"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("model=", r.stdout)
        self.assertIn("effort=", r.stdout)
        self.assertIn("warning: scripts/af.py is deprecated", r.stderr)

    def test_af_script_propagates_nonzero_exit_code(self):
        r = run([sys.executable, AF, "tier", "INVALID_TIER", "--platform", "claude-code"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("warning: scripts/af.py is deprecated", r.stderr)

    def test_af_script_works_through_symlink(self):
        tmp_dir = tempfile.mkdtemp(prefix="monday-shim-test-")
        try:
            link_path = os.path.join(tmp_dir, "af_link.py")
            os.symlink(AF, link_path)
            r = run([sys.executable, link_path, "tier", "FAST", "--platform", "claude-code"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("model=", r.stdout)
            self.assertIn("warning: scripts/af.py is deprecated", r.stderr)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def load_monday():
    import importlib.util
    spec = importlib.util.spec_from_file_location("monday_module", MONDAY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod



class PathMatrix(unittest.TestCase):
    """Adversarial matrix for is_safe_rel_path (POSIX, Windows, UNC, traversal, padding)."""
    UNSAFE = [
        "/etc/passwd", "/", "\\", "C:/windows/win.ini", "C:\\windows\\win.ini", "c:x", "C:",
        "//server/share/f", "\\\\server\\share\\f", "\\\\?\\C:\\x",
        "..", "../", "..\\", "../x", "..\\x", "src/..", "src/../*", "src\\..\\..\\x", "src/./../x",
        "a/b/../../..", "src//..//x", " /etc/passwd", " ../x", "\t..\\x", "../x ", "src/ .. /x", "", "   ",
    ]
    SAFE = ["src/a.py", "src/*", "src/**", "src/", "**", "./src/a.py", "docs/v1.2/file..txt", "...", "..notes/x", "src/a b.py"]

    def test_unsafe_rejected(self):
        mod = load_monday()
        for p in self.UNSAFE:
            with self.subTest(p=p):
                self.assertFalse(mod.is_safe_rel_path(p))

    def test_safe_accepted(self):
        mod = load_monday()
        for p in self.SAFE:
            with self.subTest(p=p):
                self.assertTrue(mod.is_safe_rel_path(p))

    def test_non_strings_rejected(self):
        mod = load_monday()
        for p in (None, 1, ["src"], {"a": 1}):
            with self.subTest(p=p):
                self.assertFalse(mod.is_safe_rel_path(p))


class ValidateMalformedScope(TempDirCase):
    def test_malformed_scope_reported_without_traceback(self):
        cases = {
            "str": {"allowed_files": "src/a.py"},
            "int": {"allowed_files": [123]},
            "null": {"allowed_files": ["src/a.py", None]},
            "list": ["src/a.py"],
            "excl": {"allowed_files": ["src/a.py"], "excluded_areas": "src/secret/"},
        }
        for name, scope in cases.items():
            with self.subTest(case=name):
                r = monday("validate", self.write(f"c-{name}.yaml", contract(scope=scope)))
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn("scope", r.stdout)
                self.assertNotIn("Traceback", r.stderr)

    def test_padded_paths_rejected_by_validate(self):
        for i, bad in enumerate((" /etc/passwd", " ../outside.py", "\t..\\x")):
            with self.subTest(bad=bad):
                r = monday("validate", self.write(f"c-{i}.yaml", contract(scope={"allowed_files": [bad]})))
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("escapes repository", r.stdout)


def tree_snapshot(root):
    """Every entry under root: type, link target, mode and content hash (not just a count)."""
    import hashlib
    snap = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for n in dirnames + filenames:
            p = os.path.join(dirpath, n)
            rel = os.path.relpath(p, root)
            st = os.lstat(p)
            if os.path.islink(p):
                snap[rel] = ("l", os.readlink(p))
            elif os.path.isdir(p):
                snap[rel] = ("d", st.st_mode)
            else:
                with open(p, "rb") as f:
                    snap[rel] = ("f", st.st_mode, hashlib.sha256(f.read()).hexdigest())
    return snap


LEGACY = ("reviewer.md", "scout.md", "worker.md")


class PurgeLegacySafety(TempDirCase):
    """install.sh --check / --purge-legacy against an isolated HOME (never the real one)."""

    def setUp(self):
        super().setUp()
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)
        self.env = {**os.environ, "HOME": self.home}
        self.install = INSTALL
        self.agents = os.path.join(self.home, ".claude", "agents")
        self.backups = os.path.join(self.home, ".claude", "backups")

    def sh(self, *args, env=None):
        return run(["bash", self.install, *args], env=env or self.env)

    def installed(self):
        r = self.sh("--claude", "--antigravity", "--agents")
        self.assertEqual(r.returncode, 0, r.stderr)

    def legacy(self, names=LEGACY):
        for n in names:
            with open(os.path.join(self.agents, n), "w") as f:
                f.write(f"legacy {n}\n")

    def assert_legacy_intact(self, names=LEGACY):
        for n in names:
            p = os.path.join(self.agents, n)
            self.assertTrue(os.path.isfile(p) and not os.path.islink(p), p)
            with open(p) as f:
                self.assertEqual(f.read(), f"legacy {n}\n")

    def shim(self, name, body):
        bindir = os.path.join(self.tmp, "bin")
        os.makedirs(bindir, exist_ok=True)
        path = os.path.join(bindir, name)
        with open(path, "w") as f:
            f.write("#!/usr/bin/env bash\n" + body + "\n")
        os.chmod(path, 0o755)
        return {**self.env, "PATH": bindir + os.pathsep + os.environ["PATH"]}

    def sandbox(self):
        """Private copy of install.sh + agents, so an official agent can be broken without touching the repo."""
        src = os.path.join(self.tmp, "src")
        shutil.copytree(os.path.join(ROOT, "adapters", "claude-code", "agents"), os.path.join(src, "adapters", "claude-code", "agents"))
        shutil.copy(INSTALL, os.path.join(src, "install.sh"))
        self.install = os.path.join(src, "install.sh")
        return src

    def test_platform_flags_rejected_with_check_or_purge(self):
        for combo in (["--check", "--claude"], ["--check", "--agents"], ["--purge-legacy", "--antigravity"], ["--purge-legacy", "--agents"]):
            with self.subTest(combo=combo):
                r = self.sh(*combo)
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertEqual(os.listdir(self.home), [])

    def test_check_is_read_only(self):
        self.installed()
        self.legacy(["worker.md"])
        os.makedirs(os.path.join(self.backups, "legacy-agents-old"))
        with open(os.path.join(self.backups, "legacy-agents-old", "scout.md"), "w") as f:
            f.write("old\n")
        before = tree_snapshot(self.home)
        for extra in ([], ["--dry-run"]):
            r = self.sh("--check", *extra)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("agente legacy detectado", r.stdout)
        self.assertEqual(tree_snapshot(self.home), before)

    def test_purge_dry_run_is_read_only(self):
        self.installed()
        self.legacy()
        before = tree_snapshot(self.home)
        r = self.sh("--purge-legacy", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.count("[dry-run] purgaría"), 3)
        self.assertEqual(tree_snapshot(self.home), before)

    def test_purge_all_three_with_verified_backup(self):
        self.installed()
        self.legacy()
        r = self.sh("--purge-legacy")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("completada con éxito", r.stdout)
        dirs = os.listdir(self.backups)
        self.assertEqual(len(dirs), 1)
        for n in LEGACY:
            self.assertFalse(os.path.lexists(os.path.join(self.agents, n)))
            with open(os.path.join(self.backups, dirs[0], n)) as f:
                self.assertEqual(f.read(), f"legacy {n}\n")
        for n in os.listdir(os.path.join(ROOT, "adapters", "claude-code", "agents")):
            self.assertTrue(os.path.islink(os.path.join(self.agents, n)))
        self.assertEqual(self.sh("--check").returncode, 0)

    def test_precondition_failure_purges_nothing(self):
        # reviewer.md is valid, scout.md is a symlink: the old loop deleted reviewer.md before failing.
        self.installed()
        self.legacy(["reviewer.md", "worker.md"])
        ext = os.path.join(self.tmp, "external.txt")
        with open(ext, "w") as f:
            f.write("external\n")
        os.symlink(ext, os.path.join(self.agents, "scout.md"))
        r = self.sh("--purge-legacy")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("es un enlace simbólico", r.stderr)
        self.assert_legacy_intact(["reviewer.md", "worker.md"])
        self.assertTrue(os.path.islink(os.path.join(self.agents, "scout.md")))
        self.assertFalse(os.path.exists(self.backups))
        self.assertNotIn("éxito", r.stdout)

    def test_non_regular_legacy_purges_nothing(self):
        self.installed()
        self.legacy(["reviewer.md", "scout.md"])
        os.makedirs(os.path.join(self.agents, "worker.md"))
        r = self.sh("--purge-legacy")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("no es un archivo regular", r.stderr)
        self.assert_legacy_intact(["reviewer.md", "scout.md"])
        self.assertFalse(os.path.exists(self.backups))

    def test_copy_failure_keeps_originals(self):
        self.installed()
        self.legacy()
        env = self.shim("cp", "exit 1")
        r = self.sh("--purge-legacy", env=env)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("No se ha borrado ningún original", r.stderr)
        self.assert_legacy_intact()
        self.assertNotIn("éxito", r.stdout)

    def test_verification_failure_keeps_originals(self):
        self.installed()
        self.legacy()
        # cp "succeeds" but writes different bytes; the real cmp must catch it.
        env = self.shim("cp", 'for a; do dst="$a"; done; printf corrupt > "$dst"')
        r = self.sh("--purge-legacy", env=env)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("No se ha borrado ningún original", r.stderr)
        self.assert_legacy_intact()

    def test_backup_collision_preserves_existing_backup(self):
        self.installed()
        self.legacy()
        env = self.shim("date", "echo 20990101-000000")
        existing = os.path.join(self.backups, "legacy-agents-20990101-000000")
        os.makedirs(existing)
        with open(os.path.join(existing, "worker.md"), "w") as f:
            f.write("previous backup\n")
        before = tree_snapshot(self.backups)
        r = self.sh("--purge-legacy", env=env)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("ya existe", r.stderr)
        self.assertEqual(tree_snapshot(self.backups), before)
        self.assert_legacy_intact()

    @unittest.skipIf(os.geteuid() == 0, "root ignores directory permissions")
    def test_unwritable_backup_dir_keeps_originals(self):
        self.installed()
        self.legacy()
        os.makedirs(self.backups)
        os.chmod(self.backups, 0o500)
        self.addCleanup(os.chmod, self.backups, 0o700)
        r = self.sh("--purge-legacy")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("No se ha modificado nada", r.stderr)
        self.assert_legacy_intact()

    def test_removal_failure_midway_reports_incomplete(self):
        self.installed()
        self.legacy()
        env = self.shim("rm", 'case "$*" in *scout.md*) exit 1 ;; esac; exec /bin/rm "$@"')
        r = self.sh("--purge-legacy", env=env)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("INCOMPLETA", r.stderr)
        self.assertNotIn("éxito", r.stdout)
        self.assert_legacy_intact(["scout.md"])
        self.assertFalse(os.path.lexists(os.path.join(self.agents, "reviewer.md")))
        backup = os.path.join(self.backups, os.listdir(self.backups)[0])
        for n in LEGACY:  # every original, removed or not, has a verified copy
            with open(os.path.join(backup, n)) as f:
                self.assertEqual(f.read(), f"legacy {n}\n")

    def test_rm_success_without_removal_reports_incomplete(self):
        # e.g. an interactive rm on a read-only file answered "n" exits 0 but keeps the file.
        self.installed()
        self.legacy()
        env = self.shim("rm", "exit 0")
        r = self.sh("--purge-legacy", env=env)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("INCOMPLETA", r.stderr)
        self.assertNotIn("purgado", r.stdout)
        self.assertNotIn("éxito", r.stdout)
        self.assert_legacy_intact()

    def test_read_only_legacy_is_purged_without_prompt(self):
        self.installed()
        self.legacy()
        os.chmod(os.path.join(self.agents, "scout.md"), 0o444)
        # stdin on a pty pre-answered "n": an rm without -f would ask and keep the file.
        master, slave = os.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        os.write(master, b"n\n")
        r = subprocess.run(["bash", self.install, "--purge-legacy"], stdin=slave, capture_output=True,
                           text=True, env=self.env, timeout=30)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for n in LEGACY:
            self.assertFalse(os.path.lexists(os.path.join(self.agents, n)))

    @unittest.skipIf(os.geteuid() == 0, "root ignores file permissions")
    def test_unreadable_legacy_purges_nothing(self):
        self.installed()
        self.legacy()
        p = os.path.join(self.agents, "scout.md")
        os.chmod(p, 0o000)
        self.addCleanup(os.chmod, p, 0o644)
        r = self.sh("--purge-legacy")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("no es legible", r.stderr)
        self.assertFalse(os.path.exists(self.backups))
        self.assert_legacy_intact(["reviewer.md", "worker.md"])

    def test_missing_official_agent_blocks_purge(self):
        self.installed()
        self.legacy()
        os.remove(os.path.join(self.agents, "monday-reviewer.md"))
        r = self.sh("--purge-legacy")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("monday-reviewer.md", r.stderr)
        self.assert_legacy_intact()
        self.assertFalse(os.path.exists(self.backups))

    def test_unhealthy_official_agent_blocks_purge_and_fails_check(self):
        src = self.sandbox()
        self.installed()
        self.legacy()
        target = os.path.join(src, "adapters", "claude-code", "agents", "monday-worker.md")
        for broken in ("", "---\nname: worker\n---\nbody\n", "no frontmatter\n"):
            with self.subTest(broken=broken):
                with open(target, "w") as f:
                    f.write(broken)
                c = self.sh("--check")
                self.assertEqual(c.returncode, 1, c.stdout)
                self.assertIn("monday-worker.md", c.stdout)
                r = self.sh("--purge-legacy")
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("no saludable", r.stderr)
                self.assert_legacy_intact()
                self.assertFalse(os.path.exists(self.backups))

    def test_symlinked_agents_dir_refused(self):
        self.installed()
        real = os.path.join(self.tmp, "dotfiles-agents")
        os.rename(self.agents, real)
        os.symlink(real, self.agents)
        self.legacy()
        r = self.sh("--purge-legacy")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("no es un directorio real", r.stderr)
        self.assert_legacy_intact()


class UnknownKeysAndSchemaValidation(TempDirCase):
    def test_unknown_task_key_rejected(self):
        d = contract()
        d["unrecognized_field"] = "bad"
        r = monday("validate", self.write("t.yaml", d))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("unknown key in task: 'unrecognized_field'", r.stdout)

    def test_scope_typo_exclude_areas_rejected_with_suggestion(self):
        d = contract()
        d["scope"] = {"allowed_files": ["src/app.py"], "exclude_areas": ["src/secret"]}
        r = monday("validate", self.write("t.yaml", d))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("unknown key in scope: 'exclude_areas' (did you mean 'excluded_areas'?)", r.stdout)

    def test_scope_typo_allowed_file_rejected_with_suggestion(self):
        d = contract()
        d["scope"] = {"allowed_file": ["src/app.py"]}
        r = monday("validate", self.write("t.yaml", d))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("unknown key in scope: 'allowed_file' (did you mean 'allowed_files'?)", r.stdout)

    def test_permissions_unknown_key_rejected(self):
        d = contract()
        d["permissions"] = {"commands": {"allow": ["ls"]}, "unknown_perm": True}
        r = monday("validate", self.write("t.yaml", d))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("unknown key in permissions: 'unknown_perm'", r.stdout)

    def test_permissions_commands_typo_rejected(self):
        d = contract()
        d["permissions"] = {"commands": {"command": ["ls"]}}
        r = monday("validate", self.write("t.yaml", d))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("unknown key in permissions.commands: 'command' (did you mean 'commands'?)", r.stdout)

    def test_routing_unknown_key_rejected(self):
        d = contract()
        d["routing"] = {"preferred_tier": "STANDARD", "auto_pilot": True}
        r = monday("validate", self.write("t.yaml", d))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("unknown key in routing: 'auto_pilot'", r.stdout)

    def test_report_unknown_key_rejected(self):
        d = report()
        d["extra_report_field"] = "test"
        r = monday("validate", self.write("r.yaml", d))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("unknown key in report: 'extra_report_field'", r.stdout)

    def test_agent_unknown_key_rejected(self):
        d = {
            "name": "scout",
            "role": "specialist",
            "purpose": "find files",
            "default_tier": "FAST",
            "returns": "files list",
            "magic_power": "levitate"
        }
        r = monday("validate", self.write("a.yaml", d))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("unknown key in agent: 'magic_power'", r.stdout)

    def test_explicit_schema_1_passes(self):
        d_task = contract()
        d_task["schema"] = 1
        r_task = monday("validate", self.write("t1.yaml", d_task))
        self.assertEqual(r_task.returncode, 0, r_task.stdout)

        d_report = report()
        d_report["schema"] = 1
        d_report["verification_results"] = [
            {"gate": "G1", "result": "pass", "evidence": "pytest passed 42 tests in 0.5s"},
            {"gate": "G5", "result": "pass", "evidence": "check-scope passed with 0 out of scope"}
        ]
        r_report = monday("validate", self.write("r1.yaml", d_report))
        self.assertEqual(r_report.returncode, 0, r_report.stdout)

    def test_unsupported_schema_rejected(self):
        d = contract()
        d["schema"] = 99
        r = monday("validate", self.write("t_bad.yaml", d))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("unsupported schema version '99'", r.stdout)


class EvidenceAndContractCommands(TempDirCase):
    def test_schema_1_trivial_evidence_rejected(self):
        for trivial in ("ok", "pass", "done", "true", "yes", "passed"):
            with self.subTest(trivial=trivial):
                d = report()
                d["schema"] = 1
                d["verification_results"] = [
                    {"gate": "G1", "result": "pass", "evidence": trivial},
                    {"gate": "G5", "result": "pass", "evidence": "substantive evidence text"}
                ]
                r = monday("validate", self.write("r_triv.yaml", d))
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("pass with trivial placeholder evidence", r.stdout)

    def test_schema_1_contract_requires_tests_executed(self):
        c = self.write("c.yaml", contract(verification={"commands": ["pytest tests/"], "gates": ["G1"]}))
        d = report()
        d["schema"] = 1
        d["verification_results"] = [{"gate": "G1", "result": "pass", "evidence": "pytest tests/ exited 0"}]
        d["tests_executed"] = []
        r = monday("validate", self.write("r.yaml", d), "--contract", c)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("contract requires verification.commands but report has empty 'tests_executed'", r.stdout)

        d["tests_executed"] = [{"command": "pytest tests/", "result": "42 passed"}]
        r2 = monday("validate", self.write("r_fixed.yaml", d), "--contract", c)
        self.assertEqual(r2.returncode, 0, r2.stdout)


    def test_schema_1_tests_executed_substantive_validation(self):
        d = report()
        d["schema"] = 1
        d["verification_results"] = [
            {"gate": "G1", "result": "pass", "evidence": "pytest passed 42 tests in 0.5s"},
            {"gate": "G5", "result": "pass", "evidence": "check-scope passed with 0 out of scope"}
        ]

        # 1. Empty command
        d["tests_executed"] = [{"command": "", "result": "42 passed"}]
        r1 = monday("validate", self.write("r_bad_cmd.yaml", d))
        self.assertEqual(r1.returncode, 1, r1.stdout)
        self.assertIn("tests_executed[0]: 'command' is empty or placeholder", r1.stdout)

        # 2. Trivial placeholder result
        d["tests_executed"] = [{"command": "pytest", "result": "ok"}]
        r2 = monday("validate", self.write("r_bad_res.yaml", d))
        self.assertEqual(r2.returncode, 1, r2.stdout)
        self.assertIn("tests_executed[0]: 'result' is empty or trivial placeholder", r2.stdout)

        # 3. Non-mapping entry
        d["tests_executed"] = ["just a string"]
        r3 = monday("validate", self.write("r_bad_map.yaml", d))
        self.assertEqual(r3.returncode, 1, r3.stdout)
        self.assertIn("tests_executed[0] must be a mapping", r3.stdout)

        # 4. Valid substantive entry
        d["tests_executed"] = [{"command": "python3 -m unittest", "result": "Ran 124 tests in 18s - OK"}]
        r4 = monday("validate", self.write("r_valid.yaml", d))
        self.assertEqual(r4.returncode, 0, r4.stdout)

    def test_strict_schema_and_deprecation_warning(self):
        # Unversioned contract passes normally with stderr warning
        d_legacy = contract()
        r_legacy = monday("validate", self.write("legacy_t.yaml", d_legacy))
        self.assertEqual(r_legacy.returncode, 0, r_legacy.stdout)
        self.assertIn("warning: missing 'schema: 1'", r_legacy.stderr)

        # Unversioned contract fails with --strict-schema
        r_strict_fail = monday("validate", self.write("legacy_t.yaml", d_legacy), "--strict-schema")
        self.assertEqual(r_strict_fail.returncode, 1, r_strict_fail.stdout)
        self.assertIn("missing 'schema: 1' (required under --strict-schema)", r_strict_fail.stdout)

        # Versioned contract passes with --strict-schema without warning
        d_v1 = contract(schema=1)
        r_strict_pass = monday("validate", self.write("v1_t.yaml", d_v1), "--strict-schema")
        self.assertEqual(r_strict_pass.returncode, 0, r_strict_pass.stdout)
        self.assertNotIn("warning: missing 'schema: 1'", r_strict_pass.stderr)


class CheckScopeIncludeIgnored(CheckScopeBase):
    def test_include_ignored_catches_ignored_file(self):
        self.commit_all("base")
        self.write(".gitignore", "ignored_folder/\n", base=self.repo)
        self.commit_all("add gitignore")

        leak_path = os.path.join(self.repo, "ignored_folder", "leak.py")
        os.makedirs(os.path.dirname(leak_path), exist_ok=True)
        with open(leak_path, "w") as f:
            f.write("# untracked ignored file\n")

        r1 = self.scope()
        self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)

        r2 = self.scope("--include-ignored")
        self.assertEqual(r2.returncode, 1, r2.stdout + r2.stderr)
        self.assertIn("OUT OF SCOPE", r2.stdout)
        self.assertIn("ignored_folder/leak.py", r2.stdout)

    def test_schema_1_catches_ignored_file_automatically(self):
        # Write schema: 1 contract
        c_v1 = contract(schema=1, scope={"allowed_files": ["src/a.py"], "excluded_areas": ["src/secret/"]})
        self.write(self.CONTRACT_REL, c_v1, base=self.repo)
        self.commit_all("use schema 1")

        self.write(".gitignore", "ignored_dir/\n", base=self.repo)
        self.commit_all("add gitignore")

        leak = os.path.join(self.repo, "ignored_dir", "leak.py")
        os.makedirs(os.path.dirname(leak), exist_ok=True)
        with open(leak, "w") as f:
            f.write("secret = 123\n")

        # Without --include-ignored: schema: 1 automatically flags it!
        r_auto = self.scope()
        self.assertEqual(r_auto.returncode, 1, r_auto.stdout + r_auto.stderr)
        self.assertIn("OUT OF SCOPE", r_auto.stdout)
        self.assertIn("ignored_dir/leak.py", r_auto.stdout)

        # With --no-include-ignored: opts out of automatic checking
        r_optout = self.scope("--no-include-ignored")
        self.assertEqual(r_optout.returncode, 0, r_optout.stdout + r_optout.stderr)

    def test_ignored_file_in_excluded_areas_caught_even_in_legacy_contract(self):
        # In legacy contract without schema: 1, creating a file inside excluded_areas (even if gitignored) is caught!
        self.commit_all("base")
        self.write(".gitignore", "src/secret/\n", base=self.repo)
        self.commit_all("add gitignore for secret")

        secret_file = os.path.join(self.repo, "src", "secret", "creds.env")
        os.makedirs(os.path.dirname(secret_file), exist_ok=True)
        with open(secret_file, "w") as f:
            f.write("KEY=foo\n")

        # Even without --include-ignored and on legacy contract:
        r = self.scope()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("OUT OF SCOPE (excluded_area): src/secret/creds.env", r.stdout)

    def test_transient_bytecache_is_not_flagged(self):
        c_v1 = contract(schema=1, scope={"allowed_files": ["src/a.py"], "excluded_areas": ["src/secret/"]})
        self.write(self.CONTRACT_REL, c_v1, base=self.repo)
        self.commit_all("schema 1")

        self.write(".gitignore", "**/__pycache__/\n*.pyc\n", base=self.repo)
        self.commit_all("add gitignore pycache")

        cache_file = os.path.join(self.repo, "src", "__pycache__", "a.cpython-312.pyc")
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, "wb") as f:
            f.write(b"compiled")

        r = self.scope()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class CapabilityCommands(TempDirCase):
    def test_cap_status_all(self):
        r = monday("cap", "status", cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("capability=git", r.stdout)
        self.assertIn("capability=python-ast", r.stdout)
        self.assertIn("state=Preparada", r.stdout)

    def test_cap_status_four_states_and_contract(self):
        # Create a custom catalog in temporary directory
        custom_cat = {
            "capabilities": {
                "installed_tool": {
                    "tier": "FAST", "category": "core", "check_cmd": "python3 -c 'import sys; sys.exit(0)'"
                },
                "uninstalled_tool": {
                    "tier": "DEEP", "category": "special", "check_cmd": "false"
                }
            }
        }
        repo = os.path.join(self.tmp, "custom_repo")
        os.makedirs(os.path.join(repo, "capabilities"), exist_ok=True)
        with open(os.path.join(repo, "capabilities", "catalog.yaml"), "w") as f:
            yaml.safe_dump(custom_cat, f)

        cat_file = os.path.join(repo, "capabilities", "catalog.yaml")

        # 1. Sin filtro de autorizacion: installed -> Preparada; uninstalled -> Disponible
        r = monday("cap", "status", "--catalog", cat_file, cwd=repo)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("capability=installed_tool state=Preparada", r.stdout)
        self.assertIn("capability=uninstalled_tool state=Disponible", r.stdout)

        # 2. Con --authorized uninstalled_tool: pasa a Autorizada (autorizada pero no preparada)
        r2 = monday("cap", "status", "--catalog", cat_file, "--authorized", "uninstalled_tool", cwd=repo)
        self.assertEqual(r2.returncode, 0, r2.stdout)
        self.assertIn("capability=uninstalled_tool state=Autorizada", r2.stdout)
        # installed_tool no estaba en la lista de autorizadas -> queda como Disponible
        self.assertIn("capability=installed_tool state=Disponible", r2.stdout)

        # 3. Con --authorized installed_tool --active installed_tool -> Activa
        r3 = monday("cap", "status", "--catalog", cat_file, "--authorized", "installed_tool", "--active", "installed_tool", cwd=repo)
        self.assertEqual(r3.returncode, 0, r3.stdout)
        self.assertIn("capability=installed_tool state=Activa", r3.stdout)

        # 4. Con contrato YAML que autoriza scope.capabilities
        c_path = os.path.join(repo, "contract.yaml")
        with open(c_path, "w") as f:
            yaml.safe_dump(contract(scope={"allowed_files": ["a.py"], "capabilities": ["uninstalled_tool"]}), f)
        r4 = monday("cap", "status", "--catalog", cat_file, "--contract", c_path, cwd=repo)
        self.assertEqual(r4.returncode, 0, r4.stdout)
        self.assertIn("capability=uninstalled_tool state=Autorizada", r4.stdout)
        self.assertIn("capability=installed_tool state=Disponible", r4.stdout)

    def test_cap_status_ignores_untrusted_cwd_catalog(self):
        # An untrusted capabilities/catalog.yaml in CWD must NOT be loaded automatically
        repo = os.path.join(self.tmp, "hostile_repo")
        os.makedirs(os.path.join(repo, "capabilities"), exist_ok=True)
        pwned_marker = os.path.join(repo, "PWNED")
        with open(os.path.join(repo, "capabilities", "catalog.yaml"), "w") as f:
            f.write(f"capabilities:\n  evil:\n    check_cmd: touch {pwned_marker}\n    tier: FAST\n")
        r = monday("cap", "status", cwd=repo)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertFalse(os.path.exists(pwned_marker), "Hostile catalog in CWD was executed!")
        self.assertIn("capability=git", r.stdout, "Default harness catalog was not used!")

    def test_cap_status_handles_missing_binary_gracefully(self):
        # A check_cmd pointing to a non-existent binary must report prepared=failed without traceback
        repo = os.path.join(self.tmp, "missing_bin_repo")
        os.makedirs(os.path.join(repo, "capabilities"), exist_ok=True)
        cat_file = os.path.join(repo, "capabilities", "catalog.yaml")
        with open(cat_file, "w") as f:
            f.write("capabilities:\n  missing_tool:\n    check_cmd: non-existent-binary-xyz-123 --version\n    tier: FAST\n")
        r = monday("cap", "status", "--catalog", cat_file, cwd=repo)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("capability=missing_tool state=Disponible prepared=failed", r.stdout)

    def test_cap_status_handles_malformed_command_gracefully(self):
        # A check_cmd with unclosed quotes triggers ValueError in shlex; must report prepared=failed without traceback
        repo = os.path.join(self.tmp, "malformed_cmd_repo")
        os.makedirs(os.path.join(repo, "capabilities"), exist_ok=True)
        cat_file = os.path.join(repo, "capabilities", "catalog.yaml")
        with open(cat_file, "w") as f:
            f.write("capabilities:\n  broken_syntax:\n    check_cmd: sh -c 'unclosed quote\n    tier: FAST\n")
        r = monday("cap", "status", "--catalog", cat_file, cwd=repo)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("capability=broken_syntax state=Disponible prepared=failed", r.stdout)

    def test_scope_capabilities_validation(self):
        d = contract()
        d["scope"]["capabilities"] = ["git", "python-ast"]
        r = monday("validate", self.write("t_caps.yaml", d))
        self.assertEqual(r.returncode, 0, r.stdout)

        d["scope"]["capabilities"] = "not_a_list"
        r_bad = monday("validate", self.write("t_bad_caps.yaml", d))
        self.assertEqual(r_bad.returncode, 1, r_bad.stdout)
        self.assertIn("scope.capabilities must be a list of non-empty strings", r_bad.stdout)


if __name__ == "__main__":
    unittest.main()
