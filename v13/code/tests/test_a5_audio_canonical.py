"""Contract-bridge unit tests with isolated source-view dependency.

Exact repository end-to-end execution remains UNVERIFIED.
"""
import unittest
from unittest.mock import patch
from v13.a5_audio_canonical import canonical_audio_percept

REF = {'source_id': 'src_test', 'sha256': 'a'*64, 'char_start': 0, 'char_end': 12, 'modality': 'text'}

def view():
    return dict(authority='observation_only', android_action_allowed=False,
                body_inference_executed=False, runtime_activated=False,
                a3_recomputed=True, a4_salience=0.4, a3_embedding=[0.1, 0.2],
                time={'start_ms': 0, 'end_ms': 20, 'sample_rate_hz': 16000},
                acoustic={'rms': 0.1, 'pitch_hz': 0, 'speech_probability': 0},
                source_sha256='a'*64, feature_sha256='b'*64)

class CanonicalAudioTests(unittest.TestCase):
    def make(self):
        return canonical_audio_percept(None, None, {}, REF, event_id='evt_test', generation_id='gen_test')

    def test_real_contract_packet(self):
        with patch('v13.a5_audio_canonical.checked_projector_audio_view', return_value=view()):
            p = self.make()
        self.assertEqual(p['modality'], 'synthetic_audio')
        self.assertEqual(p['segments'][0]['transcript'], None)
        self.assertFalse(p['segments'][0]['android_action_allowed'])
        self.assertEqual(p['source_ref'], REF)

    def test_missing_context(self):
        with self.assertRaises(ValueError):
            canonical_audio_percept(None, None, {}, REF, event_id='', generation_id='gen_test')

    def test_action_authority_rejected(self):
        v = view(); v['android_action_allowed'] = True
        with patch('v13.a5_audio_canonical.checked_projector_audio_view', return_value=v):
            with self.assertRaises(PermissionError): self.make()

    def test_nonfinite_embedding_rejected(self):
        v = view(); v['a3_embedding'] = [float('nan')]
        with patch('v13.a5_audio_canonical.checked_projector_audio_view', return_value=v):
            with self.assertRaises(ValueError): self.make()

    def test_runtime_promotion_rejected(self):
        v = view(); v['runtime_activated'] = True
        with patch('v13.a5_audio_canonical.checked_projector_audio_view', return_value=v):
            with self.assertRaises(PermissionError): self.make()

if __name__ == '__main__':
    unittest.main()
