"""HX1 read-side AG8 revocation of applied SHADOW harness overrides.

Actual Runtime/SQLite and restart. No live harness consumer or native inference.
"""
import tempfile
import unittest
from pathlib import Path

from v13.age import AgeControl
from v13.agi.harness import HarnessLibrary, default, KEY
from v13.agi.self_improve import SelfImprovement
from v13.runtime import Runtime


TARGET = 'tool_hint.list_note'
OTHER = 'prompt.en.clarify'
FIRST = 'Always preserve the exact source numbers.'
SECOND = 'Always check the exact total against its source.'
THIRD = 'Ask one precise question when uncertain.'


class HX1AppliedRevocationRead(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.h = HarnessLibrary(self.r.store)
        self.si = SelfImprovement(
            self.r.store, self.r.cfg, AgeControl(self.r.store, self.r.cfg))
        self.learning_mode = self.r.cfg['learning_mode']

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def approved(self, target, value):
        pid = self.si.propose('harness', {target: value}, origin='USER')
        self.si.evaluate(
            pid, lambda settings:
            {'overall': .5, 'seen': .6, 'unseen': .4} if settings is None
            else {'overall': .55, 'seen': .6, 'unseen': .42})
        return self.si.approve(pid)['proposal']

    def revoke(self, proposal):
        with self.r.store.tx() as conn:
            conn.execute("UPDATE requests SET status='REJECTED' WHERE id=?",
                         (proposal['request_id'],))

    def restart(self):
        self.r.close()
        self.r = Runtime(self.home)
        self.h = HarnessLibrary(self.r.store)

    def test_revoked_newest_falls_back_to_valid_previous_then_default(self):
        first = self.approved(TARGET, FIRST)
        second = self.approved(TARGET, SECOND)
        other = self.approved(OTHER, THIRD)
        for p in (first, second, other):
            self.h.apply(p, p['diff'])
        self.assertEqual(self.h.resolve(TARGET), SECOND)
        self.assertEqual(self.h.resolve(OTHER), THIRD)
        self.assertEqual(self.h.manifest_fields()['harness_targets'][TARGET], 2)

        self.revoke(second)
        self.assertEqual(self.h.resolve(TARGET), FIRST)
        self.assertEqual(self.h.overlay()[TARGET], FIRST)
        self.assertEqual(self.h.manifest_fields()['harness_targets'][TARGET], 1)
        self.assertEqual(self.h.report()['active'], sorted((TARGET, OTHER)))

        self.restart()
        self.assertEqual(self.h.resolve(TARGET), FIRST)
        self.assertEqual(self.h.resolve(OTHER), THIRD)
        self.revoke(first)
        self.assertEqual(self.h.resolve(TARGET), default(TARGET))
        self.assertEqual(self.h.overlay()[TARGET], default(TARGET))
        self.assertNotIn(TARGET, self.h.manifest_fields()['harness_targets'])
        self.assertEqual(self.h.report()['active'], [OTHER])
        self.assertEqual(self.h.resolve(OTHER), THIRD)
        self.assertEqual(self.r.cfg['learning_mode'], self.learning_mode)
        self.assertEqual(self.r.store.rows('SELECT * FROM updates'), [])

    def test_missing_history_for_revoked_override_fails_closed(self):
        first = self.approved(TARGET, FIRST)
        second = self.approved(TARGET, SECOND)
        self.h.apply(first, first['diff'])
        self.h.apply(second, second['diff'])
        state, version = self.r.store.state(KEY, None)
        state['history'] = [x for x in state['history']
                            if not (x['target'] == TARGET and
                                    x['proposal'] == second['id'] and
                                    x['op'] == 'apply')]
        self.r.store.set_state(KEY, state, expected=version)
        self.revoke(second)
        self.assertEqual(self.h.resolve(TARGET), default(TARGET))
        self.assertNotIn(TARGET, self.h.manifest_fields()['harness_targets'])
        self.assertEqual(self.r.store.rows('SELECT * FROM updates'), [])


if __name__ == '__main__':
    unittest.main()
