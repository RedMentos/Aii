"""Network-free staged deployment regression: real launcher switch, immutable snapshots.

No Android phone, model downloads or GitHub access. Tests only source/data
separation, rollback boundaries and fail-closed conditions.
"""
from contextlib import redirect_stdout
from pathlib import Path
import hashlib
import io
import json
import subprocess
import tempfile
import threading
import types
import unittest
from unittest import mock

from v13 import runtime_deploy as d


class RuntimeDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.checkout = self.root / "checkout"
        self.code = self.checkout / "v13/code"
        for rel in d.REQUIRED:
            path = self.code / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("fake fixture " + rel).encode())
        for rel in d.COPY_SUBTREES:
            (self.code / rel).mkdir(parents=True, exist_ok=True)
        actual_code = Path(d.__file__).resolve().parents[1]
        for rel in (d.UI_SOURCE, "v13/operator.py", d.UI_BUILDER):
            (self.code / rel).write_bytes((actual_code / rel).read_bytes())
        self.home = self.root / "data-home"
        (self.home / "bin").mkdir(parents=True)
        (self.home / "models").mkdir(parents=True)
        (self.home / "config").mkdir(parents=True)
        (self.home / "data/db").mkdir(parents=True)
        self.launcher = self.home / "bin/v13"
        self.old = b"#!/bin/sh\necho old\n"
        self.launcher.write_bytes(self.old)
        (self.home / "models/model.gguf").write_bytes(b"GGUF_NOT_A_REAL_MODEL")
        (self.home / "config/settings.json").write_text('{"threads":4}')
        (self.home / "data/db/brain.sqlite3").write_bytes(b"EXISTING_DB_DO_NOT_CHANGE")
        self.private = self.root / "private"
        self.builds = self.root / "builds"
        self.commit = "d" * 40
        self.source_patch = mock.patch.object(d, "_source",
            return_value=(self.checkout, self.code, self.commit))
        self.stop_patch = mock.patch.object(d, "_check_stopped")
        self.selftest_patch = mock.patch.object(d, "_selftest")
        # Legacy launcher/rollback cases use a small synthetic source tree.
        # Full composed-stage behavior is exercised in a separate real-tree test.
        def fake_stage(source, target, *, expected_commit=None):
            target.mkdir(mode=0o700)
            d._copy(source, target)
            d._apply_plain_ui_recovery(source, target)
            hashes = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in target.rglob("*") if p.is_file()}
            manifest = {"status": "SHADOW_REVIEW_ONLY", "files_sha256": hashes}
            (target / d.STAGE_MANIFEST).write_text(json.dumps(manifest))
            return d._verify_stage(target)
        self.stage_patch = mock.patch.object(d, "_stage_integrated_runtime", side_effect=fake_stage)
        for patch in (self.source_patch, self.stop_patch, self.selftest_patch, self.stage_patch):
            patch.start()
            self.addCleanup(patch.stop)

    def _run(self):
        return d.deploy(self.checkout, home=self.home, private=self.private,
                        builds=self.builds, ci_verified=True)

    def test_switches_actual_launcher_with_full_canon_and_preserves_userdata(self):
        first = self._run()
        self.assertEqual(first["status"], "DEPLOYED")
        path = Path(first["code"])
        self.assertTrue((path / d.CANON).is_file())
        self.assertIn(str(path).encode(), self.launcher.read_bytes())
        self.assertIn(b'--home', self.launcher.read_bytes())
        self.assertEqual((self.home/"models/model.gguf").read_bytes(), b"GGUF_NOT_A_REAL_MODEL")
        self.assertEqual((self.home/"data/db/brain.sqlite3").read_bytes(), b"EXISTING_DB_DO_NOT_CHANGE")
        self.assertEqual((self.home/"config/settings.json").read_text(), '{"threads":4}')
        self.assertEqual(self._run()["status"], "UP_TO_DATE")
        marker = json.loads((self.private/d.MARKER_NAME).read_text())
        self.assertEqual(marker["commit"], self.commit)
        self.assertEqual(marker["build_profile"], d.BUILD_PROFILE)
        self.assertEqual(marker["source_ui_sha256"], d.UI_SOURCE_SHA256)
        self.assertEqual(marker["derived_ui_sha256"], d.UI_DERIVED_SHA256)
        self.assertEqual(marker["ui_builder_sha256"], d.UI_BUILDER_SHA256)
        self.assertEqual(hashlib.sha256(self.launcher.read_bytes()).hexdigest(), marker["launcher_sha256"])
        self.assertEqual(Path(marker["backup_launcher"]).read_bytes(), self.old)

    @staticmethod
    def render_persisted_history(raw):
        """Run the real plain renderer with persisted history and no model."""
        ui = types.ModuleType("v13.deployment_ui_counterexample")
        ui.__package__ = "v13"
        exec(compile(raw, "<deployed-ui>", "exec"), ui.__dict__)
        rendered = threading.Event()
        main = threading.current_thread()

        def history(session, count):
            if threading.current_thread() is not main:
                rendered.set()
            return [{"id": 1, "role": "assistant", "text": "persisted previous answer"}]

        runtime = types.SimpleNamespace(store=types.SimpleNamespace(history=history),
                                        session="fixture", stop=threading.Event())

        def read_once(_):
            if not rendered.wait(2):
                raise AssertionError("real plain renderer did not poll")
            runtime.stop.set()
            return ":shutdown"

        output = io.StringIO()
        with mock.patch.object(ui, "Operator") as operator, \
             mock.patch.object(ui, "read_block", side_effect=read_once), \
             mock.patch.object(ui, "typing", return_value=False), redirect_stdout(output):
            operator.return_value.run.return_value = ""
            ui.plain(runtime)
        return output.getvalue()

    def test_real_copied_ui_uses_only_recovery_and_frozen_sources_stay_unchanged(self):
        original_ui = (self.code / d.UI_SOURCE).read_bytes()
        original_operator = (self.code / "v13/operator.py").read_bytes()
        self.assertIn("assistant> persisted previous answer", self.render_persisted_history(original_ui))
        result = self._run()
        deployed = Path(result["code"])
        derived_ui = (deployed / d.UI_SOURCE).read_bytes()
        self.assertEqual(hashlib.sha256(derived_ui).hexdigest(), d.UI_DERIVED_SHA256)
        self.assertNotIn("persisted previous answer", self.render_persisted_history(derived_ui))
        self.assertEqual((self.code / d.UI_SOURCE).read_bytes(), original_ui)
        self.assertEqual((self.code / "v13/operator.py").read_bytes(), original_operator)
        self.assertEqual((deployed / "v13/operator.py").read_bytes(), original_operator)
        self.assertEqual((deployed / "v13/runtime.py").read_bytes(),
                         (self.code / "v13/runtime.py").read_bytes())

    def test_launcher_uses_verified_package_from_competing_working_directory(self):
        snapshot = self.root / "verified snapshot"
        verified = snapshot / "v13"
        verified.mkdir(parents=True)
        (verified / "__init__.py").write_text("")
        (verified / "__main__.py").write_text(
            "import json, os, sys\nfrom pathlib import Path\n"
            "proc = Path('/proc/self/cmdline')\n"
            "os_args = [os.fsdecode(arg) for arg in proc.read_bytes().split(bytes(1))] if proc.is_file() else None\n"
            "print(json.dumps({'package': 'verified', 'cwd': os.getcwd(), "
            "'args': sys.argv[1:], 'os_args': os_args}))\n")
        foreign = self.root / "foreign working directory"
        (foreign / "v13").mkdir(parents=True)
        (foreign / "v13" / "__init__.py").write_text("")
        (foreign / "v13" / "__main__.py").write_text("print('FOREIGN PACKAGE')\n")
        (foreign / "sitecustomize.py").write_text(
            "from pathlib import Path\nPath('sitecustomize-ran').write_text('bad')\n")
        for version in ((3, 11), (3, 10)):
            with self.subTest(version=version):
                with mock.patch.object(d.sys, "version_info", version):
                    launcher = d._launcher_bytes(snapshot, self.home)
                self.launcher.write_bytes(launcher)
                # Invoke bash explicitly because the real shebang is the Termux path.
                result = subprocess.run(["bash", str(self.launcher), "restore", "relative backup.zip"],
                                        cwd=foreign, text=True, capture_output=True, check=True)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["package"], "verified")
                self.assertEqual(payload["cwd"], str(foreign))
                self.assertEqual(payload["args"], ["--home", str(self.home),
                                                     "restore", "relative backup.zip"])
                if version == (3, 10) and payload["os_args"] is not None:
                    self.assertIn(str(self.launcher), payload["os_args"])
                self.assertFalse((foreign / "sitecustomize-ran").exists())

    def test_current_commit_raw_profile_is_migrated(self):
        first = self._run()
        old_code = Path(first["code"])
        (old_code / d.UI_SOURCE).write_bytes((self.code / d.UI_SOURCE).read_bytes())
        marker_path = self.private / d.MARKER_NAME
        marker = json.loads(marker_path.read_text())
        for field in ("build_profile", "source_ui_sha256", "derived_ui_sha256", "ui_builder_sha256"):
            marker.pop(field)
        marker_path.write_text(json.dumps(marker))
        self.assertTrue(d.needs_deploy(self.checkout, home=self.home, private=self.private))
        second = self._run()
        self.assertEqual(second["status"], "DEPLOYED")
        self.assertNotEqual(second["code"], first["code"])
        self.assertFalse(d.needs_deploy(self.checkout, home=self.home, private=self.private))
        self.assertEqual((old_code / d.UI_SOURCE).read_bytes(), (self.code / d.UI_SOURCE).read_bytes())

    def test_derived_ui_tampering_requires_redeployment(self):
        result = self._run()
        (Path(result["code"]) / d.UI_SOURCE).write_text("# changed deployed renderer\n")
        self.assertTrue(d.needs_deploy(self.checkout, home=self.home, private=self.private))

    def test_changed_builder_fails_closed_before_selftest_or_launcher_switch(self):
        builder = self.code / d.UI_BUILDER
        builder.write_bytes(builder.read_bytes() + b"\n# changed builder\n")
        with self.assertRaisesRegex(d.RuntimeDeployError, "builder changed"):
            self._run()
        d._selftest.assert_not_called()
        self.assertEqual(self.launcher.read_bytes(), self.old)
        self.assertFalse((self.private / d.MARKER_NAME).exists())

    def test_changed_frozen_ui_input_fails_closed(self):
        ui = self.code / d.UI_SOURCE
        ui.write_bytes(ui.read_bytes() + b"\n# changed frozen input\n")
        with self.assertRaisesRegex(d.RuntimeDeployError, "source validation failed"):
            self._run()
        self.assertEqual(self.launcher.read_bytes(), self.old)

    def test_marker_write_failure_restores_original_launcher(self):
        write = d._atomic_file

        def fail_marker(dest, data, mode=0o600):
            if dest == self.private / d.MARKER_NAME:
                raise OSError("injected marker write failure")
            return write(dest, data, mode)

        with mock.patch.object(d, "_atomic_file", side_effect=fail_marker):
            with self.assertRaises(OSError):
                self._run()
        self.assertEqual(self.launcher.read_bytes(), self.old)
        self.assertFalse((self.private / d.MARKER_NAME).exists())

    def test_staging_failure_retains_old_launcher_and_memory(self):
        with mock.patch.object(d, "_selftest", side_effect=d.RuntimeDeployError("broken staged runtime")):
            with self.assertRaises(d.RuntimeDeployError):
                self._run()
        self.assertEqual(self.launcher.read_bytes(), self.old)
        self.assertEqual((self.home/"data/db/brain.sqlite3").read_bytes(), b"EXISTING_DB_DO_NOT_CHANGE")

    def test_active_runtime_blocks_before_switch(self):
        with mock.patch.object(d, "_check_stopped", side_effect=d.RuntimeDeployError("running")):
            with self.assertRaises(d.RuntimeDeployError):
                self._run()
        self.assertEqual(self.launcher.read_bytes(), self.old)

    def test_symlink_launcher_rejected(self):
        self.launcher.unlink()
        self.launcher.symlink_to(self.home / "config/settings.json")
        with self.assertRaises(d.RuntimeDeployError):
            self._run()
        self.assertEqual((self.home/"config/settings.json").read_text(), '{"threads":4}')

    def test_unverified_ci_never_switches_launcher(self):
        with mock.patch("v13.source_updater.ci_passed", return_value=False):
            with self.assertRaises(d.RuntimeDeployError):
                d.deploy(self.checkout, home=self.home, private=self.private,
                         builds=self.builds)
        self.assertEqual(self.launcher.read_bytes(), self.old)

    def test_pipeline_cannot_activate_a_different_commit_than_ci_checked(self):
        with self.assertRaisesRegex(d.RuntimeDeployError, "changed after CI verification"):
            d.deploy(self.checkout, home=self.home, private=self.private,
                     builds=self.builds, ci_verified=True, expected_commit="e" * 40)
        self.assertEqual(self.launcher.read_bytes(), self.old)

    def test_confirmed_auto_off_prevents_activation_after_staging(self):
        from v13 import pipeline_agent as pipeline

        ready = threading.Event()
        resume = threading.Event()
        failures = []

        def pause_before_activation(_path):
            ready.set()
            if not resume.wait(5):
                raise RuntimeError("test did not resume activation")

        def auto_update():
            try:
                d.deploy(self.checkout, home=self.home, private=self.private,
                         builds=self.builds, ci_verified=True,
                         activation_guard=pipeline._auto_activation)
            except Exception as exc:
                failures.append(exc)

        with mock.patch.object(pipeline, "PRIVATE", self.private), \
             mock.patch.object(pipeline, "ENABLED", self.private / "auto-source-update.enabled"):
            self.assertTrue(pipeline.set_enabled(True))
            with mock.patch.object(d, "_selftest", side_effect=pause_before_activation):
                worker = threading.Thread(target=auto_update)
                worker.start()
                try:
                    self.assertTrue(ready.wait(5))
                    self.assertFalse(pipeline.set_enabled(False))
                finally:
                    resume.set()
                    worker.join(10)
            self.assertFalse(worker.is_alive())
            self.assertEqual([type(exc) for exc in failures], [pipeline.AutoUpdateDisabled])
            self.assertEqual(self.launcher.read_bytes(), self.old)
            self.assertFalse((self.private / d.MARKER_NAME).exists())
            self.assertEqual(self._run()["status"], "DEPLOYED")
            self.assertFalse(pipeline.enabled())


