"""Run22 Linux/software negative controls for the LP3 cgroup join bootstrap.

No real cgroup, native model or production runtime is invoked.  A hostile
PYTHONPATH sitecustomize is a deterministic stand-in for Python startup code
running before the helper can migrate itself into the owned cgroup.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import venv

import lp3_cgroup_v2 as cg


class PrejoinBootstrapTests(unittest.TestCase):
    def test_no_sitecustomize_code_can_run_before_cgroup_join(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            # A fresh private venv with an executable .pth file reproduces
            # Python site startup independently of this host's sitecustomize.
            venv_dir = root / 'venv'
            venv.EnvBuilder(with_pip=False).create(venv_dir)
            py = venv_dir / 'bin' / 'python'
            site_packages = venv_dir / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
            sentinel = root / 'prejoin-startup-executed'
            (site_packages / 'prejoin.pth').write_text(
                "import os; __import__('pathlib').Path(os.environ['LP3_PREJOIN_SENTINEL']).write_text('ran before join')\n")
            fake_group = root / 'no-cgroup'
            fake_group.mkdir()
            marker = root / 'join.json'
            job = object.__new__(cg.CgroupV2Job)
            job.group, job.marker = fake_group, marker
            cmd = job.wrap([sys.executable, '-c', 'print(\"native\")'])
            cmd[0] = str(py)  # identical bootstrap args on an isolated test interpreter
            env = os.environ.copy()
            env['LP3_PREJOIN_SENTINEL'] = str(sentinel)
            # Verify the injected .pth is genuinely active in a normal
            # interpreter; otherwise the negative control proves nothing.
            control = subprocess.run([str(py), '-c', 'pass'], env=env,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     timeout=8, check=False)
            self.assertEqual(control.returncode, 0, control.stderr)
            self.assertTrue(sentinel.exists(), 'startup injection control inactive')
            sentinel.unlink()
            proc = subprocess.run(cmd, env=env, cwd=root,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  timeout=8, check=False)
            # The fake group has no cgroup.procs; the helper must stop before
            # exec, independently of this test's injection control.
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn(b'cgroup.procs', proc.stderr)  # helper itself reached
            self.assertFalse(marker.exists())
            self.assertNotIn(b'native', proc.stdout)
            self.assertFalse(sentinel.exists(),
                             'sitecustomize ran before the helper joined cgroup')

    def test_helper_command_uses_isolated_no_site_interpreter(self):
        job = object.__new__(cg.CgroupV2Job)
        job.group, job.marker = Path('/sys/fs/cgroup/delegated/lp3-active'), Path('/tmp/join-marker')
        cmd = job.wrap([sys.executable, '/tmp/native_runner.py'])
        self.assertEqual(cmd[0], sys.executable)
        self.assertEqual(cmd[1:3], ['-I', '-S'])
        self.assertTrue(Path(cmd[3]).is_absolute())
        self.assertEqual(cmd[4:7], [str(job.group), str(job.marker), '--'])
        self.assertEqual(cmd[7:], [sys.executable, '/tmp/native_runner.py'])


if __name__ == '__main__':
    unittest.main()
