"""Run616 actual SQLite/Runtime read-only native-tap similarity tests."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
from v13.runtime import Runtime
from v13.operator import Operator
from v13 import gist_similarity as S


class SimilarityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def tap(self, text, vector, event=None):
        event = event or self.r.store.event(self.r.session, text)
        runner = MagicMock()
        runner.tap.return_value = {'token_ids': [42], 'vectors': [vector], 'metrics': {}}
        runner.tap_id = 'qwen35.result_norm.final.v1'
        with patch.object(self.r.pool, 'get_tap', return_value=runner), \
             patch.object(self.r.learner, 'predict_states', return_value=None):
            return self.r.cognition.tap('B2_GIST', event, event['source_ref'], time.monotonic()+30)

    def test_read_only_ranked_source_bound_and_operator(self):
        first = self.tap('The red bridge crosses the river.', [1., 0., 0.])
        other = self.tap('A blue mountain lies beyond town.', [0., 1., 0.])
        query = self.tap('Where is the red bridge?', [.99, .01, 0.])
        out = json.loads(Operator(self.r).run(':gist similar 2'))
        self.assertEqual(out['status'], 'READ_ONLY')
        self.assertEqual(out['query_packet_id'], query['packet_id'])
        self.assertEqual([x['packet_id'] for x in out['matches']], [first['packet_id'], other['packet_id']])
        self.assertIn('red bridge', out['matches'][0]['excerpt'])
        self.assertEqual(out['receiver_injection_authority'], 0)
        self.assertEqual(out['body_learning_authority'], 0)
        self.assertNotIn('vectors', json.dumps(out))
        self.assertNotIn('feature_path', json.dumps(out))
        self.assertIsNotNone(self.r.store.one("SELECT 1 FROM telemetry WHERE kind='gist_similarity'"))

    def test_empty_and_cross_session_isolation(self):
        self.assertEqual(json.loads(Operator(self.r).run(':gist similar'))['status'], 'NO_B2_TAP')
        self.tap('Original session private fact', [1., 0.])
        other_session = Operator(self.r).run(':new')
        self.tap('Other session query', [1., 0.])
        out = json.loads(Operator(self.r).run(':gist similar'))
        self.assertEqual(out['matches'], [])
        self.assertEqual(out['scanned'], 1)

    def test_revoked_source_and_corrupt_candidate_are_excluded(self):
        revoked = self.tap('revoked candidate', [1., 0.])
        corrupt = self.tap('corrupt feature candidate', [1., 0.])
        self.tap('query', [1., 0.])
        with self.r.store.tx() as c:
            c.execute('UPDATE sources SET deleted=1 WHERE id=?', (revoked['source_ref']['source_id'],))
        path = self.r.home / corrupt['feature_path']
        path.write_text('{"token_ids":[],"vectors":[]}')
        out = json.loads(Operator(self.r).run(':gist similar'))
        self.assertEqual(out['matches'], [])
        self.assertEqual(out['excluded'], 2)

    def test_forged_cross_session_source_ref_cannot_leak(self):
        candidate = self.tap('same-session candidate', [1., 0.])
        own = self.r.session
        Operator(self.r).run(':new')
        foreign_event = self.r.store.event(self.r.session, 'OTHER SESSION PRIVATE')
        self.r.session = own
        self.tap('query', [1., 0.])
        row = self.r.store.one('SELECT payload FROM packets WHERE id=?', (candidate['packet_id'],))
        forged = json.loads(row['payload'])
        forged['source_ref'] = foreign_event['source_ref']
        with self.r.store.tx() as c:
            c.execute('UPDATE packets SET payload=? WHERE id=?', (json.dumps(forged), candidate['packet_id']))
        out = json.loads(Operator(self.r).run(':gist similar'))
        self.assertEqual(out['matches'], [])
        self.assertEqual(out['excluded'], 1)
        self.assertNotIn('OTHER SESSION PRIVATE', json.dumps(out))

    def test_exact_subspan_taps_remain_supported(self):
        e = self.r.store.event(self.r.session, 'prefix exact source suffix')
        ref = dict(e['source_ref'], char_start=7, char_end=19)
        runner = MagicMock()
        runner.tap.return_value = {'token_ids': [42], 'vectors': [[1., 0.]], 'metrics': {}}
        runner.tap_id = 'qwen35.result_norm.final.v1'
        with patch.object(self.r.pool, 'get_tap', return_value=runner), \
             patch.object(self.r.learner, 'predict_states', return_value=None):
            sub = self.r.cognition.tap('B2_GIST', e, ref, time.monotonic()+30)
        self.tap('query', [1., 0.])
        out = json.loads(Operator(self.r).run(':gist similar'))
        self.assertEqual(out['matches'][0]['packet_id'], sub['packet_id'])
        self.assertEqual(out['matches'][0]['excerpt'], 'exact source')

    def test_stale_query_model_revision_fails_closed(self):
        self.tap('query', [1., 0.])
        with patch.object(self.r.models, 'revision', return_value='wrong-revision'):
            with self.assertRaises(S.SimilarityUnavailable):
                Operator(self.r).run(':gist similar')

    def test_source_and_taps_survive_restart(self):
        first = self.tap('past observation', [1., 0.])
        self.tap('current observation', [1., 0.])
        sess = self.r.session
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.r.session = sess
        out = json.loads(Operator(self.r).run(':gist similar'))
        self.assertEqual(out['matches'][0]['packet_id'], first['packet_id'])

    def test_nonfinite_zero_dimension_and_bad_limits(self):
        for bad in ([0., 0.], [float('nan'), 1.], [float('inf'), 1.], [[1., 2.]]):
            with self.assertRaises(S.SimilarityUnavailable):
                S.last_vector({'vectors': [bad]})
        with self.assertRaises(S.SimilarityUnavailable):
            S.last_vector({'vectors': [[1., 0.]]}, expected_dim=3)
        for arg in ('0', '6', 'bad', '1 2'):
            with self.assertRaises(ValueError):
                Operator(self.r).run(':gist similar ' + arg)

    def test_near_equal_display_cosines_rank_by_full_precision(self):
        # Old is slightly closer, but both scores round to the same 6 decimals.
        # The read-only operator must agree with full-precision native cosine,
        # not let insertion recency win an artificial display-rounding tie.
        old = self.tap('old more similar', [1., .0014])
        newer = self.tap('new less similar', [1., .0015])
        self.tap('query exact', [1., 0.])
        out = json.loads(Operator(self.r).run(':gist similar 2'))
        self.assertEqual([x['packet_id'] for x in out['matches']],
                         [old['packet_id'], newer['packet_id']])
        self.assertEqual(out['matches'][0]['cosine'], out['matches'][1]['cosine'])
        self.assertEqual(out['receiver_injection_authority'], 0)
        self.assertEqual(out['body_learning_authority'], 0)
        self.assertNotIn('_score', json.dumps(out))
        self.assertNotIn('vectors', json.dumps(out))

    def test_ties_are_stable_and_limit_is_bounded(self):
        old = self.tap('old equal', [1., 0.])
        new = self.tap('new equal', [1., 0.])
        self.tap('query', [1., 0.])
        out = json.loads(Operator(self.r).run(':gist similar 1'))
        self.assertEqual(len(out['matches']), 1)
        self.assertEqual(out['matches'][0]['packet_id'], new['packet_id'])
        self.assertNotEqual(out['matches'][0]['packet_id'], old['packet_id'])


if __name__ == '__main__':
    unittest.main()
