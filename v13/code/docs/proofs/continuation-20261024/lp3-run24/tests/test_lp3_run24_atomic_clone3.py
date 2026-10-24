"""Run24: static ELF / sealed memfd / fail-closed Linux clone3 staging.

These tests DO NOT demonstrate CLONE_INTO_CGROUP on a writable delegated
kernel hierarchy, nor run native LP3, nor alter any real cgroup.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import lp3_atomic_bootstrap as atom


class AtomicClone3Staging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform != 'linux' or not shutil.which('gcc'):
            raise unittest.SkipTest('Linux and gcc required')
        cls.work = tempfile.TemporaryDirectory()
        cls.root = Path(cls.work.name)
        cls.src = SCRIPTS / 'lp3_atomic_clone3.c'
        cls.binary = cls.root / 'lp3_atomic_clone3'
        cls.build = subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror',
                                    '-static','-no-pie','-o',str(cls.binary),str(cls.src)],
                                   capture_output=True, text=True, timeout=45)
        if cls.build.returncode:
            raise AssertionError(cls.build.stderr)
        cls.sha = hashlib.sha256(cls.binary.read_bytes()).hexdigest()

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def test_compiled_binary_has_no_interpreter_or_dynamic_section(self):
        atom._check_static_elf(self.binary.read_bytes())
        if shutil.which('readelf'):
            out = subprocess.run(['readelf','-l',str(self.binary)], capture_output=True,
                                 text=True, timeout=10)
            self.assertEqual(out.returncode, 0)
            self.assertNotIn('INTERP', out.stdout)
            self.assertNotIn('DYNAMIC', out.stdout)

    def test_hash_and_sealed_memfd_are_immutable(self):
        import fcntl
        with atom.sealed_static_helper(self.binary, self.sha) as fd:
            self.assertTrue(fcntl.fcntl(fd, fcntl.F_GET_SEALS) & fcntl.F_SEAL_WRITE)
            with self.assertRaises(OSError):
                os.write(fd, b'X')
            args, opts = atom.launch_spec(fd, '/sys/fs/cgroup/delegated/lp3-active',
                                          '/tmp/lp3-private-marker', ['/usr/bin/true'])
            self.assertEqual(args[3], '--')
            self.assertEqual(opts['pass_fds'], (fd,))

    def test_wrong_hash_rejected_before_launch(self):
        with self.assertRaisesRegex(atom.AtomicBootstrapBlocked, 'SHA256 mismatch'):
            with atom.sealed_static_helper(self.binary, '0'*64):
                self.fail('must not yield')

    def test_symlink_and_group_world_writable_helper_rejected(self):
        link = self.root / 'helper-symlink'
        link.symlink_to(self.binary)
        with self.assertRaisesRegex(atom.AtomicBootstrapBlocked, 'nonsymlink'):
            with atom.sealed_static_helper(link, self.sha):
                self.fail('must not yield')
        self.binary.chmod(0o777)
        try:
            with self.assertRaisesRegex(atom.AtomicBootstrapBlocked, 'group/world writable'):
                with atom.sealed_static_helper(self.binary, self.sha):
                    self.fail('must not yield')
        finally:
            self.binary.chmod(0o700)

    def test_dynamic_elf_and_invalid_header_rejected(self):
        dynamic = self.root / 'dynamic'
        code = self.root / 'dynamic.c'
        code.write_text('int main(void) { return 0; }\n')
        build = subprocess.run(['gcc','-o',str(dynamic),str(code)], capture_output=True,
                               text=True, timeout=15)
        self.assertEqual(build.returncode, 0, build.stderr)
        with self.assertRaisesRegex(atom.AtomicBootstrapBlocked, 'ET_EXEC|dynamic'):
            atom._check_static_elf(dynamic.read_bytes())
        with self.assertRaisesRegex(atom.AtomicBootstrapBlocked, 'ELF64'):
            atom._check_static_elf(b'not-an-elf')

    def test_command_and_group_paths_are_restricted(self):
        with self.assertRaises(atom.AtomicBootstrapBlocked):
            atom.launch_spec(7, '/sys/fs/cgroup', '/tmp/marker', ['/usr/bin/true'])
        with self.assertRaises(atom.AtomicBootstrapBlocked):
            atom.launch_spec(7, '/sys/fs/cgroup/delegated/lp3-active', '/tmp/marker', ['true'])
        with self.assertRaises(atom.AtomicBootstrapBlocked):
            atom.launch_spec(7, '/sys/fs/cgroup/delegated/lp3-active', 'relative', ['/usr/bin/true'])

    def test_no_cgroup_no_spawn_no_marker_or_native_child(self):
        # The executable runs as real Linux machine code from the sealed
        # memfd, but the group is a private NON-cgroup directory. This MUST
        # fail before clone3; it is not a positive kernel containment test.
        with tempfile.TemporaryDirectory() as d:
            fake = Path(d)/'lp3-active'
            fake.mkdir()
            marker, sentinel = Path(d)/'join.json', Path(d)/'native-executed'
            with atom.sealed_static_helper(self.binary, self.sha) as fd:
                args = [f'/proc/self/fd/{fd}', str(fake), str(marker), '--',
                        '/bin/sh','-c',f'echo wrong > {sentinel}']
                result = subprocess.run(args, executable=f'/proc/self/fd/{fd}',
                                        pass_fds=(fd,), capture_output=True, text=True,
                                        timeout=10)
            self.assertEqual(result.returncode, 125, result.stderr)
            self.assertIn('LP3_ATOMIC_BLOCKED', result.stderr)
            self.assertFalse(marker.exists())
            self.assertFalse(sentinel.exists())

    def test_cgroup_root_never_used_for_probe(self):
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d)/'join.json'
            with atom.sealed_static_helper(self.binary, self.sha) as fd:
                with self.assertRaises(atom.AtomicBootstrapBlocked):
                    atom.launch_spec(fd, '/sys/fs/cgroup/lp3-active', marker,
                                     ['/usr/bin/true'])
            self.assertFalse(marker.exists())

    def test_atomic_marker_closed_schema_and_identity(self):
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d)/'marker.json'
            data = {'schema':'V13_LP3_ATOMIC_CLONE3_V1',
                    'cgroup':'/sys/fs/cgroup/delegated/lp3-active',
                    'helper_pid':123, 'child_pid':124,
                    'atomic_placement':True, 'pidfd':True,
                    'verified_membership':True}
            marker.write_text(json.dumps(data))
            self.assertEqual(atom.verify_atomic_marker(marker, data['cgroup'], 123), 124)
            for key, bad in [('child_pid', True), ('atomic_placement', 1),
                             ('pidfd', False), ('helper_pid', 999),
                             ('cgroup', '/sys/fs/cgroup/foreign/lp3-active')]:
                with self.subTest(key=key):
                    changed = {**data, key:bad}
                    marker.write_text(json.dumps(changed))
                    with self.assertRaises(atom.AtomicBootstrapBlocked):
                        atom.verify_atomic_marker(marker, data['cgroup'], 123)
            marker.write_text(json.dumps({**data, 'unregistered':True}))
            with self.assertRaises(atom.AtomicBootstrapBlocked):
                atom.verify_atomic_marker(marker, data['cgroup'], 123)

    def test_static_helper_not_injected_by_ld_preload(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src, lib = root/'inject.c', root/'inject.so'
            src.write_text('''#include <stdio.h>
#include <stdlib.h>
__attribute__((constructor)) static void hook(void) {
  const char *p = getenv("LP3_RUN24_SENTINEL");
  if (p) { FILE *f=fopen(p,"w"); if (f) { fputs("INJECTED",f); fclose(f); } }
}
''')
            built = subprocess.run(['gcc','-shared','-fPIC','-o',str(lib),str(src)],
                                   capture_output=True, text=True, timeout=15)
            self.assertEqual(built.returncode, 0, built.stderr)
            sentinel = root/'sentinel'
            env = {**os.environ, 'LD_PRELOAD':str(lib),
                   'LP3_RUN24_SENTINEL':str(sentinel)}
            # Positive control: loader injection is active for dynamic binary.
            dynamic = subprocess.run([sys.executable,'-c','pass'], env=env,
                                     capture_output=True, timeout=10)
            self.assertEqual(dynamic.returncode, 0)
            self.assertEqual(sentinel.read_text(), 'INJECTED')
            sentinel.unlink()
            # The static helper rejects fake cgroup before clone3; its own
            # startup cannot be intercepted by LD_PRELOAD.
            fake = root/'lp3-active'
            fake.mkdir()
            with atom.sealed_static_helper(self.binary, self.sha) as fd:
                args = [f'/proc/self/fd/{fd}', str(fake), str(root/'marker.json'),
                        '--', '/usr/bin/true']
                run = subprocess.run(args, executable=f'/proc/self/fd/{fd}',
                                     pass_fds=(fd,), env=env, capture_output=True,
                                     timeout=10)
            self.assertEqual(run.returncode, 125)
            self.assertFalse(sentinel.exists())
            self.assertFalse((root/'marker.json').exists())

    def test_source_declares_no_fallback_to_fork(self):
        source = self.src.read_text()
        self.assertIn('CLONE_INTO_CGROUP | CLONE_PIDFD', source)
        self.assertIn('SYS_clone3', source)
        self.assertIn('SYS_pidfd_send_signal', source)
        self.assertNotIn('fork(', source)
        self.assertNotIn('vfork(', source)


if __name__ == '__main__':
    unittest.main()