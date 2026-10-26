"""Run551: answer-quality rating revisions are one effective AG9 sample.

Synthetic software only; no model/Redmi, age promotion or factual truth claim.
"""
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13 import inputs
from v13.agi import hub, live
from v13.agi.metacog import Metacognition, WINDOW


class Run551RatingRevision(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.g = hub(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def event(self, text='Budget Aurora?'):
        e = self.r.store.event(self.r.session, text)
        live.before_effort(self.r, e, {}, {'uncertainty': .2, 'route_hint': 'simple'})
        mid = self.r.store.message(self.r.session, e['event_id'], 'assistant', 'answer')
        self.r.store.finish_message(mid, 'FINAL', {})
        return e['event_id']

    def quality(self):
        return self.g.metacog.box.load()[0]['components'][live.ANSWER_QUALITY]

    def test_forty_edits_one_answer_never_fabricate_calibration_support(self):
        eid = self.event()
        for i in range(40):
            inputs.record_rating(self.r.store, eid, 3 if i % 2 else 9, 'EXPLICIT_NOTE')
        comp = self.quality()
        self.assertEqual(comp['pairs'], [[.8, 0]])
        self.assertEqual(comp['evidence_keys'], ['rating:'+eid])
        self.assertIsNone(comp['calibrator'])
        self.assertEqual(self.g.metacog.decide(live.ANSWER_QUALITY, .8)['reason'], 'UNCALIBRATED')
        self.assertNotIn('metacog_abstain', self._before(eid))

    def _before(self, eid):
        meta = {}
        live.before_effort(self.r, {'event_id': eid}, meta, {'uncertainty': .2, 'route_hint': 'simple'})
        return meta

    def test_edit_and_neutral_retraction_are_not_additional_samples(self):
        eid = self.event()
        inputs.record_rating(self.r.store, eid, 3, 'EXPLICIT_NOTE')
        self.assertEqual(self.quality()['pairs'], [[.8, 0]])
        inputs.record_rating(self.r.store, eid, 9, 'EXPLICIT_NOTE')
        self.assertEqual(self.quality()['pairs'], [[.8, 1]])
        inputs.record_rating(self.r.store, eid, 5, 'EXPLICIT_NOTE')
        self.assertEqual(self.quality()['pairs'], [])
        self.assertEqual(self.quality()['evidence_keys'], [])
        inputs.record_rating(self.r.store, eid, 2, 'EXPLICIT_NOTE')
        self.assertEqual(self.quality()['pairs'], [[.8, 0]])

    def test_explicit_outweighs_later_implicit_and_neutral_suppresses(self):
        eid = self.event()
        inputs.record_rating(self.r.store, eid, 3, 'IMPLICIT_CHAT')
        inputs.record_rating(self.r.store, eid, 9, 'EXPLICIT_NOTE')
        inputs.record_rating(self.r.store, eid, 3, 'IMPLICIT_CHAT')
        self.assertEqual(self.quality()['pairs'], [[.8, 1]])
        inputs.record_rating(self.r.store, eid, 5, 'EXPLICIT_NOTE')
        self.assertEqual(self.quality()['pairs'], [])
        inputs.record_rating(self.r.store, eid, 8, 'IMPLICIT_CHAT')
        self.assertEqual(self.quality()['pairs'], [])

    def test_distinct_events_and_restart_are_distinct_sources(self):
        a, b = self.event('A'), self.event('B')
        inputs.record_rating(self.r.store, a, 9, 'EXPLICIT_NOTE')
        inputs.record_rating(self.r.store, b, 3, 'EXPLICIT_NOTE')
        self.assertEqual(self.quality()['pairs'], [[.8, 1], [.8, 0]])
        self.r.close()
        self.r = Runtime(self.home)
        self.g = hub(self.r)
        inputs.record_rating(self.r.store, a, 2, 'EXPLICIT_NOTE')
        self.assertEqual(self.quality()['pairs'], [[.8, 0], [.8, 0]])
        self.assertEqual(set(self.quality()['evidence_keys']), {'rating:'+a, 'rating:'+b})

    def test_old_unkeyed_pairs_survive_mixed_writes_and_window_eviction(self):
        m = Metacognition(self.r.store)
        for i in range(3):
            m.record(live.ANSWER_QUALITY, .8, bool(i % 2))
        m.record_keyed(live.ANSWER_QUALITY, .8, True, 'rating:one')
        self.assertEqual(self.quality()['evidence_keys'], [None, None, None, 'rating:one'])
        m.record(live.ANSWER_QUALITY, .8, False)
        self.assertEqual(self.quality()['evidence_keys'][-1], None)
        for i in range(WINDOW + 3):
            m.record_keyed(live.ANSWER_QUALITY, .8, True, 'rating:unique:'+str(i))
        comp = self.quality()
        self.assertEqual(len(comp['pairs']), WINDOW)
        self.assertEqual(len(comp['evidence_keys']), WINDOW)
        self.assertNotIn('rating:one', comp['evidence_keys'])
        m.record_keyed(live.ANSWER_QUALITY, .8, False, 'rating:unique:'+str(WINDOW+2))
        self.assertEqual(len(self.quality()['pairs']), WINDOW)
        self.assertEqual(self.quality()['pairs'][-1], [.8, 0])

    def test_corrupt_parallel_keys_refuse_mutation(self):
        m = Metacognition(self.r.store)
        m.record_keyed(live.ANSWER_QUALITY, .8, True, 'rating:one')
        m.box.mutate(lambda st: st['components'][live.ANSWER_QUALITY].update(evidence_keys=[]))
        before = m.box.load()[0]
        with self.assertRaisesRegex(ValueError, 'METACOG_EVIDENCE_KEYS_CORRUPT'):
            m.record_keyed(live.ANSWER_QUALITY, .8, False, 'rating:one')
        self.assertEqual(m.box.load()[0], before)


if __name__ == '__main__':
    unittest.main()
