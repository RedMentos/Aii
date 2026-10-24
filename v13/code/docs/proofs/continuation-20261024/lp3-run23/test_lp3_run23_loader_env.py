"""Run23: Linux loader injection before Python -I -S; software-only guard.

No writable cgroup, model or unowned process is touched. The C constructor
writes a private sentinel; it does not fork or modify host state.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_lp3_serial_cohort as base
mod = base.mod
import lp3_cgroup_v2 as cg


class LoaderPrejoinCounterexample(unittest.TestCase):
    def test_ld_preload_constructor_runs_before_isolated_helper(self):
        if sys.platform != 'linux' or not shutil.which('gcc'):
            self.skipTest('Linux gcc required for native loader negative control')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src, lib = root/'prejoin.c', root/'prejoin.so'
            src.write_text(r'''#include <stdio.h>
#include <stdlib.h>
__attribute__((constructor)) static void before_main(void) {
    const char *p = getenv("LP3_PREJOIN_SENTINEL");
    if (p) { FILE *f = fopen(p, "w");
        if (f) { fputs("loader-before-join\n", f); fclose(f); } }
}
''')
            built = subprocess.run(['gcc','-shared','-fPIC','-o',str(lib),str(src)],
                                   capture_output=True, timeout=15)
            self.assertEqual(built.returncode, 0, built.stderr)
            sentinel = root/'prejoin.txt'
            fake_group = root/'not-a-cgroup'
            fake_group.mkdir()
            helper = Path(cg.__file__).with_name('lp3_cgroup_join.py')
            env = os.environ.copy()
            env['LD_PRELOAD'] = str(lib)
            env['LP3_PREJOIN_SENTINEL'] = str(sentinel)
            run = subprocess.run([sys.executable, '-I','-S',str(helper),
                                  str(fake_group),str(root/'join.json'),'--','/usr/bin/true'],
                                 env=env, capture_output=True, timeout=10)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn(b'cgroup.procs', run.stderr)
            self.assertEqual(sentinel.read_text(), 'loader-before-join\n')
            self.assertFalse((root/'join.json').exists())

    def test_wrap_rejects_nonempty_dynamic_loader_variables(self):
        job = object.__new__(cg.CgroupV2Job)
        job.group = Path('/sys/fs/cgroup/delegated/lp3-active')
        job.marker = Path('/tmp/private-marker')
        for key in ('LD_PRELOAD', 'LD_AUDIT', 'LD_LIBRARY_PATH', 'LD_FUTURE_INJECTOR'):
            with self.subTest(key=key), patch.dict(os.environ, {key:'/tmp/injected'}, clear=False):
                with self.assertRaisesRegex(cg.ContainmentBlocked, 'prejoin dynamic loader'):
                    job.wrap([sys.executable,'/tmp/runner.py'])

    def test_even_empty_loader_variables_are_rejected(self):
        job = object.__new__(cg.CgroupV2Job)
        job.group = Path('/sys/fs/cgroup/delegated/lp3-active')
        job.marker = Path('/tmp/private-marker')
        env = {k:v for k,v in os.environ.items() if not k.startswith('LD_')}
        # ld.so treats LD_TRACE_LOADED_OBJECTS as active if merely present;
        # LD_LIBRARY_PATH empty entries can mean the working directory.
        for key in ('LD_TRACE_LOADED_OBJECTS', 'LD_LIBRARY_PATH'):
            with self.subTest(key=key):
                env[key] = ''
                with self.assertRaisesRegex(cg.ContainmentBlocked, 'prejoin dynamic loader'):
                    cg.reject_prejoin_loader_env(env)
                del env[key]
        self.assertEqual(cg.reject_prejoin_loader_env(env), None)
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(job.wrap(['/usr/bin/true'])[1:3], ['-I','-S'])


class LauncherEnvironmentBinding(unittest.TestCase):
    setUp = base.SerialCohortTests.setUp
    call = base.SerialCohortTests.call
    def test_loader_injection_blocks_before_any_native_spawn(self):
        with patch.object(mod, 'check', return_value=self.ready), \
             patch.dict(os.environ, {'LD_PRELOAD':'/tmp/foreign.so'}), \
             patch.object(mod.subprocess, 'Popen') as popen:
            with self.assertRaisesRegex(cg.ContainmentBlocked, 'prejoin dynamic loader'):
                self.call()
            popen.assert_not_called()
        self.assertFalse((self.evidence/'receipt.json').exists())
        self.assertEqual(__import__('json').loads((self.evidence/'launch_status.json').read_text())['status'],
                         'WRAPPER_OR_AUDIT_FAILED_PRESERVED')

    def test_native_popen_receives_checked_environment_snapshot(self):
        with patch.object(mod, 'check', return_value=self.ready), \
             patch.dict(os.environ, {'LP3_RUN23_PROBE':'bound-env'}), \
             patch.object(mod.subprocess, 'Popen', wraps=subprocess.Popen) as popen, \
             patch.object(mod, 'audit', return_value=self.good_audit), \
             patch.object(mod, 'receipt_for', return_value={'schema':'synthetic'}):
            self.call()
            passed = popen.call_args.kwargs['env']
            self.assertEqual(passed['LP3_RUN23_PROBE'], 'bound-env')
            self.assertFalse(any(k.startswith('LD_') and v for k,v in passed.items()))


if __name__ == '__main__':
    unittest.main()