class RuntimeSourcePreparationTests(unittest.TestCase):
    """Real Git fixtures exercise old/missing checkouts, without network."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.seed = self.base / "release"
        self.seed.mkdir()
        self.git(self.seed, "init", "--initial-branch=" + d.SOURCE_BRANCH)
        self.git(self.seed, "config", "user.name", "Synthetic fixture")
        self.git(self.seed, "config", "user.email", "fixture@example.invalid")
        self.git(self.seed, "remote", "add", "origin", d.REPO_ORIGIN[1])
        for rel in d.REQUIRED:
            target = self.seed / "v13/code" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# synthetic source fixture\n")
        self.git(self.seed, "add", ".")
        self.git(self.seed, "commit", "-m", "Synthetic runtime release")
        self.target = self.base / "runtime-source"

    @staticmethod
    def git(root, *args):
        return subprocess.run(["git", "-C", str(root), *args],
                              capture_output=True, text=True, check=True).stdout.strip()

    def local_clones(self):
        real_run = subprocess.run
        def run(args, **kwargs):
            if args[:2] == ["git", "clone"]:
                self.assertEqual(args[-2], d.REPO_ORIGIN[1])
                proc = real_run([*args[:-2], str(self.seed), args[-1]], **kwargs)
                if proc.returncode == 0:
                    real_run(["git", "-C", args[-1], "remote", "set-url", "origin",
                              d.REPO_ORIGIN[1]], check=True, capture_output=True)
                return proc
            return real_run(args, **kwargs)
        return mock.patch.object(d.subprocess, "run", side_effect=run)

    def test_missing_runtime_checkout_is_prepared_on_fixed_release(self):
        with self.local_clones():
            result = d.prepare_source(self.target)
        self.assertEqual(result["status"], "CREATED")
        self.assertEqual(result["commit"], self.git(self.seed, "rev-parse", "HEAD"))
        self.assertEqual(self.git(self.target, "branch", "--show-current"), d.SOURCE_BRANCH)
        self.assertEqual(self.git(self.target, "remote", "get-url", "origin"), d.REPO_ORIGIN[1])
        for rel in d.REQUIRED:
            self.assertTrue((self.target / "v13/code" / rel).is_file(), rel)
        self.assertFalse(list(self.base.glob(".v13-source-*")))
        self.assertEqual(d.prepare_source(self.target)["status"], "READY")

    def test_existing_incomplete_sparse_checkout_is_migrated(self):
        with self.local_clones():
            d.prepare_source(self.target)
        self.git(self.target, "sparse-checkout", "set", "--no-cone",
                 "v13/code/v13/common.py")
        self.assertFalse((self.target / "v13/code" / d.CANON).exists())
        previous = self.git(self.target, "rev-parse", "HEAD")
        d.prepare_source(self.target)
        self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), previous)
        self.assertTrue((self.target / "v13/code" / d.CANON).is_file())
        self.assertEqual(self.git(self.target, "status", "--porcelain"), "")

    def test_existing_untrusted_checkout_and_local_edits_are_retained(self):
        with self.local_clones():
            d.prepare_source(self.target)
        path = self.target / "v13/code/v13/common.py"
        path.write_text("# local edit that must survive\n")
        with self.assertRaises(d.RuntimeDeployError):
            d.prepare_source(self.target)
        self.assertIn("must survive", path.read_text())
        self.git(self.target, "restore", ".")
        self.git(self.target, "remote", "set-url", "origin", "https://example.invalid/untrusted.git")
        with self.assertRaises(d.RuntimeDeployError):
            d.prepare_source(self.target)
        self.assertTrue(path.is_file())

    def test_untracked_and_git_ignored_deployable_files_block_without_deleting(self):
        with self.local_clones():
            d.prepare_source(self.target)
        code = self.target / "v13/code"
        # Git ignores this file, but the Canon copy operation would include it.
        with (self.target / ".git/info/exclude").open("a") as out:
            out.write("\nprivate-user-note.txt\n")
        paths = ("v13/untracked.py", "scripts/untracked.py", "specs/untracked.json",
                 "docs/canon/private-user-note.txt")
        for rel in paths:
            with self.subTest(path=rel):
                extra = code / rel
                extra.parent.mkdir(parents=True, exist_ok=True)
                extra.write_text("LOCAL_USER_DATA")
                with self.assertRaisesRegex(d.RuntimeDeployError, "Untracked or ignored"):
                    d._source(self.target)
                self.assertEqual(extra.read_text(), "LOCAL_USER_DATA")
                extra.unlink()  # Only the disposable synthetic fixture.

    def test_excluded_caches_and_models_remain_usable_and_untouched(self):
        with self.local_clones():
            d.prepare_source(self.target)
        code = self.target / "v13/code"
        paths = ("v13/__pycache__/cache.txt", "v13/trace.log",
                 "scripts/model.gguf", "specs/fixture.sqlite",
                 "docs/canon/__pycache__/cache.txt", "docs/canon/cache.pyo")
        for rel in paths:
            entry = code / rel
            entry.parent.mkdir(parents=True, exist_ok=True)
            entry.write_text("PRESERVE")
        d._source(self.target)
        for rel in paths:
            self.assertEqual((code / rel).read_text(), "PRESERVE")

    def test_untracked_source_cannot_switch_existing_launcher(self):
        with self.local_clones():
            d.prepare_source(self.target)
        extra = self.target / "v13/code/v13/untracked.py"
        extra.write_text("LOCAL_USER_DATA")
        home = self.base / "phone"
        (home / "bin").mkdir(parents=True)
        launcher = home / "bin/v13"
        launcher.write_text("OLD_LAUNCHER")
        with mock.patch.object(d, "_stage_integrated_runtime") as stage:
            with self.assertRaisesRegex(d.RuntimeDeployError, "Untracked or ignored"):
                d.deploy(self.target, home=home, private=self.base / "private",
                         builds=self.base / "builds", ci_verified=True)
        stage.assert_not_called()
        self.assertEqual(launcher.read_text(), "OLD_LAUNCHER")
        self.assertEqual(extra.read_text(), "LOCAL_USER_DATA")

    def test_file_inserted_after_source_check_cannot_enter_stage(self):
        # A tiny trusted test stager simulates a file appearing after _source().
        builder = self.seed / "v13/code" / d.STAGER
        builder.parent.mkdir(parents=True, exist_ok=True)
        builder.write_text("""
