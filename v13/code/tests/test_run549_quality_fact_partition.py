"""Run549: human satisfaction cannot masquerade as factual correctness or Age evidence.

Synthetic source-only evidence. No native inference, user-rights or Age promotion.
"""
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13.agi import hub, live, maturity
from v13 import inputs

SIG = {'uncertainty': .2, 'route_hint': 'simple'}


class Run549EvidencePartition(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.g = hub(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _event(self):
        e = self.r.store.event(self.r.session, 'Budget Aurora?')
        live.before_effort(self.r, e, {}, SIG)
        return e

    def test_legacy_mixed_labels_cannot_drive_factual_abstention(self):
        e = self._event()
        for _ in range(512):
            self.g.metacog.record(live.LEGACY_ANSWER, .8, False)
        meta = {}
        out = live.before_effort(self.r, e, meta, SIG)
        self.assertEqual(out['uncertainty'], .2)
        self.assertNotIn('metacog_abstain', meta)
        self.assertTrue(meta['metacognition']['legacy_mixed_answer_ignored'])
        self.assertEqual(meta['metacognition']['answer']['reason'], 'UNCALIBRATED')
        self.assertIsNone(live.clarify(self.r, meta))
        self.assertIsNone(maturity.collect(self.g, self.r.store, self.r.cfg)['calibration'])
        self.assertEqual(self.g.metacog.box.load()[0]['components'][live.LEGACY_ANSWER]['pairs'][-1], [.8, 0])

    def test_quality_can_raise_effort_but_never_claim_factual_abstention(self):
        e = self._event()
        for _ in range(40):
            self.g.metacog.record(live.ANSWER_QUALITY, .8, False)
        meta = {}
        out = live.before_effort(self.r, e, meta, SIG)
        self.assertEqual(out['uncertainty'], .6)
        self.assertNotIn('metacog_abstain', meta)
        self.assertTrue(meta['metacognition']['answer_quality']['abstain'])
        self.assertEqual(meta['metacognition']['answer']['reason'], 'UNCALIBRATED')
        self.assertIsNone(live.clarify(self.r, meta))
        self.assertIsNone(maturity.collect(self.g, self.r.store, self.r.cfg)['calibration'])

    def test_grounded_factual_corrections_keep_existing_shadow_gate(self):
        e = self._event()
        self.r.memory.feedback(e['event_id'], 'fact', '120 Euro', key='Budget Aurora?')
        self.assertEqual(self.g.metacog.box.load()[0]['components'][live.ANSWER_GROUNDED]['pairs'], [[.8, 0]])
        for _ in range(39):
            self.g.metacog.record(live.ANSWER_GROUNDED, .8, False)
        meta = {}
        out = live.before_effort(self.r, e, meta, SIG)
        self.assertEqual(out['uncertainty'], .8)
        self.assertTrue(meta['metacog_abstain'])
        self.assertEqual(live.clarify(self.r, meta)['mode'], 'SHADOW')
        self.assertFalse(live.clarify(self.r, meta)['apply'])

    def test_explicit_rating_is_quality_only_and_restart_keeps_provenance_split(self):
        e = self._event()
        mid = self.r.store.message(self.r.session, e['event_id'], 'assistant', 'ok')
        self.r.store.finish_message(mid, 'FINAL', {})
        inputs.record_rating(self.r.store, e['event_id'], 9, 'EXPLICIT_NOTE')
        st = self.g.metacog.box.load()[0]['components']
        self.assertEqual(st[live.ANSWER_QUALITY]['pairs'], [[.8, 1]])
        self.assertNotIn(live.ANSWER_GROUNDED, st)
        self.assertNotIn(live.LEGACY_ANSWER, st)
        self.r.close()
        self.r = Runtime(self.home)
        self.g = hub(self.r)
        self.assertEqual(self.g.metacog.box.load()[0]['components'][live.ANSWER_QUALITY]['pairs'], [[.8, 1]])
        self.assertNotIn(live.ANSWER_GROUNDED, self.g.metacog.box.load()[0]['components'])

    def test_age_calibration_excludes_quality_and_legacy_but_keeps_ag12(self):
        for _ in range(40):
            self.g.metacog.record(live.LEGACY_ANSWER, .8, True)
            self.g.metacog.record(live.ANSWER_QUALITY, .8, True)
        self.assertIsNone(maturity.collect(self.g, self.r.store, self.r.cfg)['calibration'])
        for _ in range(40):
            self.g.metacog.record('ag12:source_scored', .8, True)
        self.assertIsNotNone(maturity.collect(self.g, self.r.store, self.r.cfg)['calibration'])


if __name__ == '__main__':
    unittest.main()
