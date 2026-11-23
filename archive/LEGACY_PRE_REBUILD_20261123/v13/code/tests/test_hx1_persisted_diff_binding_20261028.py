"""HX1 read-side value/target binding to the durable AG8-approved diff.

Actual Runtime/SQLite and restart; SHADOW only, no native/Redmi or live consumer.
RED-first regression: approval of a proposal ID must not authorize a different
persisted value or target. No automatic rollback or mutation is permitted.
"""
import tempfile
import unittest
from pathlib import Path

from v13.age import AgeControl
from v13.agi.harness import HarnessLibrary, KEY, default
from v13.agi.self_improve import SelfImprovement
from v13.runtime import Runtime


TARGET = 'tool_hint.list_note'
OTHER = 'prompt.en.clarify'
FIRST = 'Preserve the exact source numbers in the output.'
SECOND = 'Verify every sum against its source before reporting.'
OTHER_VALUE = 'Ask one short question when the task is ambiguous.'
UNAPPROVED = 'Invent the total from memory instead of the source.'


class HX1PersistedApprovedDiffRead(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.runtime = Runtime(self.home)
        self.runtime.sleep.cycle.set_policy('enabled', 'off')
        self.h = HarnessLibrary(self.runtime.store)
        self.si = SelfImprovement(
            self.runtime.store, self.runtime.cfg,
            AgeControl(self.runtime.store, self.runtime.cfg))
        self.learning_mode = self.runtime.cfg['learning_mode']

    def tearDown(self):
        self.runtime.close()
        self.temp.cleanup()

    def approved_apply(self, target, value):
        pid = self.si.propose('harness', {target: value}, origin='USER')
        self.si.evaluate(pid, lambda settings:
                         {'overall': .5, 'seen': .6, 'unseen': .4}
                         if settings is None else
                         {'overall': .55, 'seen': .6, 'unseen': .42})
        proposal = self.si.approve(pid)['proposal']
        self.h.apply(proposal, proposal['diff'])
        return proposal

    def mutate(self, change):
        state, version = self.runtime.store.state(KEY, None)
        change(state)
        self.runtime.store.set_state(KEY, state, expected=version)

    def restart(self):
        self.runtime.close()
        self.runtime = Runtime(self.home)
        self.h = HarnessLibrary(self.runtime.store)

    def assert_shadow_only(self):
        self.assertEqual(self.h.report()['live_consumers'], 0)
        self.assertEqual(self.runtime.cfg['learning_mode'], self.learning_mode)
        self.assertEqual(self.runtime.store.rows('SELECT * FROM updates'), [])

    def test_changed_active_value_uses_approved_previous_and_preserves_other(self):
        self.approved_apply(TARGET, FIRST)
        self.approved_apply(TARGET, SECOND)
        self.approved_apply(OTHER, OTHER_VALUE)
        self.assertEqual(self.h.resolve(TARGET), SECOND)
        self.mutate(lambda st: st['active'][TARGET].__setitem__('value', UNAPPROVED))
        self.assertEqual(self.h.resolve(TARGET), FIRST)
        self.assertEqual(self.h.overlay()[TARGET], FIRST)
        self.assertEqual(self.h.manifest_fields()['harness_targets'][TARGET], 1)
        self.assertEqual(self.h.resolve(OTHER), OTHER_VALUE)
        self.restart()
        self.assertEqual(self.h.resolve(TARGET), FIRST)
        self.assertEqual(self.h.resolve(OTHER), OTHER_VALUE)
        self.assert_shadow_only()

    def test_changed_previous_value_never_served_after_revocation(self):
        first = self.approved_apply(TARGET, FIRST)
        second = self.approved_apply(TARGET, SECOND)
        def corrupt_previous(st):
            row = next(h for h in st['history']
                       if h.get('op') == 'apply'
                       and h.get('proposal') == second['id'])
            self.assertEqual(row['previous']['proposal'], first['id'])
            row['previous']['value'] = UNAPPROVED
        self.mutate(corrupt_previous)
        with self.runtime.store.tx() as conn:
            conn.execute("UPDATE requests SET status='REJECTED' WHERE id=?",
                         (second['request_id'],))
        self.assertEqual(self.h.resolve(TARGET), default(TARGET))
        self.assertNotIn(TARGET, self.h.manifest_fields()['harness_targets'])
        self.assert_shadow_only()

    def test_approved_id_for_other_target_does_not_authorize_target_value(self):
        self.approved_apply(TARGET, FIRST)
        other = self.approved_apply(OTHER, OTHER_VALUE)
        self.mutate(lambda st: st['active'][TARGET].__setitem__('proposal', other['id']))
        self.assertEqual(self.h.resolve(TARGET), default(TARGET))
        self.assertEqual(self.h.resolve(OTHER), OTHER_VALUE)
        self.assert_shadow_only()


if __name__ == '__main__':
    unittest.main()