import hashlib
from pathlib import Path
import shutil
def stage(source, target):
    source, target = Path(source), Path(target)
    target.mkdir(parents=True)
    for name in ('v13', 'scripts', 'specs'):
        shutil.copytree(source / name, target / name)
    hashes = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in target.rglob('*') if p.is_file()}
    return {'status': 'SHADOW_REVIEW_ONLY', 'replaced_files': [], 'files_sha256': hashes}
""")
        self.git(self.seed, "add", "v13/code/" + d.STAGER)
        self.git(self.seed, "commit", "-m", "Add synthetic staging fixture")
        with self.local_clones():
            d.prepare_source(self.target)
        _, code, _ = d._source(self.target)
        extra = code / "v13/arrived_during_copy.py"
        extra.write_text("LOCAL_USER_DATA")
        target = self.base / "built" / "code"
        with mock.patch.object(d, "STAGER_SHA256", hashlib.sha256(builder.read_bytes()).hexdigest()):
            d._stage_integrated_runtime(code, target)
        self.assertFalse((target / "v13/arrived_during_copy.py").exists())
        self.assertEqual(extra.read_text(), "LOCAL_USER_DATA")

    def test_tracked_worktree_race_cannot_change_source_or_generated_stage(self):
        # The pinned synthetic builder changes the checkout while constructing
        # both a normal file and a generated file from its supplied inputs.
        builder = self.seed / "v13/code" / d.STAGER
        builder.parent.mkdir(parents=True, exist_ok=True)
        builder.write_text("""
