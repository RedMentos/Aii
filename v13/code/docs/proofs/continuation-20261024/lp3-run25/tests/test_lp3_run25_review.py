"""Run25 adversarial review: no positive delegated-cgroup claim."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import lp3_atomic_bootstrap as atom

GROUP = '/sys/fs/cgroup/delegated/lp3-active'
VALID = {'schema':'V13_LP3_ATOMIC_CLONE3_V1', 'cgroup':GROUP,
         'helper_pid':101, 'child_pid':102, 'atomic_placement':True,
         'pidfd':True, 'verified_membership':True}

class Run25Review(unittest.TestCase):
    def test_reject_duplicate_json_keys_even_when_last_value_valid(self):
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td) / 'marker.json'
            text = json.dumps(VALID)
            marker.write_text(text[:-1] + ',"child_pid":102}')
            with self.assertRaises(atom.AtomicBootstrapBlocked):
                atom.verify_atomic_marker(marker, GROUP, 101)

    def test_reject_symlink_marker_even_if_content_valid(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root/'real.json').write_text(json.dumps(VALID))
            (root/'marker.json').symlink_to(root/'real.json')
            with self.assertRaises(atom.AtomicBootstrapBlocked):
                atom.verify_atomic_marker(root/'marker.json', GROUP, 101)

    def test_reject_large_marker_before_json_parsing(self):
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td)/'marker.json'
            marker.write_bytes(b' ' * 1024 * 1024 + json.dumps(VALID).encode())
            with self.assertRaisesRegex(atom.AtomicBootstrapBlocked, 'size|oversize|too large'):
                atom.verify_atomic_marker(marker, GROUP, 101)

    def test_reject_noncanonical_cgroup_receipt_even_if_equal(self):
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td)/'marker.json'
            group = '/sys/fs/cgroup/delegated/../delegated/lp3-active'
            marker.write_text(json.dumps({**VALID,'cgroup':group}))
            with self.assertRaises(atom.AtomicBootstrapBlocked):
                atom.verify_atomic_marker(marker, group, 101)

    def test_reject_same_helper_and_child_pid(self):
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td)/'marker.json'
            marker.write_text(json.dumps({**VALID, 'child_pid':101}))
            with self.assertRaises(atom.AtomicBootstrapBlocked):
                atom.verify_atomic_marker(marker, GROUP, 101)

    def test_reject_invalid_helper_pid_input(self):
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td)/'marker.json'
            marker.write_text(json.dumps({**VALID, 'helper_pid':-1}))
            with self.assertRaises(atom.AtomicBootstrapBlocked):
                atom.verify_atomic_marker(marker, GROUP, -1)

    def test_c_realpath_never_uses_undersized_caller_buffer(self):
        src = (SCRIPTS/'lp3_atomic_clone3.c').read_text()
        self.assertNotIn('realpath(path, canonical)', src)
        self.assertIn('realpath(path, NULL)', src)

if __name__ == '__main__': unittest.main()
