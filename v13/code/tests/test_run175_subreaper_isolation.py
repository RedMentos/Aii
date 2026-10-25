"""Real Linux synthetic process tests. No model, no cgroup proof."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/run175_subreaper_isolation.py'

class TestSubreaper(unittest.TestCase):
    def run_case(self,extra):
        p=subprocess.run([sys.executable,str(SCRIPT),*extra],capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)
        d=json.loads(p.stdout)
        self.assertTrue(d['orphan_adopted'])
        self.assertTrue(d['cleanup']['closed'])
        self.assertEqual(d['cleanup']['remaining'],0)
        self.assertGreaterEqual(d['cleanup']['killed_by_pidfd'],1)
        self.assertFalse(d['cgroup_isolation_proven'])
        self.assertFalse(d['body_model_executed'])
    def test_orphan_setsids_reaped(self):self.run_case([])
    def test_double_fork_setsids_reaped(self):self.run_case(['--double-fork'])
    def test_no_numeric_pid_signal_fallback(self):
        source=SCRIPT.read_text()
        self.assertNotIn('os.kill(',source)
        self.assertNotIn('os.killpg(',source)
        self.assertIn('signal.pidfd_send_signal(',source)

if __name__=='__main__':unittest.main()