import hashlib, os, shutil
from pathlib import Path
def stage(source, target):
    source, target = Path(source), Path(target)
    worktree = Path(os.environ['V13_TEST_MUTABLE_CHECKOUT']) / 'v13/code/v13/common.py'
    old = worktree.read_bytes()
    try:
        worktree.write_bytes(b'CHANGED DURING COPY')
        target.mkdir(parents=True)
        for name in ('v13', 'scripts', 'specs'):
            shutil.copytree(source / name, target / name)
        (target / 'v13/generated.py').write_bytes((source / 'v13/common.py').read_bytes())
    finally:
        worktree.write_bytes(old)
    hashes = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in target.rglob('*') if p.is_file()}
    return {'status': 'SHADOW_REVIEW_ONLY', 'replaced_files': ['v13/generated.py'], 'files_sha256': hashes}
""")
        self.git(self.seed, "add", "v13/code/" + d.STAGER)
        self.git(self.seed, "commit", "-m", "Add deterministic racing stager")
        with self.local_clones():
            d.prepare_source(self.target)
        _, code, commit = d._source(self.target)
        before = (code / "v13/common.py").read_bytes()
        target = self.base / "built" / "code"
        with mock.patch.object(d, "STAGER_SHA256", hashlib.sha256(builder.read_bytes()).hexdigest()), \
             mock.patch.dict("os.environ", {"V13_TEST_MUTABLE_CHECKOUT": str(self.target)}):
            d._stage_integrated_runtime(code, target, expected_commit=commit)
        self.assertEqual((target / "v13/common.py").read_bytes(), before)
        self.assertEqual((target / "v13/generated.py").read_bytes(), before)
        self.assertEqual((code / "v13/common.py").read_bytes(), before)
        self.assertEqual(self.git(self.target, "status", "--porcelain"), "")
        self.assertEqual(json.loads((target / d.STAGE_MANIFEST).read_text())["source_commit"], commit)

    def test_self_consistent_manifest_cannot_hide_changed_tracked_blob(self):
        # A malicious/broken builder emits a changed tracked file and a
        # matching manifest but does not declare it as a generated output.
        builder = self.seed / "v13/code" / d.STAGER
        builder.parent.mkdir(parents=True, exist_ok=True)
        builder.write_text("""
