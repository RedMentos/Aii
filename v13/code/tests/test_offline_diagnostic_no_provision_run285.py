"""Run285: extracted-phone ZIP source-only diagnostics never provision packages.

Linux-software tests with a simulated Termux PREFIX and explicit pkg/pip
sentinels. They are not native model inference or Redmi measurements.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from scripts.package_source import package
from scripts.verify_phone_zip_current_run268 import verify


class Run285OfflineNoProvision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.source = Path(__file__).resolve().parents[1]
        cls.zip_path = cls.root / "V13-Phone.zip"
        package(cls.source, cls.zip_path, phone_install=True)
        cls.report = verify(cls.zip_path, cls.source)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def make_app(self, label):
        target = self.root / label
        with zipfile.ZipFile(self.zip_path) as z:
            z.extractall(target)
        return target / "V13-Phone"

    def run_diagnostic(self, label, *, no_numpy=False, tamper=False):
        app = self.make_app(label)
        if tamper:
            with (app / "v13/memory.py").open("ab") as f:
                f.write(b"\n# run285 tamper control\n")
        sentinel = self.root / (label + "-sentinels")
        sentinel.mkdir()
        marker = sentinel / "provision-attempted"
        python_shim = sentinel / "python3"
        real_python = str(Path(sys.executable))
        # The actual Python is the isolated CI venv. Fail if the setup ever
        # tries Python -m pip, even if the requested package is already cached.
        python_shim.write_text(
            "#!/bin/sh\n"
            "for arg in \"$@\"; do\n"
            "  if [ \"$arg\" = pip ]; then\n"
            "    printf pip >> " + repr(str(marker)) + "\n"
            "    exit 93\n"
            "  fi\n"
            "done\n"
            + (
                "if [ \"$1\" = -c ] && [ \"$2\" = 'import numpy' ]; then exit 92; fi\n"
                if no_numpy else ""
            )
            + "exec " + repr(real_python) + " \"$@\"\n"
        )
        python_shim.chmod(0o700)
        pkg = sentinel / "pkg"
        pkg.write_text("#!/bin/sh\nprintf pkg >> " + repr(str(marker)) + "\nexit 94\n")
        pkg.chmod(0o700)
        prefix = self.root / (label + "-com.termux/files/usr")
        (prefix / "bin").mkdir(parents=True)
        home = self.root / (label + "-home")
        env = os.environ.copy()
        env.update(
            PATH=str(sentinel) + os.pathsep + env.get("PATH", ""),
            PREFIX=str(prefix),
            V13_HOME=str(home),
            V13_NO_AUTOSTART="1",
            V13_SOURCE_ONLY_DIAGNOSTIC="1",
            PIP_NO_INDEX="1",
            PIP_DISABLE_PIP_VERSION_CHECK="1",
            NEEDLE_TELEMETRY="0",
            DO_NOT_TRACK="1",
        )
        p = subprocess.run(
            ["bash", "setup.sh"], cwd=app, env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90,
        )
        return p, home, marker, prefix

    def test_simulated_termux_offline_success_without_pkg_or_pip(self):
        p, home, marker, prefix = self.run_diagnostic("positive")
        self.assertEqual(p.returncode, 0, p.stdout[-5000:])
        self.assertIn("SOURCE_ONLY_DIAGNOSTIC", p.stdout)
        self.assertIn("NO_NATIVE_MODEL / NO_REDMi / NO_JEPA_PROOF", p.stdout)
        self.assertIn("STEP2=UTILITY_FAIL B3_L1=FAIL", p.stdout)
        self.assertFalse(marker.exists(), p.stdout)
        self.assertTrue((home / "bin/v13").is_file())
        self.assertTrue((prefix / "bin/v13").is_symlink())
        self.assertFalse((home / "bin/llama-server").exists())
        self.assertEqual(list(home.rglob("*.gguf")), [])

    def test_missing_numpy_refuses_without_attempting_install(self):
        p, home, marker, _ = self.run_diagnostic("missing-numpy", no_numpy=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("numpy fehlt", p.stdout)
        self.assertFalse(marker.exists(), p.stdout)
        self.assertFalse((home / "bin/v13").exists())

    def test_tampered_source_refused_before_pkg_pip_and_state(self):
        p, home, marker, _ = self.run_diagnostic("tampered", tamper=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("SOURCE_HASH_MISMATCH", p.stdout.upper())
        self.assertFalse(marker.exists(), p.stdout)
        self.assertFalse((home / "bin/v13").exists())

    def test_normal_installer_paths_remain_present(self):
        script = (self.source / "setup.sh").read_text()
        self.assertIn("pkg install -y python python-numpy", script)
        self.assertIn('"$V13_PYTHON" -m v13.bootstrap --home "$V13_DATA_HOME"', script)
        self.assertIn('"$V13_DATA_HOME/bin/v13" selftest', script)
        self.assertIn('"$V13_DATA_HOME/bin/v13" probe', script)
        self.assertEqual(
            subprocess.run(["bash", "-n", str(self.source / "setup.sh")]).returncode, 0
        )


if __name__ == "__main__":
    unittest.main()
