"""Synthetic tests only; no Android microphone or native model proof."""
import unittest
from v13.timed_audio_percept_candidate import acoustic_packet

class TestTimedAudioPercept(unittest.TestCase):
    def packet(self, **kw):
        return acoustic_packet([0.5,-0.5,0.0,0.5],8000,1200,source='synthetic',consent_scope='fixture',**kw)
    def test_timing(self):
        p=self.packet()
        self.assertEqual((p.start_ms,p.end_ms,p.sample_count),(1200,1201,4))
    def test_acoustic_features(self):
        p=self.packet()
        self.assertAlmostEqual(p.rms,0.4330127019)
        self.assertEqual(p.peak,0.5)
        self.assertGreater(p.zero_crossing_rate,0)
    def test_nonverbal_without_asr(self):
        self.assertIsNone(self.packet().speech_text)
    def test_provenanced_teacher_final(self):
        p=self.packet(speech_text='hello',transcript_provenance='teacher_asr',final=True)
        self.assertEqual((p.status,p.transcript_provenance),('final','teacher_asr'))
    def test_unprovenanced_text_rejected(self):
        with self.assertRaises(ValueError): self.packet(speech_text='hello')
    def test_no_consent(self):
        with self.assertRaises(PermissionError):
            acoustic_packet([0.1],8000,0,source='microphone',consent_scope='')
    def test_nonfinite_pcm_rejected(self):
        with self.assertRaises(ValueError):
            acoustic_packet([float('nan')],8000,0,source='fixture',consent_scope='fixture')
    def test_duration_bound(self):
        with self.assertRaises(ValueError):
            acoustic_packet([0.0]*80001,8000,0,source='fixture',consent_scope='fixture')

if __name__=='__main__': unittest.main()