import hashlib, shutil
from pathlib import Path
def stage(source, target):
    source, target = Path(source), Path(target)
    target.mkdir(parents=True)
    for name in ('v13', 'scripts', 'specs'):
        shutil.copytree(source / name, target / name)
    (target / 'v13/common.py').write_bytes(b'CHANGED DURING COPY')
    hashes = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in target.rglob('*') if p.is_file()}
    return {'status': 'SHADOW_REVIEW_ONLY', 'replaced_files': [], 'files_sha256': hashes}
""")
        self.git(self.seed, "add", "v13/code/" + d.STAGER)
        self.git(self.seed, "commit", "-m", "Add broken stager")
        with self.local_clones():
            d.prepare_source(self.target)
        _, code, commit = d._source(self.target)
        with mock.patch.object(d, "STAGER_SHA256", hashlib.sha256(builder.read_bytes()).hexdigest()):
            with self.assertRaisesRegex(d.RuntimeDeployError, "differs from Git commit"):
                d._stage_integrated_runtime(code, self.base / "built" / "code", expected_commit=commit)

    def test_explicit_commit_is_used_if_checkout_head_advances(self):
        builder = self.seed / "v13/code" / d.STAGER
        builder.parent.mkdir(parents=True, exist_ok=True)
        builder.write_text("""
