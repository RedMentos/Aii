"""Run623: active-turn configuration mutations must fail atomically at idle gate."""
import json
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.operator import Operator
from v13.effort import get_mode


MUTATIONS = (':semantic off', ':sampling legacy', ':duplex interrupt',
             ':effort high')
STATUSES = (':semantic status', ':sampling', ':duplex status', ':effort')


class AtomicConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def snapshot(self):
        return ((self.home / 'config/settings.json').read_bytes(),
                get_mode(self.r.store),
                self.r.cfg['memory_embedding'],
                self.r.cfg['c3_sampling'],
                self.r.cfg['duplex_mode'],
                self.r.cfg['learning_mode'],
                self.r.cfg['system_stage'],
                self.r.cfg['latents_enabled'])

    def test_busy_turn_and_shadow_refuse_all_mutations_without_changes(self):
        before = self.snapshot()
        for owner in ('turn', 'shadow'):
            with self.r.lock:
                self.r.current = owner
                try:
                    for command in MUTATIONS:
                        with self.subTest(owner=owner, command=command):
                            with self.assertRaises(ValueError):
                                Operator(self.r).run(command)
                            self.assertEqual(self.snapshot(), before)
                finally:
                    self.r.current = None

    def test_status_remains_available_while_busy(self):
        before = self.snapshot()
        with self.r.lock:
            self.r.current = 'turn'
            try:
                for command in STATUSES:
                    with self.subTest(command=command):
                        result = Operator(self.r).run(command)
                        self.assertTrue(result)
                        self.assertEqual(self.snapshot(), before)
            finally:
                self.r.current = None

    def test_idle_mutations_persist_after_restart_without_new_rights(self):
        before = self.snapshot()
        for command in MUTATIONS:
            self.assertTrue(Operator(self.r).run(command))
        self.assertEqual(self.r.cfg['memory_embedding'], 'off')
        self.assertEqual(self.r.cfg['c3_sampling'], 'legacy')
        self.assertEqual(self.r.cfg['duplex_mode'], 'interrupt')
        self.assertEqual(get_mode(self.r.store), 'high')
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.assertEqual(self.r.cfg['memory_embedding'], 'off')
        self.assertEqual(self.r.cfg['c3_sampling'], 'legacy')
        self.assertEqual(self.r.cfg['duplex_mode'], 'interrupt')
        self.assertEqual(get_mode(self.r.store), 'high')
        self.assertEqual((self.r.cfg['learning_mode'], self.r.cfg['system_stage'],
                          self.r.cfg['latents_enabled']), before[-3:])

    def test_invalid_values_never_change_config(self):
        before = self.snapshot()
        for command in (':semantic invalid', ':sampling unknown',
                        ':duplex wrong', ':effort impossible',
                        ':sampling legacy extra', ':semantic off extra'):
            with self.subTest(command=command), self.assertRaises(ValueError):
                Operator(self.r).run(command)
            self.assertEqual(self.snapshot(), before)

    def test_no_status_promotes_age_or_learning(self):
        before = self.snapshot()
        for command in STATUSES:
            Operator(self.r).run(command)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.r.cfg['system_stage'], 0)
        self.assertFalse(self.r.cfg['latents_enabled'])


if __name__ == '__main__':
    unittest.main()
