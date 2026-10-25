"""Run178 Linux-native synthetic ownership tests; no model/cgroup claim."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from run178_pidfd_child_ownership import UnownedProcess, open_owned_child_pidfd


@unittest.skipUnless(sys.platform == 'linux' and hasattr(os, 'P_PIDFD'),
                     'requires Linux pidfd waitid')
class PidfdOwnershipTests(unittest.TestCase):
    def test_direct_child_accepted_then_killed_via_pidfd(self):
        p = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(10)'])
        try:
            fd = open_owned_child_pidfd(p.pid)
            try:
                signal.pidfd_send_signal(fd, signal.SIGKILL, None, 0)
            finally:
                os.close(fd)
            self.assertEqual(p.wait(timeout=3), -signal.SIGKILL)
        finally:
            if p.poll() is None:
                p.kill(); p.wait()

    def test_nonchild_rejected_and_remains_alive(self):
        # The parent is ours; the printed sleeping grandchild is not.
        helper = subprocess.Popen([sys.executable, '-c',
            'import subprocess,sys; p=subprocess.Popen([sys.executable,"-c",'
            '"import time;time.sleep(30)"]);print(p.pid,flush=True);'
            'sys.stdin.readline();p.terminate();p.wait()'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            foreign_pid = int(helper.stdout.readline().strip())
            with self.assertRaises(UnownedProcess):
                open_owned_child_pidfd(foreign_pid)
            self.assertIsNone(helper.poll())
            helper.stdin.write('stop\n'); helper.stdin.flush()
            self.assertEqual(helper.wait(timeout=5), 0)
        finally:
            if helper.poll() is None:
                try:
                    helper.stdin.write('stop\n'); helper.stdin.flush()
                    helper.wait(timeout=5)
                except (BrokenPipeError, subprocess.TimeoutExpired):
                    helper.terminate(); helper.wait(timeout=5)
            helper.stdout.close(); helper.stdin.close()

    def test_bad_pid_rejected_without_open(self):
        for pid in (0, -1, '1', True):
            with self.subTest(pid=pid), self.assertRaises(ValueError):
                open_owned_child_pidfd(pid)

    def test_fd_closed_if_waitid_refuses_child(self):
        p = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(10)'])
        try:
            with patch('run178_pidfd_child_ownership.os.waitid',
                       side_effect=ChildProcessError('synthetic ECHILD')):
                with self.assertRaises(UnownedProcess):
                    open_owned_child_pidfd(p.pid)
            # Closing the fd is mandatory on failure, but must not signal p.
            self.assertIsNone(p.poll())
        finally:
            p.kill(); p.wait()

    def test_no_numeric_signal_fallback(self):
        source = (Path(__file__).resolve().parents[1] / 'scripts' /
                  'run178_pidfd_child_ownership.py').read_text()
        self.assertNotIn('os.kill(', source)
        self.assertNotIn('os.killpg(', source)
        self.assertIn('os.waitid(os.P_PIDFD', source)


if __name__ == '__main__':
    unittest.main()
