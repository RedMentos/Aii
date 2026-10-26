"""Run617 replay integration model-free negative tests, real ephemeral SQLite."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import run617_gist_native_replay as R


class ReplayTests(unittest.TestCase):
    def test_rank_is_cosine_and_newer_tie_first(self):
        y = np.asarray([[1., 0.], [0., 1.], [1., 0.], [1., 0.]])
        self.assertEqual(R.rank_raw(y, 0, [1, 2, 3]), [2, 1, 0])

    def test_real_sqlite_operator_matches_raw_replayed_vectors(self):
        rows = [{'id': f'topic-{i}-'+v, 'fact_id': f'topic-{i}', 'variant': v,
                 'text': f'Original synthetic prompt {i} {v}'}
                for i in range(1, 4) for v in 'AB']
        y = np.zeros((6, 1024))
        for i in range(3):
            y[2*i, i] = 1.
            y[2*i+1, i] = 1.
        r = R.replay_case(rows, y, list(range(6)), 0)
        self.assertTrue(r['matched_raw_cosine_top5'])
        self.assertEqual(r['opposite_rank_top5'], 1)
        self.assertEqual(len(r['operator_top5_ids']), 5)

    def test_receipt_source_tampering_is_rejected(self):
        rows = [{'id': f'topic-{i}-{v}', 'fact_id': f'topic-{i}', 'variant': v,
                 'text': f'Unique prompt {i} {v}'} for i in range(40) for v in 'AB']
        ids = [r['id'] for r in rows]
        receipts = [{'id': r['id'], 'prompt_sha256': hashlib.sha256(r['text'].encode()).hexdigest(),
                     'tap_id': R.TAP_ID, 'dimension': 1024, 'token_count': 1} for r in rows]
        report = {'receipts': {'B2_GIST': receipts}, 'models': {'B2_GIST': {'revision': R.REV,
                  'sha256': '57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf'}},
                  'gates': dict(R.GATES), 'can_latent_inject': False}
        R.validate_receipts(rows, ids, report)
        receipts[0]['prompt_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'receipt mismatch'):
            R.validate_receipts(rows, ids, report)

    def test_unpinned_cohort_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'cohort.json'
            path.write_text(json.dumps({'prompts': []}))
            with self.assertRaisesRegex(ValueError, 'Git blob changed'):
                R.cohort_rows(path)

    def test_zero_or_nonfinite_replay_state_rejected(self):
        y = np.array([[1., 0.], [0., 0.], [float('nan'), 1.]])
        with self.assertRaises(ValueError):
            R.rank_raw(y, 0, [1, 2])


if __name__ == '__main__':
    unittest.main()
