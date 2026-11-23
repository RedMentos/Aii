"""AG8 request payload must bind the exact durable approved proposal.

Actual Runtime/SQLite + restart, HX1/HX3 SHADOW consumers. No native models,
live authority, age promotion or automatic mutation of human decisions.
"""
import json
import tempfile
import unittest
from pathlib import Path

from v13.age import AgeControl
from v13.agi.harness import HarnessLibrary, KEY as HX1_KEY, default
from v13.agi.experience import ExperienceLibrary
from v13.agi.self_improve import (
    SelfImprovement, KEY as AG8_KEY, require_approved_origin)
from v13.runtime import Runtime


TARGET = 'tool_hint.list_note'
OTHER = 'prompt.en.clarify'
APPROVED_TEXT = 'Preserve the exact source numbers before reporting.'
OTHER_TEXT = 'Ask one short question when the source is ambiguous.'
UNAPPROVED_TEXT = 'Use an invented number instead of the source.'


class AG8RequestPayloadBinding(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.si = SelfImprovement(
            self.r.store, self.r.cfg, AgeControl(self.r.store, self.r.cfg))
        self.h = HarnessLibrary(self.r.store)
        self.x = ExperienceLibrary(self.r.store, self.home)
        (self.home / 'evidence.txt').write_text('source-backed evidence',
                                                encoding='utf-8')
        self.learning_mode = self.r.cfg['learning_mode']

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def approve_apply(self, target, value):
        pid = self.si.propose('harness', {target: value}, origin='USER')
        self.si.evaluate(pid, lambda settings:
                         {'overall': .5, 'seen': .6, 'unseen': .4}
                         if settings is None else
                         {'overall': .55, 'seen': .6, 'unseen': .42})
        proposal = self.si.approve(pid)['proposal']
        self.h.apply(proposal, proposal['diff'])
        return proposal

    def restart(self):
        self.r.close()
        self.r = Runtime(self.home)
        self.h = HarnessLibrary(self.r.store)
        self.x = ExperienceLibrary(self.r.store, self.home)

    def test_modified_ag8_diff_cannot_reuse_old_human_request(self):
        approved = self.approve_apply(TARGET, APPROVED_TEXT)
        other = self.approve_apply(OTHER, OTHER_TEXT)
        self.x.record(approved, 'calculation source', 'quote exact numbers',
                      'evidence.txt', 'list_arith')
        self.assertEqual(self.h.resolve(TARGET), APPROVED_TEXT)
        self.assertEqual(len(self.x.lookup('list_arith')), 1)
        state, version = self.r.store.state(AG8_KEY, None)
        state['proposals'][approved['id']]['diff'][TARGET] = UNAPPROVED_TEXT
        self.r.store.set_state(AG8_KEY, state, expected=version)
        state, version = self.r.store.state(HX1_KEY, None)
        state['active'][TARGET]['value'] = UNAPPROVED_TEXT
        self.r.store.set_state(HX1_KEY, state, expected=version)
        # Human request still contains the original diff; changed AG8 state
        # must not inherit that approval even when HX1's value matches it.
        self.assertEqual(self.h.resolve(TARGET), default(TARGET))
        self.assertEqual(self.x.lookup('list_arith'), [])
        self.assertEqual(self.h.resolve(OTHER), OTHER_TEXT)
        self.restart()
        self.assertEqual(self.h.resolve(TARGET), default(TARGET))
        self.assertEqual(self.h.resolve(OTHER), OTHER_TEXT)
        self.assertEqual(self.x.lookup('list_arith'), [])
        self.assertEqual(self.r.cfg['learning_mode'], self.learning_mode)
        self.assertEqual(self.r.store.rows('SELECT * FROM updates'), [])
        self.assertEqual(self.h.report()['live_consumers'], 0)

    def test_request_payload_and_kind_must_match_approved_snapshot(self):
        approved = self.approve_apply(TARGET, APPROVED_TEXT)
        rid = approved['request_id']
        row = self.r.store.one('SELECT kind,payload,status FROM requests WHERE id=?',
                               (rid,))
        self.assertEqual(row['kind'], 'SELF_IMPROVEMENT')
        self.assertEqual(row['status'], 'APPROVED')
        original = json.loads(row['payload'])
        self.assertEqual(original['proposal'], approved['id'])
        cases = []
        for field, value in (
            ('proposal', 'imp_foreign'),
            ('kind', 'knob'),
            ('diff', {TARGET: UNAPPROVED_TEXT}),
            ('shield', {'passed': True, 'gain': .99}),
        ):
            altered = dict(original)
            altered[field] = value
            cases.append((field, 'SELF_IMPROVEMENT', json.dumps(altered)))
        cases += [('invalid_json', 'SELF_IMPROVEMENT', '{not-json'),
                  ('wrong_row_kind', 'UNRELATED', row['payload'])]
        for label, kind, payload in cases:
            with self.subTest(label=label):
                with self.r.store.tx() as conn:
                    conn.execute('UPDATE requests SET kind=?, payload=? WHERE id=?',
                                 (kind, payload, rid))
                with self.assertRaises(PermissionError):
                    require_approved_origin(self.r.store, approved, kind='harness')
                with self.r.store.tx() as conn:
                    conn.execute('UPDATE requests SET kind=?, payload=? WHERE id=?',
                                 (row['kind'], row['payload'], rid))
        self.assertEqual(require_approved_origin(
            self.r.store, approved, kind='harness')['id'], approved['id'])
        self.assertEqual(self.h.resolve(TARGET), APPROVED_TEXT)


if __name__ == '__main__':
    unittest.main()
