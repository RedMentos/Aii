"""Explicit B3 promotion cannot consume a verdict-only L1 manifest."""
import json
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np

from v13 import b3degrade as D
from v13 import b3bridge as BB
from v13 import b3calibration as B
from v13.runtime import Runtime
from tests.test_b3_l1_baseline_completeness_review import complete


class B3L1PromotionEvidenceReview(unittest.TestCase):
    def test_label_only_or_incomplete_l1_is_not_a_gate(self):
        for gate in ({'verdict': 'PASS'},
                     {'verdict': 'PASS', 'criteria': {'receiver_ood': {'significant': True}}},
                     {'verdict': 'PASS', 'criteria': {k: {'significant': True}
                        for k in ('beats_no_message',)}, 'missing_baselines': [],
                        'invalid_evidence': []}):
            with self.subTest(gate=gate):
                self.assertFalse(D.gate_passed({'l1_gate': gate}, 'L1'))

    def test_complete_synthetic_l1_control_and_higher_rung_dependency(self):
        valid = BB.l1_gate(complete())
        self.assertEqual(valid['verdict'], 'PASS')
        self.assertTrue(D.gate_passed({'l1_gate': valid}, 'L1'))
        for rung in ('L2', 'L3', 'L4'):
            with self.subTest(rung=rung):
                self.assertFalse(D.gate_passed({rung.lower()+'_gate': {'verdict': 'PASS'}}, rung))
                self.assertFalse(D.gate_passed({'l1_gate': {'verdict': 'PASS'},
                                                rung.lower()+'_gate': {'verdict': 'PASS'}}, rung))
                self.assertTrue(D.gate_passed({'l1_gate': valid,
                                               rung.lower()+'_gate': {'verdict': 'PASS'}}, rung))

    def test_explicit_operator_cannot_promote_with_partial_l1_manifest(self):
        with tempfile.TemporaryDirectory() as t:
            r = Runtime(Path(t))
            try:
                r.sleep.cycle.set_policy('enabled', 'off')
                r.revisions = lambda: {'C3_LANGUAGE': 'c3', 'B1_DETAIL': 'rev-b1',
                                       'B2_GIST': 'rev-b2'}
                (r.home / 'b3').mkdir(exist_ok=True)
                rng = np.random.default_rng(0)
                x = rng.normal(size=(80, 8))
                cal = B.compute(x, x[::-1]*1.05, body_pair_id='B1->B2',
                                sender_revision='rev-b1', receiver_revision='rev-b2',
                                target_tap_id='lfm2.l8') | {
                                    'created_wall_time': time.time()-60}
                man = {'calibrated': True, 'created_wall_time': time.time()-60,
                       'sender_revision': 'rev-b1', 'receiver_revision': 'rev-b2',
                       'r': 16, 'K': 4, 'receiver_calibration': cal,
                       'sha256': '0'*64, 'train': {'samples': 80},
                       'l1_gate': {'verdict': 'PASS',
                                   'criteria': {'receiver_ood': {'significant': True}}}}
                (r.home / 'b3' / 'B1_TO_B2.json').write_text(json.dumps(man))
                with self.assertRaisesRegex(ValueError, 'GATE_L1'):
                    D.promote(r, 'B1_TO_B2', 'EXPLICIT_HUMAN')
                self.assertFalse(D.allowed(r.store, 'B1_TO_B2', 'L1'))
            finally:
                r.close()


if __name__ == '__main__':
    unittest.main()
