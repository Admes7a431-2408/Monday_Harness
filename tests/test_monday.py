"""Pruebas de Monday: escenarios de validación (S1–S8), distribución e integridad de adaptadores.

Ejecutar: python3 -m unittest discover -s tests -v
Cada prueba crea un proyecto temporal, instala Monday con `core/monday.py install` y usa el CLI instalado.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC_CLI = REPO / "core" / "monday.py"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def run(cmd, cwd, inp=None, env=None):
    e = {**os.environ, **GIT_ENV, **(env or {})}
    e.pop("MONDAY_ROOT", None)
    return subprocess.run(cmd, cwd=cwd, input=inp, capture_output=True, text=True, env=e)


class Project:
    def __init__(self, git=True, platforms=None):
        self.dir = Path(tempfile.mkdtemp(prefix="monday-test-"))
        (self.dir / "src").mkdir()
        (self.dir / "src" / "calc.py").write_text("def add(a, b):\n    return a - b\n")
        (self.dir / "README.md").write_text("demo\n")
        (self.dir / ".gitignore").write_text("__pycache__/\n")
        self.git = git
        if git:
            self.sh("git", "init", "-q")
            self.commit("init")
        args = [sys.executable, str(SRC_CLI), "install", "."]
        for p in platforms or []:
            args += ["--platform", p]
        r = run(args, self.dir)
        assert r.returncode == 0, r.stdout + r.stderr
        if git:
            self.commit("monday")

    def sh(self, *cmd, inp=None, env=None):
        return run(list(cmd), self.dir, inp=inp, env=env)

    def m(self, *args, inp=None, env=None):
        return self.sh(sys.executable, ".monday/monday.py", *args, inp=inp, env=env)

    def commit(self, msg):
        self.sh("git", "add", "-A")
        self.sh("git", "commit", "-qm", msg)

    def write(self, rel, text):
        p = self.dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def read(self, rel):
        return (self.dir / rel).read_text()

    def features(self):
        return json.loads(self.read("features.json"))

    def add_feature(self, **f):
        data = self.features()
        base = {"id": "F-001", "title": "Arreglar add", "status": "pending", "risk": "medium",
                "scope": ["src/calc.py", "tests/**"],
                "acceptance_criteria": [{"id": "AC1", "text": "add(2, 3) == 5",
                                         "verify": "python3 -B -c 'import sys; sys.path.insert(0, \"src\"); import calc; assert calc.add(2, 3) == 5'"}]}
        base.update(f)
        data["features"].append(base)
        self.write("features.json", json.dumps(data, indent=2))
        if self.git:
            self.commit("feature")
        return base

    def fix_bug(self):
        self.write("src/calc.py", "def add(a, b):\n    return a + b\n")

    def cleanup(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class Base(unittest.TestCase):
    def project(self, **kw):
        p = Project(**kw)
        self.addCleanup(p.cleanup)
        return p


# ---------------------------------------------------------------- S1–S8

class S1DirectTask(Base):
    """Tarea sencilla sin delegación: sin feature activa no hay ceremonia ni objeciones."""

    def test_direct_edit_has_no_objection_and_init_passes(self):
        p = self.project()
        r = p.m("hook", "pre", "--platform", "claude",
                inp=json.dumps({"cwd": str(p.dir), "tool_name": "Edit", "tool_input": {"file_path": str(p.dir / "README.md")}}))
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "", "en modo directo el hook no debe objetar")
        r = p.sh("./init.sh")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("monday check: PASS", r.stdout)
        self.assertIn("UNAVAILABLE: no hay comprobaciones", r.stdout)


class S2Exploration(Base):
    """Exploración previa: el explorador y el revisor son de solo lectura y los hallazgos tienen destino persistente."""

    def test_explorer_and_reviewer_cannot_write(self):
        p = self.project()
        for agent in ("monday-explorer", "monday-reviewer"):
            front = p.read(f".claude/agents/{agent}.md").split("---")[1]
            tools = next(l for l in front.splitlines() if l.startswith("tools:"))
            for w in ("Edit", "Write", "NotebookEdit", "Agent"):
                self.assertNotIn(w, tools, f"{agent} no debe tener {w}")

    def test_exploration_log_exists_and_is_referenced(self):
        p = self.project()
        self.assertTrue((p.dir / "progress" / "exploration_logs.md").is_file())
        self.assertIn("exploration_logs.md", p.read("AGENTS.md"))
        self.assertIn("exploration_logs", p.read(".monday/roles/implementer.md"))


class S3VerifiableChange(Base):
    """Modificación con criterios verificables: done acepta solo con evidencia y mueve el resumen al historial."""

    def test_full_cycle(self):
        p = self.project()
        p.add_feature()
        self.assertEqual(p.m("start", "F-001").returncode, 0)
        self.assertIn("F-001", p.read("progress/current.md"))
        r = p.m("verify", "F-001")
        self.assertEqual(r.returncode, 1, "el criterio debe fallar antes del arreglo (capaz de fallar)")
        p.fix_bug()
        p.write("progress/current.md", p.read("progress/current.md").replace(
            "## Resumen para el historial\n", "## Resumen para el historial\n\nCorregido el signo de add().\n"))
        r = p.m("done", "F-001")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ACEPTADO", r.stdout)
        self.assertEqual(p.features()["features"][0]["status"], "done")
        hist = p.read("progress/history.md")
        self.assertIn("F-001 · DONE", hist)
        self.assertIn("AC1 PASS", hist)
        self.assertIn("Corregido el signo", hist)
        self.assertIn("Feature: (ninguna)", p.read("progress/current.md"))


class S4DelegationAndReview(Base):
    """Tarea compleja (risk high): sin revisión aprobada no hay cierre; la revisión caduca si el diff cambia."""

    def test_review_required_and_anchored_to_diff(self):
        p = self.project()
        p.add_feature(risk="high")
        p.m("start", "F-001")
        p.fix_bug()
        r = p.m("done", "F-001")
        self.assertEqual(r.returncode, 1)
        self.assertIn("revisión independiente", r.stdout)
        self.assertEqual(p.m("review", "F-001", "--verdict", "changes_required", "--by", "monday-reviewer",
                             "--notes", "falta test").returncode, 0)
        self.assertEqual(p.m("done", "F-001").returncode, 1)
        p.m("review", "F-001", "--verdict", "approve", "--by", "monday-reviewer")
        p.write("src/calc.py", p.read("src/calc.py") + "# cambio tras la revisión\n")
        r = p.m("done", "F-001")
        self.assertEqual(r.returncode, 1)
        self.assertIn("después de la revisión", r.stdout)
        p.m("review", "F-001", "--verdict", "approve", "--by", "monday-reviewer")
        r = p.m("done", "F-001")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("REVISIÓN: changes_required", p.read("progress/history.md"))


class S5FailedVerification(Base):
    """Un fallo de verificación impide declarar éxito y queda registrado."""

    def test_failing_criterion_blocks_done(self):
        p = self.project()
        p.add_feature()
        p.m("start", "F-001")
        r = p.m("done", "F-001")
        self.assertEqual(r.returncode, 1)
        self.assertIn("RECHAZADO", r.stdout)
        self.assertIn("[FAIL] AC1", r.stdout)
        self.assertEqual(p.features()["features"][0]["status"], "in_progress")
        self.assertIn("F-001 · RECHAZADO", p.read("progress/history.md"))

    def test_failing_init_blocks_done(self):
        p = self.project()
        p.add_feature()
        p.m("start", "F-001")
        p.fix_bug()
        p.write("init.sh", "#!/usr/bin/env bash\necho 'lint: error'\nexit 1\n")
        r = p.m("done", "F-001")
        self.assertEqual(r.returncode, 1)
        self.assertIn("[FAIL] init.sh", r.stdout)

    def test_manual_status_edit_is_not_trusted_by_check(self):
        p = self.project()
        p.add_feature(scope=[], acceptance_criteria=[])
        data = p.features()
        data["features"][0]["status"] = "done"
        p.write("features.json", json.dumps(data))
        r = p.m("check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("necesita 'scope'", r.stdout)


class S6Recovery(Base):
    """Interrupción: un proceso nuevo reconstruye el estado solo desde archivos."""

    def test_status_and_session_start_restore_context(self):
        p = self.project()
        p.add_feature()
        p.m("start", "F-001")
        p.write("progress/current.md", p.read("progress/current.md").replace(
            "## Estado y próximos pasos\n", "## Estado y próximos pasos\n\nPaso 2 de 3: falta el test de regresión.\n"))
        r = p.m("status")
        self.assertIn("EN CURSO: F-001", r.stdout)
        self.assertIn("Paso 2 de 3", r.stdout)
        for plat in ("claude", "antigravity"):
            payload = {"cwd": str(p.dir)} if plat == "claude" else {"workspacePaths": [str(p.dir)]}
            r = p.m("hook", "session-start", "--platform", plat, inp=json.dumps(payload))
            self.assertIn("Paso 2 de 3", r.stdout)
        inj = json.loads(p.m("hook", "session-start", "--platform", "antigravity",
                             inp=json.dumps({"workspacePaths": [str(p.dir)]})).stdout)
        self.assertIn("EN CURSO: F-001", inj["injectSteps"][0]["systemMessage"]["systemMessage"])


class S7MissingCapability(Base):
    """Falta una capacidad o dependencia: UNAVAILABLE nunca cuenta como éxito; la alternativa exige evidencia explícita."""

    def test_missing_tool_is_unavailable_not_pass(self):
        p = self.project()
        p.add_feature(acceptance_criteria=[{"id": "AC1", "text": "e2e verde", "verify": "herramienta-inexistente --run"}])
        p.m("start", "F-001")
        p.fix_bug()
        r = p.m("done", "F-001")
        self.assertEqual(r.returncode, 1)
        self.assertIn("[UNAVAILABLE] AC1", r.stdout)
        r = p.m("done", "F-001", "--manual", "AC1=probado a mano en el navegador: flujo OK")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("Evidencia manual AC1", p.read("progress/history.md"))

    def test_without_git_scope_needs_manual_evidence(self):
        p = self.project(git=False)
        p.add_feature()
        p.m("start", "F-001")
        p.fix_bug()
        r = p.m("done", "F-001")
        self.assertEqual(r.returncode, 1)
        self.assertIn("[UNAVAILABLE] scope", r.stdout)
        r = p.m("done", "F-001", "--manual", "scope=solo src/calc.py")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_init_fails_clearly_without_python(self):
        p = self.project()
        bindir = p.dir / "nopython-bin"
        bindir.mkdir()
        for tool in ("bash", "dirname", "env"):
            os.symlink(shutil.which(tool), bindir / tool)
        r = p.sh("./init.sh", env={"PATH": str(bindir)})
        self.assertEqual(r.returncode, 1)
        self.assertIn("python3 no está disponible", r.stderr)

    def test_manual_criterion_requires_evidence(self):
        p = self.project()
        p.add_feature(acceptance_criteria=[{"id": "AC1", "text": "El texto del botón es claro"}])
        p.m("start", "F-001")
        r = p.m("done", "F-001")
        self.assertEqual(r.returncode, 1)
        self.assertIn("PENDING_MANUAL", r.stdout)


class S8OutOfScope(Base):
    """Operación fuera de alcance: los hooks piden permiso y done rechaza el diff."""

    def test_hooks_ask_outside_scope(self):
        p = self.project()
        p.add_feature()
        p.m("start", "F-001")
        out_path = str(p.dir / "README.md")
        r = p.m("hook", "pre", "--platform", "claude",
                inp=json.dumps({"cwd": str(p.dir), "tool_name": "Write", "tool_input": {"file_path": out_path}}))
        decision = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "ask")
        self.assertIn("fuera del alcance de F-001", decision["permissionDecisionReason"])
        r = p.m("hook", "pre", "--platform", "antigravity",
                inp=json.dumps({"workspacePaths": [str(p.dir)],
                                "toolCall": {"name": "write_to_file", "args": {"TargetFile": out_path}}}))
        self.assertEqual(json.loads(r.stdout)["decision"], "deny", "en agy solo 'deny' bloquea en accept-edits")
        in_path = str(p.dir / "src" / "calc.py")
        r = p.m("hook", "pre", "--platform", "antigravity",
                inp=json.dumps({"workspacePaths": [str(p.dir)],
                                "toolCall": {"name": "write_to_file", "args": {"TargetFile": in_path}}}))
        self.assertEqual(r.stdout, "", "dentro del alcance no hay salida (agy trata {} como denegación)")
        self.assertEqual(p.m("guard", "progress/current.md").returncode, 0)

    def test_agy_guard_does_not_depend_on_tool_names(self):
        """agy cambió su catálogo (edit_file/Path) sin cambiar de versión: la guarda no puede depender de nombres."""
        p = self.project()
        p.add_feature()
        p.m("start", "F-001")
        def pre(name, args):
            r = p.m("hook", "pre", "--platform", "antigravity",
                    inp=json.dumps({"workspacePaths": [str(p.dir)], "toolCall": {"name": name, "args": args}}))
            return json.loads(r.stdout)["decision"] if r.stdout.strip() else None
        out, inside = str(p.dir / "README.md"), str(p.dir / "src" / "calc.py")
        self.assertEqual(pre("edit_file", {"Path": out, "Target": "demo", "Replacement": "demo\nhola"}), "deny")
        self.assertEqual(pre("herramienta_futura", {"DestinationFile": "file://" + out}), "deny")
        self.assertEqual(pre("apply_patch", {"Input": "*** Begin Patch\n*** Update File: README.md\n@@\n+hola\n*** End Patch"}), "deny")
        self.assertIsNone(pre("edit_file", {"Path": inside, "Target": "a - b", "Replacement": "a + b"}))
        self.assertIsNone(pre("replace_file_content", {"TargetFile": inside, "TargetContent": "// comentario",
                                                       "ReplacementContent": "/etc/passwd"}),
                          "el contenido no es una ruta")
        self.assertEqual(pre("search_replace", {"file_path": out, "old": "a", "new": "b"}), "deny", "verbo de escritura > prefijo")
        self.assertEqual(pre("find_and_replace", {"TargetFile": out}), "deny")
        self.assertEqual(pre("write_file", {"filename": "README.md", "content": "x"}), "deny")
        self.assertEqual(pre("move_file", {"source": "src/calc.py", "destination": "README.md"}), "deny")
        self.assertIsNone(pre("run_snippet_tool", {"Source": "x = 1"}), "código de una línea no es una ruta")
        r = p.m("hook", "pre", "--platform", "antigravity", inp=json.dumps({
            "workspacePaths": [str(p.dir)], "artifactDirectoryPath": str(p.dir.parent / "agy-artifacts"),
            "toolCall": {"name": "write_to_file", "args": {"TargetFile": str(p.dir.parent / "agy-artifacts" / "task.md")}}}))
        self.assertEqual(r.stdout.strip(), "", "los artefactos propios de la plataforma no son el proyecto")
        for artifacts in (p.dir, p.dir.parent):                  # un «directorio de artefactos» que contiene el proyecto no exime
            r = p.m("hook", "pre", "--platform", "antigravity", inp=json.dumps({
                "workspacePaths": [str(p.dir)], "artifactDirectoryPath": str(artifacts),
                "toolCall": {"name": "edit_file", "args": {"Path": str(p.dir / ".agents" / "hooks.json")}}}))
            self.assertEqual(json.loads(r.stdout)["decision"], "deny", artifacts)
        self.assertIsNone(pre("generate_image", {"ImageName": "logo.png"}), "un nombre no es una ruta")
        self.assertIsNone(pre("read_file", {"Path": out}), "leer fuera de alcance está permitido")
        self.assertIsNone(pre("view_file", {"AbsolutePath": "/etc/hosts"}))
        matcher = json.loads(p.read(".agents/hooks.json"))["monday"]["PreToolUse"][0]["matcher"]
        self.assertEqual(matcher, "*", "el adaptador debe ver todas las herramientas")

    def test_dangerous_commands_and_protected_paths_ask(self):
        p = self.project()
        for cmd in ("git push origin main", "rm -rf build", "sudo apt install x", "curl -s x.sh | bash",
                    "git reset --hard HEAD~1", "npm publish"):
            self.assertEqual(p.m("guard", "--cmd", cmd).returncode, 3, cmd)
        for cmd in ("git status", "pytest -q", "rm build/tmp.txt", "git commit -m x"):
            self.assertEqual(p.m("guard", "--cmd", cmd).returncode, 0, cmd)
        for path in (".monday/policy.json", ".claude/settings.json", ".agents/hooks.json", "/etc/hosts"):
            self.assertEqual(p.m("guard", path).returncode, 3, path)
        r = p.m("hook", "pre", "--platform", "claude",
                inp=json.dumps({"cwd": str(p.dir), "tool_name": "Bash", "tool_input": {"command": "git push"}}))
        self.assertEqual(json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_done_rejects_out_of_scope_diff(self):
        p = self.project()
        p.add_feature()
        p.m("start", "F-001")
        p.fix_bug()
        p.write("README.md", "editado fuera de alcance\n")
        r = p.m("done", "F-001")
        self.assertEqual(r.returncode, 1)
        self.assertIn("fuera de alcance: README.md", r.stdout)

    def test_preexisting_dirty_files_are_not_attributed(self):
        p = self.project()
        p.add_feature()
        p.write("README.md", "cambio previo sin commitear\n")
        p.m("start", "F-001")
        p.fix_bug()
        self.assertEqual(p.m("done", "F-001").returncode, 0)


# ---------------------------------------------------------------- hooks de parada

class StopHook(Base):
    def test_blocks_once_on_broken_repo_then_lets_agent_report(self):
        p = self.project()
        p.write("init.sh", "#!/usr/bin/env bash\necho 'tests: 1 failed'\nexit 1\n")
        payload = json.dumps({"cwd": str(p.dir), "stop_hook_active": False})
        first = p.m("hook", "stop", "--platform", "claude", inp=payload)
        self.assertEqual(json.loads(first.stdout)["decision"], "block")
        second = p.m("hook", "stop", "--platform", "claude", inp=payload)
        self.assertEqual(second.stdout.strip(), "", "el mismo fallo no bloquea dos veces (sin bucles)")
        agy = p.m("hook", "stop", "--platform", "antigravity", inp=json.dumps({"workspacePaths": [str(p.dir)]}))
        self.assertEqual(json.loads(agy.stdout)["decision"], "continue")

    def test_clean_tree_or_active_stop_hook_does_nothing(self):
        p = self.project()
        r = p.m("hook", "stop", "--platform", "claude", inp=json.dumps({"cwd": str(p.dir)}))
        self.assertEqual(r.stdout.strip(), "")
        p.write("src/new.py", "x = 1\n")
        r = p.m("hook", "stop", "--platform", "claude", inp=json.dumps({"cwd": str(p.dir), "stop_hook_active": True}))
        self.assertEqual(r.stdout.strip(), "")

    def test_broken_hook_input_fails_open(self):
        p = self.project()
        r = p.m("hook", "pre", "--platform", "claude", inp="no es json")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")


# ---------------------------------------------------------------- features.json

class FeatureSchema(Base):
    def test_typo_in_key_is_an_error(self):
        p = self.project()
        p.add_feature(scopes=["src/**"])
        r = p.m("check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("claves desconocidas", r.stdout)

    def test_unsafe_scope_and_single_active_feature(self):
        p = self.project()
        p.add_feature(scope=["../otro/**"])
        self.assertIn("sin '..'", p.m("check").stdout)
        p2 = self.project()
        p2.add_feature()
        p2.add_feature(id="F-002")
        p2.m("start", "F-001")
        r = p2.m("start", "F-002")
        self.assertEqual(r.returncode, 2)
        self.assertIn("ya hay una feature en curso", r.stderr)

    def test_dependencies_and_block(self):
        p = self.project()
        p.add_feature()
        p.add_feature(id="F-002", depends_on=["F-001"])
        self.assertIn("depende de", p.m("start", "F-002").stderr)
        p.m("start", "F-001")
        p.m("block", "F-001", "--reason", "la causa está en un módulo excluido")
        self.assertIn("BLOQUEADA: F-001", p.m("status").stdout)
        self.assertEqual(p.m("start", "F-001").returncode, 0, "una feature bloqueada se reanuda con start")


# ---------------------------------------------------------------- distribución

class Distribution(Base):
    def test_update_is_idempotent_and_detects_local_edits(self):
        p = self.project()
        r = run([sys.executable, str(SRC_CLI), "install", "."], p.dir)
        self.assertIn("sin cambios", r.stdout)
        p.write(".monday/method.md", p.read(".monday/method.md") + "\nregla local divergente\n")
        r = p.m("check")
        self.assertEqual(r.returncode, 1)
        self.assertIn(".monday/method.md difiere", r.stdout)
        r = run([sys.executable, str(SRC_CLI), "install", "."], p.dir)
        self.assertEqual(r.returncode, 2)
        self.assertIn("archivos gestionados modificados", r.stderr)

    def test_existing_files_are_merged_not_overwritten(self):
        d = Path(tempfile.mkdtemp(prefix="monday-test-"))
        self.addCleanup(shutil.rmtree, d, True)
        (d / "AGENTS.md").write_text("# Mi proyecto\n\nRegla propia del equipo.\n")
        (d / "CLAUDE.md").write_text("Instrucciones propias.\n")
        (d / ".claude").mkdir()
        (d / ".claude" / "settings.json").write_text(json.dumps({"permissions": {"allow": ["Bash(make:*)"]},
                                                                   "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo mio"}]}]}}))
        self.assertEqual(run([sys.executable, str(SRC_CLI), "install", "."], d).returncode, 0)
        agents = (d / "AGENTS.md").read_text()
        self.assertIn("Regla propia del equipo.", agents)
        self.assertIn("<!-- monday:begin", agents)
        self.assertIn("Instrucciones propias.", (d / "CLAUDE.md").read_text())
        self.assertIn("@AGENTS.md", (d / "CLAUDE.md").read_text())
        settings = json.loads((d / ".claude" / "settings.json").read_text())
        self.assertEqual(settings["permissions"]["allow"], ["Bash(make:*)"])
        stop_cmds = [h["command"] for g in settings["hooks"]["Stop"] for h in g["hooks"]]
        self.assertIn("echo mio", stop_cmds)
        self.assertEqual(sum("hook stop --platform claude" in c for c in stop_cmds), 1)
        self.assertEqual(run([sys.executable, str(SRC_CLI), "install", "."], d).returncode, 0)
        settings = json.loads((d / ".claude" / "settings.json").read_text())
        self.assertEqual(sum("hook stop --platform claude" in h["command"]
                             for g in settings["hooks"]["Stop"] for h in g["hooks"]), 1)
        r = run([sys.executable, str(d / ".monday" / "monday.py"), "rollback", "."], d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((d / "AGENTS.md").read_text(), "# Mi proyecto\n\nRegla propia del equipo.\n")
        self.assertEqual((d / "CLAUDE.md").read_text(), "Instrucciones propias.\n")
        self.assertFalse((d / ".monday").exists())
        self.assertFalse((d / "features.json").exists())

    def test_existing_dirty_project_with_legacy_residue_is_restored_byte_for_byte(self):
        d = Path(tempfile.mkdtemp(prefix="monday-test-"))
        home = Path(tempfile.mkdtemp(prefix="monday-home-"))
        self.addCleanup(shutil.rmtree, d, True)
        self.addCleanup(shutil.rmtree, home, True)
        files = {"AGENTS.md": "# App\n\nNotas propias.\n", "CLAUDE.md": "Usa tabs.\n", "src/app.py": "print(1)\n",
                 ".claude/settings.json": json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo mio"}]}]}}),
                 "init.sh": "#!/bin/sh\necho checks propios\n", ".monday/CONTEXT.md": "contexto 0.9\n",
                 ".monday/contracts/X.yaml": "id: X\n"}
        for rel, text in files.items():
            (d / rel).parent.mkdir(parents=True, exist_ok=True)
            (d / rel).write_text(text)
        (d / "init.sh").chmod(0o755)
        run(["git", "init", "-q"], d); run(["git", "add", "-A"], d); run(["git", "commit", "-qm", "init"], d)
        (d / "src" / "app.py").write_text("print(2)  # sin commitear\n")
        (d / "notas.txt").write_text("sin rastrear\n")
        (home / ".claude" / "skills").mkdir(parents=True)
        (home / ".claude" / "skills" / "monday").symlink_to(d)          # enlace global que dejaba install.sh 0.9
        (home / ".claude" / "agents").mkdir()
        (home / ".claude" / "agents" / "af-worker.md").symlink_to(d / "CLAUDE.md")   # y el de install.sh 0.1 (AgentForge)
        (home / ".claude" / "agents" / "mine.md").write_text("agente propio\n")       # no es un enlace: sin aviso
        snapshot = lambda: {str(p.relative_to(d)): p.read_bytes() for p in d.rglob("*") if p.is_file() and ".git" not in p.relative_to(d).parts}
        before = snapshot()
        env = {"HOME": str(home)}
        r = run([sys.executable, str(SRC_CLI), "install", "."], d, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("init.sh es del proyecto y no ejecuta", r.stdout)
        self.assertIn(".monday/CONTEXT.md, .monday/contracts", r.stdout)
        self.assertIn(".claude/skills/monday", r.stdout)
        self.assertIn(".claude/agents/af-worker.md", r.stdout)
        self.assertIn("install.sh --uninstall --agents", r.stdout)
        self.assertNotIn("mine.md", r.stdout)
        for rel in ("init.sh", "src/app.py", "notas.txt", ".monday/CONTEXT.md", ".monday/contracts/X.yaml"):
            self.assertEqual((d / rel).read_bytes(), before[rel], rel)
        self.assertEqual(run([sys.executable, ".monday/monday.py", "check"], d).returncode, 0)
        self.assertIn("sin cambios", run([sys.executable, str(SRC_CLI), "install", "."], d, env=env).stdout)
        (d / ".monday" / "runtime").mkdir(exist_ok=True)                   # lo que dejan las sesiones con hooks
        (d / ".monday" / "runtime" / "hooks.log").write_text("{}\n")
        r = run([sys.executable, ".monday/monday.py", "rollback", ".", "--all"], d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(snapshot(), before)

    def test_rollback_keeps_project_data_created_after_install(self):
        p = self.project()
        p.add_feature()
        r = p.m("rollback", ".")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("conservar features.json", r.stdout)
        self.assertTrue((p.dir / "features.json").exists())
        self.assertFalse((p.dir / ".monday" / "monday.py").exists())

    def test_platform_selection(self):
        p = self.project(platforms=["antigravity"])
        self.assertFalse((p.dir / ".claude").exists())
        self.assertFalse((p.dir / "CLAUDE.md").exists())
        self.assertIn("monday", json.loads(p.read(".agents/hooks.json")))
        self.assertEqual(p.m("check").returncode, 0)

    def test_local_runtime_state_is_never_distributed(self):
        # En el repo de Monday `.monday -> core`: el estado efímero puede acabar en core/runtime y core/backups.
        import importlib.util
        spec = importlib.util.spec_from_file_location("monday_cli", SRC_CLI)
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        src = Path(tempfile.mkdtemp(prefix="monday-src-"))
        target = Path(tempfile.mkdtemp(prefix="monday-test-"))
        self.addCleanup(shutil.rmtree, src, True)
        self.addCleanup(shutil.rmtree, target, True)
        shutil.copytree(REPO / "core", src / "core", ignore=shutil.ignore_patterns("runtime", "backups", "__pycache__"))
        shutil.copytree(REPO / "adapters", src / "adapters")
        for leaked in ("runtime/verification.json", "backups/x/journal.json", "__pycache__/m.pyc"):
            (src / "core" / leaked).parent.mkdir(parents=True, exist_ok=True)
            (src / "core" / leaked).write_text("{}")
        paths = [rel for rel, _, _ in cli.plan_install(src, target, ["claude", "antigravity"])]
        self.assertFalse([p for p in paths if "/runtime/" in p or "/backups/" in p or "__pycache__" in p], paths)
        self.assertIn(".monday/monday.py", paths)

    def test_removed_adapter_hooks_are_detected(self):
        p = self.project()
        p.write(".agents/hooks.json", "{}\n")
        r = p.m("check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("adaptador antigravity", r.stdout)


# ---------------------------------------------------------------- regresiones de la revisión independiente de M-001

class ReviewRegressions(Base):
    def test_contract_tampering_is_rejected_until_amended(self):
        p = self.project()
        p.add_feature(risk="high")
        p.m("start", "F-001")
        data = p.features()
        f = data["features"][0]
        f["risk"], f["scope"] = "low", ["**"]
        f["acceptance_criteria"][0]["verify"] = "true"
        p.write("features.json", json.dumps(data, indent=2))
        p.write("README.md", "editado\n")
        r = p.m("done", "F-001")
        self.assertEqual(r.returncode, 1, "rebajar el contrato a mano no debe permitir el cierre")
        self.assertIn("[FAIL] contract", r.stdout)
        self.assertEqual(p.m("amend", "F-001", "--reason", "el humano rebajó el riesgo").returncode, 0)
        hist = p.read("progress/history.md")
        self.assertIn("CONTRATO MODIFICADO", hist)
        self.assertIn("el humano rebajó el riesgo", hist)

    def test_moving_diff_base_is_contract_tampering(self):
        p = self.project()
        p.add_feature(risk="high")
        p.m("start", "F-001")
        p.fix_bug()
        p.write("README.md", "fuera de alcance\n")
        p.commit("cuela un cambio")
        data = p.features()
        data["features"][0]["base"] = p.sh("git", "rev-parse", "HEAD").stdout.strip()
        p.write("features.json", json.dumps(data, indent=2))
        p.m("review", "F-001", "--verdict", "approve", "--by", "x")
        r = p.m("done", "F-001")
        self.assertEqual(r.returncode, 1)
        self.assertIn("[FAIL] contract", r.stdout)

    def test_amend_requires_human_permission(self):
        p = self.project()
        self.assertEqual(p.m("guard", "--cmd", "python3 .monday/monday.py amend F-001 --reason x").returncode, 3)

    def test_amend_invalidates_previous_review(self):
        p = self.project()
        p.add_feature(risk="high")
        p.m("start", "F-001")
        p.fix_bug()
        p.m("review", "F-001", "--verdict", "approve", "--by", "monday-reviewer")
        data = p.features()
        data["features"][0]["scope"].append("docs/**")
        p.write("features.json", json.dumps(data, indent=2))
        self.assertIn("revisión invalidada", p.m("amend", "F-001", "--reason", "docs").stdout)
        self.assertEqual(p.m("done", "F-001").returncode, 1)

    def test_rollback_keeps_merged_files_edited_after_install(self):
        d = Path(tempfile.mkdtemp(prefix="monday-test-"))
        self.addCleanup(shutil.rmtree, d, True)
        (d / "AGENTS.md").write_text("# Equipo\n")
        run([sys.executable, str(SRC_CLI), "install", "."], d)
        (d / "AGENTS.md").write_text((d / "AGENTS.md").read_text() + "Nota añadida por el equipo.\n")
        r = run([sys.executable, str(d / ".monday" / "monday.py"), "rollback", "."], d)
        self.assertIn("conservar AGENTS.md", r.stdout)
        self.assertIn("Nota añadida por el equipo.", (d / "AGENTS.md").read_text())
        self.assertTrue(any((d / ".monday" / "backups").iterdir()), "el backup se conserva para --force")
        run([sys.executable, str(SRC_CLI), "rollback", ".", "--force"], d)
        self.assertEqual((d / "AGENTS.md").read_text(), "# Equipo\n")

    def test_rollback_all_removes_runtime_state(self):
        p = self.project()
        p.write("src/x.py", "x = 1\n")
        p.write("init.sh", "#!/usr/bin/env bash\nexit 1\n")
        p.m("hook", "stop", "--platform", "claude", inp=json.dumps({"cwd": str(p.dir)}))
        self.assertTrue((p.dir / ".monday" / "runtime").exists())
        p.sh("git", "checkout", "init.sh")
        p.m("rollback", ".", "--all", "--force")
        self.assertFalse((p.dir / ".monday").exists())

    def test_stop_signature_ignores_variable_output(self):
        p = self.project()
        p.write("init.sh", '#!/usr/bin/env bash\necho "FAIL: pytest (exit 1)"\necho "Ran 3 tests in $RANDOM.$RANDOM s"\nexit 1\n')
        p.write("src/x.py", "x = 1\n")
        payload = json.dumps({"workspacePaths": [str(p.dir)]})
        self.assertEqual(json.loads(p.m("hook", "stop", "--platform", "antigravity", inp=payload).stdout)["decision"], "continue")
        self.assertEqual(p.m("hook", "stop", "--platform", "antigravity", inp=payload).stdout.strip(), "")

    def test_stop_skips_when_only_memory_changed(self):
        p = self.project()
        p.write("init.sh", "#!/usr/bin/env bash\nexit 1\n")
        p.commit("init roto a propósito")
        p.write("progress/current.md", "nota\n")
        r = p.m("hook", "stop", "--platform", "claude", inp=json.dumps({"cwd": str(p.dir)}))
        self.assertEqual(r.stdout.strip(), "")


# ---------------------------------------------------------------- AC4: el cierre lo decide la verificación, no el informe

class VerificationState(Base):
    """El agente puede terminar con cualquier texto (agy devuelve el último del modelo y SUCCESS):
    el estado verificado se persiste, se comunica y es lo único que decide el cierre."""

    def stop(self, p, plat="antigravity"):
        payload = {"workspacePaths": [str(p.dir)]} if plat == "antigravity" else {"cwd": str(p.dir)}
        return p.m("hook", "stop", "--platform", plat, inp=json.dumps(payload))

    def red_project(self):
        p = self.project()
        p.add_feature()
        p.write("init.sh", p.read("init.sh").replace('  # "npm run lint"', '  "python3 -B -c \'import sys; sys.path.insert(0, \\"src\\"); import calc; assert calc.add(2, 3) == 5\'"'))
        p.commit("init con check del bug")
        p.m("start", "F-001")
        p.write("src/calc.py", "# revisado\n" + p.read("src/calc.py"))   # el agente toca, pero no arregla
        return p

    def test_green_verification_allows_closure(self):
        p = self.project()
        p.add_feature()
        p.m("start", "F-001")
        p.fix_bug()
        self.assertEqual(self.stop(p).stdout.strip(), "", "en verde el hook no bloquea")
        self.assertIn("Verificación: VERDE", p.m("status").stdout)
        self.assertEqual(p.m("done", "F-001").returncode, 0)

    def test_red_session_ending_with_success_claim_cannot_close(self):
        p = self.red_project()
        self.assertEqual(json.loads(self.stop(p).stdout)["decision"], "continue")
        # el agente responde «todo correcto» y vuelve a parar: la plataforma lo deja terminar…
        self.assertEqual(self.stop(p).stdout.strip(), "")
        # …pero el estado verificado queda persistido y comunicado, y el cierre se rechaza
        hist = p.read("progress/history.md")
        self.assertIn("SESIÓN TERMINADA CON init.sh EN ROJO (antigravity)", hist)
        status = p.m("status").stdout
        self.assertIn("Verificación: ROJO", status)
        self.assertIn("NO está terminado", status)
        start = json.loads(p.m("hook", "session-start", "--platform", "antigravity",
                               inp=json.dumps({"workspacePaths": [str(p.dir)]})).stdout)
        self.assertIn("Verificación: ROJO", start["injectSteps"][0]["systemMessage"]["systemMessage"])
        r = p.m("done", "F-001")
        self.assertEqual(r.returncode, 1)
        self.assertIn("[FAIL] init.sh", r.stdout)

    def test_platform_termination_without_second_stop_still_red(self):
        p = self.red_project()
        self.stop(p, plat="claude")                    # un solo Stop: la plataforma corta sin volver a llamarlo
        self.assertIn("Verificación: ROJO", p.m("status").stdout)
        self.assertEqual(p.m("done", "F-001").returncode, 1)

    def test_absent_or_stale_evidence_is_not_success(self):
        p = self.project()
        p.write("src/calc.py", "def add(a, b):\n    return a + b\n")
        self.assertIn("ninguna registrada", p.m("status").stdout)
        self.stop(p)
        self.assertIn("Verificación: VERDE", p.m("status").stdout)
        p.write("src/otro.py", "x = 1\n")
        self.assertIn("DESACTUALIZADA", p.m("status").stdout)

    def test_green_does_not_survive_a_commit(self):
        p = self.project()
        p.add_feature()
        p.m("start", "F-001")
        p.fix_bug()
        p.commit("arreglo commiteado antes de cerrar")   # done verifica en verde sobre un árbol limpio
        self.assertEqual(p.m("done", "F-001").returncode, 0)
        self.assertIn("Verificación: VERDE", p.m("status").stdout)
        p.write("src/calc.py", "def add(a, b):\n    return a - b\n")
        p.commit("código roto commiteado")
        status = p.m("status").stdout
        self.assertNotIn("Verificación: VERDE", status)
        self.assertIn("DESACTUALIZADA", status)

    def test_claude_second_stop_in_red_is_recorded(self):
        p = self.red_project()
        self.stop(p, plat="claude")
        r = p.m("hook", "stop", "--platform", "claude", inp=json.dumps({"cwd": str(p.dir), "stop_hook_active": True}))
        self.assertEqual(r.stdout.strip(), "", "no se bloquea dos veces")
        self.assertIn("SESIÓN TERMINADA CON init.sh EN ROJO (claude)", p.read("progress/history.md"))

    def test_missing_init_is_red_not_success(self):
        p = self.project()
        p.add_feature()
        p.m("start", "F-001")
        p.fix_bug()
        (p.dir / "init.sh").unlink()
        r = p.m("done", "F-001")
        self.assertEqual(r.returncode, 1)
        self.assertIn("init.sh no existe", r.stdout)
        self.assertIn("Verificación: ROJO", p.m("status").stdout)


# ---------------------------------------------------------------- integridad del diseño

class DesignIntegrity(unittest.TestCase):
    def test_agents_md_template_under_200_lines(self):
        self.assertLess(len((REPO / "core/templates/AGENTS.md").read_text().splitlines()), 200)
        self.assertLess(len((REPO / "AGENTS.md").read_text().splitlines()), 200)

    def test_repo_agents_md_block_matches_template(self):
        block = lambda t: t[t.index("<!-- monday:begin"):t.index("<!-- monday:end -->")]
        self.assertEqual(block((REPO / "AGENTS.md").read_text()), block((REPO / "core/templates/AGENTS.md").read_text()))

    def test_adapters_point_to_core_roles_instead_of_copying(self):
        for agent in (REPO / "adapters").glob("*/agents/*.md"):
            body = agent.read_text().split("---", 2)[2]
            role = agent.stem.replace("monday-", "")
            self.assertIn(f".monday/roles/{role}.md", body, agent)
            self.assertLess(len(body.splitlines()), 5, f"{agent}: el cuerpo debe ser un puntero, no una copia")

    def test_golden_rules_live_in_one_place(self):
        marker = "Evidencia o nada"
        holders = [p for p in REPO.rglob("*.md") if ".git" not in p.parts and marker in p.read_text()]
        allowed = {REPO / "core/templates/AGENTS.md", REPO / "AGENTS.md"}
        self.assertTrue(set(holders) <= allowed, holders)

    def test_platform_specifics_stay_out_of_the_core_method(self):
        text = (REPO / "core/method.md").read_text() + "".join(p.read_text() for p in (REPO / "core/roles").glob("*.md"))
        for word in ("Claude", "Antigravity", "haiku", "sonnet", "opus", "gemini", "settings.json", "hooks.json"):
            self.assertNotIn(word, text, f"el núcleo no debe nombrar '{word}'")


if __name__ == "__main__":
    unittest.main()
