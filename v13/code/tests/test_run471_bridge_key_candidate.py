"""Run471 synthetic bridge identity and weight-integrity tests; no latent authority."""
import json
import os
import shutil
import sys
import tempfile
import unittest
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from v13.b3bridge import Bridge
from v13.bodyport import bridge_key
import run471_bridge_key_candidate as A


def specs():
    return {
        'B1_DETAIL': {'model_id': 'detail', 'revision': 'same-revision-A',
                      'sha256': 'a'*64, 'dims': 4, 'tokenizer': 'tok-A',
                      'capabilities': ['CAN_NATIVE_DECODE', 'CAN_TAP']},
        'B2_GIST': {'model_id': 'gist', 'revision': 'same-revision-B',
                    'sha256': 'b'*64, 'dims': 3, 'tokenizer': 'tok-B',
                    'capabilities': ['CAN_NATIVE_DECODE']}}


class ExactBridgeKeyCandidate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'B1_TO_B2'
        self.specs = specs()
        a, b = self.specs['B1_DETAIL'], self.specs['B2_GIST']
        self.man = Bridge(4, K=2, r=2, h=3, classes=2, seed=4).save(
            self.path, a['revision'], b['revision'], {
                'sender_bridge_key': bridge_key('B1_DETAIL', a),
                'receiver_bridge_key': bridge_key('B2_GIST', b),
                'l1_gate': {'verdict': 'FAIL'}})

    def test_exact_identity_and_real_numpy_weights_no_authority(self):
        result = A.verify_file(self.path, self.specs)
        self.assertTrue(result['identity_compatible'])
        self.assertEqual(result['status'], 'RUN471_EXACT_BRIDGE_IDENTITY_NO_AUTHORITY')
        self.assertEqual(result['latent_authority'], 0)
        self.assertEqual(result['b3_l1'], 'FAIL')
        self.assertFalse(result['canonical_gate_pass'])
        self.assertFalse(result['calibrated'])

    def test_same_revision_changed_weight_sha_rejected(self):
        changed = specs()
        changed['B1_DETAIL']['sha256'] = 'c'*64
        with self.assertRaisesRegex(ValueError, 'BRIDGE_EXACT_KEY_MISMATCH:sender'):
            A.verify_file(self.path, changed)

    def test_same_revision_changed_tokenizer_dims_or_capabilities_rejected(self):
        for key, value in [('tokenizer', 'tok-NEW'), ('dims', 999),
                           ('capabilities', ['CAN_NATIVE_DECODE'])]:
            with self.subTest(key=key):
                changed = specs()
                changed['B1_DETAIL'][key] = value
                with self.assertRaisesRegex(ValueError, 'BRIDGE_EXACT_KEY_MISMATCH:sender'):
                    A.verify_file(self.path, changed)

    def test_legacy_revision_only_manifest_fails_closed(self):
        legacy = dict(self.man)
        legacy.pop('sender_bridge_key')
        with self.assertRaisesRegex(ValueError, 'BRIDGE_EXACT_KEY_MISSING:sender'):
            A.exact_identity(legacy, self.specs)

    def test_bad_direction_and_missing_serving_dimensions_rejected(self):
        with self.assertRaisesRegex(ValueError, 'BRIDGE_DIRECTION_INVALID'):
            A.exact_identity(dict(self.man, direction='B2_TO_B3'), self.specs)
        changed = specs()
        changed['B2_GIST']['dims'] = None
        with self.assertRaisesRegex(ValueError, 'BRIDGE_SPEC_NOT_EXACT'):
            A.exact_identity(self.man, changed)

    def test_forged_l1_pass_does_not_grant_authority(self):
        changed = dict(self.man, l1_gate={'verdict': 'PASS'})
        (self.path.with_suffix('.json')).write_text(json.dumps(changed))
        result = A.verify_file(self.path, self.specs)
        self.assertEqual(result['l1_verdict'], 'PASS')
        self.assertEqual(result['latent_authority'], 0)
        self.assertEqual(result['b3_l1'], 'FAIL')
        self.assertFalse(result['canonical_gate_pass'])

    def test_forged_calibration_flag_refused(self):
        changed = dict(self.man, calibrated=True)
        self.path.with_suffix('.json').write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, 'BRIDGE_CALIBRATION_FLAG_MISMATCH'):
            A.verify_file(self.path, self.specs)

    def test_weights_tamper_refused(self):
        p = self.path.with_suffix('.npz')
        with np.load(p, allow_pickle=False) as original:
            tensors = {key: original[key].copy() for key in original.files}
        tensors['p_Q'][0, 0] += 0.5
        np.savez(p, **tensors)
        with self.assertRaisesRegex(ValueError, 'bridge weights do not match'):
            A.verify_file(self.path, self.specs)

    def test_direction_cannot_be_relabelled_by_filename(self):
        other = Path(self.tmp.name) / 'B2_TO_B1'
        shutil.copyfile(self.path.with_suffix('.json'), other.with_suffix('.json'))
        shutil.copyfile(self.path.with_suffix('.npz'), other.with_suffix('.npz'))
        with self.assertRaisesRegex(ValueError, 'BRIDGE_PATH_DIRECTION_MISMATCH'):
            A.verify_file(other, self.specs)

    def test_symlink_and_hardlink_refused(self):
        p = self.path.with_suffix('.npz')
        other = Path(self.tmp.name) / 'other.npz'
        p.rename(other)
        p.symlink_to(other)
        with self.assertRaisesRegex(ValueError, 'BRIDGE_FILE_MISSING_OR_SYMLINK'):
            A.verify_file(self.path, self.specs)
        p.unlink()
        os.link(other, p)
        with self.assertRaisesRegex(ValueError, 'BRIDGE_FILE_HARDLINK_OR_NONREGULAR'):
            A.verify_file(self.path, self.specs)


if __name__ == '__main__':
    unittest.main()
