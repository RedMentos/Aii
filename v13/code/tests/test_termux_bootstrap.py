"""Exercise the real Termux bootstrap against isolated local Git fixtures.

Package installation and GitHub auth are inert stubs. Fetches use a local bare
repository; tests never contact GitHub, launch a dashboard or signal device jobs.
"""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/termux_one_command.sh"
BRANCH = "gpt6/v13-private-remote-bridge-20261111"
SOURCE = "https://github.com/RedMentos/Aii.git"
REAL_GIT = shutil.which("git")


def git(root, *args):
    result = subprocess.run([REAL_GIT, "-C", str(root), *args], check=True,
                            capture_output=True, text=True)
    return result.stdout.strip()


class TermuxBootstrapTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp = Path(directory.name)
        self.home = self.tmp / "home"
        self.home.mkdir(mode=0o700)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.remote = self.tmp / "remote.git"
        self.publisher = self.tmp / "publisher"
        self.phone = self.home / ".v13-agent-source"
        self.calls = self.tmp / "git-calls.jsonl"
        self.gh_calls = self.tmp / "gh-calls"
        subprocess.run([REAL_GIT, "init", "--bare", str(self.remote)],
                       capture_output=True, check=True)
        subprocess.run([REAL_GIT, "clone", str(self.remote), str(self.publisher)],
                       capture_output=True, check=True)
        git(self.publisher, "config", "user.name", "Bootstrap Tests")
        git(self.publisher, "config", "user.email", "bootstrap@example.invalid")
        git(self.publisher, "checkout", "-b", BRANCH)
        source = self.publisher / "v13/code/v13"
        source.mkdir(parents=True)
        (source / "owner_read_bridge.py").write_text("# local source fixture\n")
        (source / "__init__.py").write_text("")
        git(self.publisher, "add", ".")
        git(self.publisher, "commit", "-m", "initial source")
        git(self.publisher, "push", "-u", "origin", BRANCH)
        subprocess.run([REAL_GIT, "clone", "--branch", BRANCH,
                        str(self.remote), str(self.phone)],
                       capture_output=True, check=True)
        git(self.phone, "remote", "set-url", "origin", SOURCE)
        git(self.phone, "config", "user.name", "Bootstrap Tests")
        git(self.phone, "config", "user.email", "bootstrap@example.invalid")
        self.initial = git(self.phone, "rev-parse", "HEAD")
        self._stub("pkg", "#!/bin/sh\nexit 0\n")
        self._stub("gh", '#!/bin/sh\nprintf "%s\\n" "$*" >> "$BOOTSTRAP_GH_CALLS"\nexit 1\n')
        self._stub("git", "#!" + sys.executable + "\n" + '''import json, os, subprocess, sys
from pathlib import Path
args = sys.argv[1:]
with open(os.environ["BOOTSTRAP_GIT_CALLS"], "a") as out:
    out.write(json.dumps(args) + "\\n")
if "clone" in args:
    raise SystemExit("unexpected clone; network forbidden in bootstrap tests")
if "fetch" in args:
    stopped_pid = os.environ.get("BOOTSTRAP_EXPECT_STOPPED_PID")
    if stopped_pid:
        try:
            state = (Path("/proc") / stopped_pid / "stat").read_text().rsplit(")", 1)[1].strip()
        except FileNotFoundError:
            state = "Z"
        if not state.startswith("Z"):
            raise SystemExit("source fetch started while old dashboard was alive")
    args[args.index("origin")] = os.environ["BOOTSTRAP_LOCAL_REMOTE"]
raise SystemExit(subprocess.run([os.environ["BOOTSTRAP_REAL_GIT"], *args]).returncode)
''')
        (self.bin / "python").symlink_to(sys.executable)
        self.env = dict(os.environ, HOME=str(self.home),
                        PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                        PREFIX=str(self.tmp / "prefix"),
                        BOOTSTRAP_GIT_CALLS=str(self.calls),
                        BOOTSTRAP_GH_CALLS=str(self.gh_calls),
                        BOOTSTRAP_LOCAL_REMOTE=str(self.remote),
                        BOOTSTRAP_REAL_GIT=REAL_GIT,
                        PYTHONDONTWRITEBYTECODE="1", GIT_TERMINAL_PROMPT="0")

    def _stub(self, name, text):
        path = self.bin / name
        path.write_text(text)
        path.chmod(0o700)

    def run_bootstrap(self):
        return subprocess.run(["bash", str(SCRIPT)], env=self.env,
                              capture_output=True, text=True, timeout=15)

    def operations(self):
        return ([json.loads(line) for line in self.calls.read_text().splitlines()]
                if self.calls.exists() else [])

    def assert_no_source_update(self):
        self.assertFalse(any("fetch" in args or "merge" in args or "checkout" in args
                             for args in self.operations()), self.operations())
        self.assertEqual(git(self.phone, "rev-parse", "HEAD"), self.initial)
        self.assertFalse(self.gh_calls.exists())

    def publish(self):
        source = self.publisher / "v13/code/v13/owner_read_bridge.py"
        source.write_text("# updated local fixture\n")
        git(self.publisher, "add", ".")
        git(self.publisher, "commit", "-m", "new source")
        git(self.publisher, "push", "origin", BRANCH)
        return git(self.publisher, "rev-parse", "HEAD")

    def start_fake_dashboard(self, *, with_child):
        app = self.tmp / "dashboard-app"
        package = app / "v13"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("")
        (package / "mobile_dashboard.py").write_text('''import json, os, subprocess, sys, time
from pathlib import Path
child = (subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
         if os.environ.get("BOOTSTRAP_FAKE_CHILD") == "1" else None)
Path(os.environ["BOOTSTRAP_FAKE_READY"]).write_text(json.dumps(
    {"parent": os.getpid(), "child": None if child is None else child.pid}))
while True:
    Path(os.environ["BOOTSTRAP_FAKE_HEARTBEAT"]).write_text(str(time.monotonic_ns()))
    time.sleep(.03)
''')
        ready = self.tmp / "dashboard-ready.json"
        heartbeat = self.tmp / "dashboard-heartbeat"
        env = dict(self.env, PYTHONPATH=str(app), BOOTSTRAP_FAKE_CHILD=str(int(with_child)),
                   BOOTSTRAP_FAKE_READY=str(ready), BOOTSTRAP_FAKE_HEARTBEAT=str(heartbeat))
        process = subprocess.Popen([sys.executable, "-m", "v13.mobile_dashboard", "ui"],
                                   cwd=app, env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        child_pid = None

        def cleanup():
            # These PIDs belong only to this test fixture, never real V13 jobs.
            if process.poll() is None:
                process.send_signal(signal.SIGCONT)
                process.terminate()
            process.wait(timeout=5)
            if child_pid is not None:
                try:
                    os.kill(child_pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass

        self.addCleanup(cleanup)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if ready.exists() and heartbeat.exists() and ready.stat().st_size:
                try:
                    details = json.loads(ready.read_text())
                except ValueError:
                    continue
                child_pid = details["child"]
                return process, child_pid, heartbeat
            if process.poll() is not None:
                self.fail("fake dashboard exited before startup")
            time.sleep(.01)
        self.fail("fake dashboard did not become ready")

    def test_idle_dashboard_is_stopped_before_source_fetch(self):
        dashboard, child, _ = self.start_fake_dashboard(with_child=False)
        self.assertIsNone(child)
        self.env["BOOTSTRAP_EXPECT_STOPPED_PID"] = str(dashboard.pid)
        result = self.run_bootstrap()
        self.assertIn("GitHub-Anmeldung abgebrochen", result.stdout + result.stderr)
        dashboard.wait(timeout=5)
        self.assertEqual(dashboard.returncode, -signal.SIGTERM)
        self.assertTrue(any("fetch" in args for args in self.operations()))
        self.assertIn("auth login", self.gh_calls.read_text())

    def test_dashboard_with_child_is_resumed_and_preserved_before_fetch(self):
        dashboard, child, heartbeat = self.start_fake_dashboard(with_child=True)
        self.assertIsNotNone(child)
        result = self.run_bootstrap()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("aktive V13-Sitzung", result.stdout + result.stderr)
        self.assertIsNone(dashboard.poll(), "bootstrap terminated a child-owning dashboard")
        os.kill(child, 0)  # owned child is still running
        child_state = (Path("/proc") / str(child) / "stat").read_text().rsplit(")", 1)[1].strip()
        self.assertFalse(child_state.startswith("Z"), "bootstrap killed the managed child")
        first = heartbeat.read_text()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and heartbeat.read_text() == first:
            time.sleep(.03)
        self.assertNotEqual(heartbeat.read_text(), first, "dashboard remained SIGSTOPped")
        self.assert_no_source_update()

    def test_local_stop_is_preserved_and_requires_explicit_resume(self):
        stop = self.home / ".v13-private/bridge-state/STOP"
        stop.parent.mkdir(parents=True, mode=0o700)
        stop.write_text("local stop\n")
        result = self.run_bootstrap()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("resume", result.stdout + result.stderr)
        self.assertNotIn("PRIVATE BRIDGE: STARTED", result.stdout)
        self.assertEqual(stop.read_text(), "local stop\n")
        self.assert_no_source_update()

    def test_active_v13_is_preserved_before_fetch_or_dashboard_cleanup(self):
        process = subprocess.Popen([sys.executable, "-c",
                                    "import time; time.sleep(30)", "v13"])
        try:
            result = self.run_bootstrap()
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("V13 beenden", result.stdout + result.stderr)
            self.assertIsNone(process.poll(), "bootstrap signalled the active V13 fixture")
            self.assert_no_source_update()
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=5)

    def test_new_command_stops_verified_chat_and_records_auto_resume(self):
        launcher = self.home / "v13/bin/v13"
        launcher.parent.mkdir(parents=True)
        launcher.write_text(
            "#!" + sys.executable + "\n"
            "import signal, sys, time\n"
            "signal.signal(signal.SIGINT, lambda *args: sys.exit(0))\n"
            "signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))\n"
            "while True: time.sleep(.05)\n"
        )
        launcher.chmod(0o700)
        proc = subprocess.Popen([str(launcher), "chat", "--plain"],
                                env=self.env, start_new_session=True)
        try:
            time.sleep(.15)
            self.assertIsNone(proc.poll())
            result = self.run_bootstrap()
            proc.wait(timeout=3)
            self.assertIsNotNone(proc.returncode)
            self.assertIn("automatischer Neustart", result.stdout+result.stderr)
            marker = self.home/".v13-private/v13-lifecycle-resume.json"
            payload = json.loads(marker.read_text())
            self.assertEqual(payload["reason"],"INSTALL")
            self.assertEqual(payload["schema"],"v13.lifecycle.resume/1")
            self.assertTrue(any("fetch" in args for args in self.operations()))
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=3)

    def test_unexpected_origin_is_refused_before_fetch(self):
        git(self.phone, "remote", "set-url", "origin", "https://example.invalid/other.git")
        result = self.run_bootstrap()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_no_source_update()

    def test_unexpected_branch_is_refused_before_fetch(self):
        git(self.phone, "checkout", "-b", "unrelated-local-branch")
        result = self.run_bootstrap()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_no_source_update()
        self.assertEqual(git(self.phone, "branch", "--show-current"), "unrelated-local-branch")

    def test_dirty_tracked_source_is_not_overwritten(self):
        path = self.phone / "v13/code/v13/owner_read_bridge.py"
        path.write_text("# owner local edits\n")
        result = self.run_bootstrap()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_no_source_update()
        self.assertEqual(path.read_text(), "# owner local edits\n")

    def test_divergent_history_preserves_local_commit(self):
        self.publish()
        local = self.phone / "owner-local-file"
        local.write_text("preserve local history\n")
        git(self.phone, "add", ".")
        git(self.phone, "commit", "-m", "owner local commit")
        local_head = git(self.phone, "rev-parse", "HEAD")
        result = self.run_bootstrap()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(git(self.phone, "rev-parse", "HEAD"), local_head)
        self.assertEqual(local.read_text(), "preserve local history\n")
        self.assertFalse(self.gh_calls.exists())
        self.assertTrue(any("fetch" in args for args in self.operations()))
        self.assertFalse(any("reset" in args or "checkout" in args for args in self.operations()))

    def test_fast_forward_reaches_auth_gate_without_resetting_branch(self):
        updated = self.publish()
        result = self.run_bootstrap()
        # The intentional auth stub stops execution before all private/device work.
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("GitHub-Anmeldung abgebrochen", result.stdout + result.stderr)
        self.assertEqual(git(self.phone, "rev-parse", "HEAD"), updated)
        self.assertEqual(git(self.phone, "branch", "--show-current"), BRANCH)
        self.assertIn("auth login", self.gh_calls.read_text())
        self.assertTrue(any("merge" in args and "--ff-only" in args
                            for args in self.operations()))
        self.assertFalse(any("reset" in args or "checkout" in args for args in self.operations()))

    def test_shallow_install_fast_forwards_across_multiple_new_commits(self):
        # A filesystem-path clone ignores --depth; file:// exercises the real
        # shallow history created by the phone's initial --depth 1 installation.
        shutil.rmtree(self.phone)
        subprocess.run([REAL_GIT, "clone", "--depth", "1", "--branch", BRANCH,
                        self.remote.as_uri(), str(self.phone)],
                       capture_output=True, check=True)
        self.assertEqual(git(self.phone, "rev-parse", "--is-shallow-repository"), "true")
        self.assertEqual(git(self.phone, "rev-list", "--count", "HEAD"), "1")
        git(self.phone, "remote", "set-url", "origin", SOURCE)
        self.env["BOOTSTRAP_LOCAL_REMOTE"] = self.remote.as_uri()
        self.publish()
        marker = self.publisher / "v13/code/v13/__init__.py"
        marker.write_text("# second upstream commit\n")
        git(self.publisher, "add", ".")
        git(self.publisher, "commit", "-m", "second new source revision")
        git(self.publisher, "push", "origin", BRANCH)
        updated = git(self.publisher, "rev-parse", "HEAD")
        result = self.run_bootstrap()
        self.assertNotEqual(result.returncode, 0)  # intentional auth endpoint
        self.assertIn("GitHub-Anmeldung abgebrochen", result.stdout + result.stderr)
        self.assertEqual(git(self.phone, "rev-parse", "HEAD"), updated)
        self.assertEqual(git(self.phone, "branch", "--show-current"), BRANCH)
        self.assertIn("auth login", self.gh_calls.read_text())
        self.assertTrue(any("merge" in args and "--ff-only" in args
                            for args in self.operations()))
        self.assertFalse(any("reset" in args or "checkout" in args for args in self.operations()))


if __name__ == "__main__":
    unittest.main()