import hashlib, shutil
from pathlib import Path
def stage(source, target):
    source, target = Path(source), Path(target)
    target.mkdir(parents=True)
    for name in ('v13', 'scripts', 'specs'):
        shutil.copytree(source / name, target / name)
    hashes = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in target.rglob('*') if p.is_file()}
    return {'status': 'SHADOW_REVIEW_ONLY', 'replaced_files': [], 'files_sha256': hashes}
""")
        self.git(self.seed, "add", "v13/code/" + d.STAGER)
        self.git(self.seed, "commit", "-m", "Add pinned stager")
        with self.local_clones():
            d.prepare_source(self.target)
        _, code, original_commit = d._source(self.target)
        original = (code / "v13/common.py").read_bytes()
        self.git(self.target, "config", "user.name", "Synthetic fixture")
        self.git(self.target, "config", "user.email", "fixture@example.invalid")
        (code / "v13/common.py").write_text("newer source\n")
        self.git(self.target, "add", "v13/code/v13/common.py")
        self.git(self.target, "commit", "-m", "Move checkout head")
        target = self.base / "built" / "code"
        with mock.patch.object(d, "STAGER_SHA256", hashlib.sha256(builder.read_bytes()).hexdigest()):
            d._stage_integrated_runtime(code, target, expected_commit=original_commit)
        self.assertEqual((target / "v13/common.py").read_bytes(), original)
        self.assertEqual((code / "v13/common.py").read_text(), "newer source\n")
        self.assertEqual(json.loads((target / d.STAGE_MANIFEST).read_text())["source_commit"], original_commit)

    def test_failed_download_removes_only_owned_staging_directory(self):
        sentinel = self.base / "existing-user-data"
        sentinel.write_text("preserve")
        with mock.patch.object(d.subprocess, "run", return_value=mock.Mock(returncode=1)):
            with self.assertRaises(d.RuntimeDeployError):
                d.prepare_source(self.target)
        self.assertFalse(self.target.exists())
        self.assertFalse(list(self.base.glob(".v13-source-*")))
        self.assertEqual(sentinel.read_text(), "preserve")

    def test_symlink_source_is_refused_without_modifying_target(self):
        self.target.symlink_to(self.seed, target_is_directory=True)
        before = self.git(self.seed, "rev-parse", "HEAD")
        with self.assertRaises(d.RuntimeDeployError):
            d.prepare_source(self.target)
        self.assertEqual(self.git(self.seed, "rev-parse", "HEAD"), before)



class RealRuntimeSelftestDiagnosticsTests(unittest.TestCase):
    """Fail closed and report only fixed phase, exit and exception class."""

    def test_missing_sqlite_reports_phase_without_private_stderr(self):
        raw = (b'Traceback: private=/data/data/com.termux/files/home/token\n'
               b"ModuleNotFoundError: No module named 'sqlite3'\n")
        failed = subprocess.CompletedProcess(['python', '-m', 'v13'], 1,
                                             stdout=b'', stderr=raw)
        with mock.patch.object(d.subprocess, "run", return_value=failed):
            with self.assertRaises(d.RuntimeDeployError) as cm:
                d._selftest(Path('/nonexistent-staged-code'))
        result = str(cm.exception)
        self.assertIn('phase=module_help', result)
        self.assertIn('error=ModuleNotFoundError(sqlite3)', result)
        self.assertIn('exit=1', result)
        self.assertNotIn('token', result)
        self.assertNotIn('/data/data/', result)

    def test_second_phase_reports_sqlite_error_class_without_raw_trace(self):
        ok = subprocess.CompletedProcess(['python', '-m', 'v13'], 0,
                                         stdout=b'ok', stderr=b'')
        broken = subprocess.CompletedProcess(['python', '-c', 'script'], 2,
                                             stdout=b'', stderr=(
                                                 b'Traceback: local secret 123\n'
                                                 b'sqlite3.OperationalError: readonly database\n'))
        with mock.patch.object(d.subprocess, "run", side_effect=(ok, broken)):
            with self.assertRaises(d.RuntimeDeployError) as cm:
                d._selftest(Path('/nonexistent-staged-code'))
        result = str(cm.exception)
        self.assertIn('phase=sqlite_source_roundtrip', result)
        self.assertIn('error=sqlite3.OperationalError', result)
        self.assertNotIn('readonly database', result)
        self.assertNotIn('local secret', result)

    def test_permission_error_reports_allowlisted_site_and_errno_only(self):
        good = subprocess.CompletedProcess(['python', '-m', 'v13'], 0,
                                           stdout=b'ok', stderr=b'')
        denied = subprocess.CompletedProcess(
            ['python', '-c', 'probe'], 1, stdout=b'',
            stderr=(b'Traceback: PRIVATE TEXT and /data/data/com.termux/secret\n'
                    b'V13_PROBE_LOCATION=source_lifecycle_candidate._rename_named_no_replace:174:13\n'
                    b'PermissionError: /data/data/com.termux/very_private_path\n'))
        with mock.patch.object(d.subprocess, 'run', side_effect=(good, denied)):
            with self.assertRaises(d.RuntimeDeployError) as cm:
                d._selftest(Path('/nonexistent-staged-code'))
        message = str(cm.exception)
        self.assertIn('error=PermissionError', message)
        self.assertIn('site=source_lifecycle_candidate._rename_named_no_replace:174', message)
        self.assertIn('errno=13', message)
        self.assertNotIn('/data/data/com.termux', message)
        self.assertNotIn('PRIVATE TEXT', message)

    def test_untrusted_site_marker_is_never_reflected(self):
        good = subprocess.CompletedProcess(['python', '-m', 'v13'], 0,
                                           stdout=b'ok', stderr=b'')
        denied = subprocess.CompletedProcess(
            ['python', '-c', 'probe'], 1, stdout=b'',
            stderr=(b'V13_PROBE_LOCATION=../../secret.private:42:13\n'
                    b'PermissionError: private-path\n'))
        with mock.patch.object(d.subprocess, 'run', side_effect=(good, denied)):
            with self.assertRaises(d.RuntimeDeployError) as cm:
                d._selftest(Path('/nonexistent-staged-code'))
        message = str(cm.exception)
        self.assertIn('error=PermissionError', message)
        self.assertNotIn('site=', message)
        self.assertNotIn('private-path', message)
        self.assertNotIn('secret', message)

    def test_signal_like_exit_remains_a_failed_selftest(self):
        killed = subprocess.CompletedProcess(['python', '-m', 'v13'], -9,
                                             stdout=b'', stderr=b'')
        with mock.patch.object(d.subprocess, "run", return_value=killed):
            with self.assertRaisesRegex(d.RuntimeDeployError, r'exit=-9'):
                d._selftest(Path('/nonexistent-staged-code'))


if __name__ == "__main__":
    unittest.main()
