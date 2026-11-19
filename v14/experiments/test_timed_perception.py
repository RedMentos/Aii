"""Offline synthetic proof only; not Android mic or runtime integration."""
import unittest
from dataclasses import replace
from v14.experiments.timed_perception import AudioSource, pcm_digest, timed_audio_packets, validate_packet_sequence

class TimedAudioTests(unittest.TestCase):
    def setUp(self):
        self.samples = [1000,-1000]*401
        self.src = AudioSource('synthetic','consent-fixture',5000,8000,len(self.samples),pcm_digest(self.samples))
    def test_lossless_windows(self):
        p=timed_audio_packets(self.samples,self.src)
        self.assertEqual(len(p),3)
        self.assertTrue(validate_packet_sequence(p,self.src))
        self.assertEqual(p[-1]['sample_end'],len(self.samples))
        self.assertGreater(p[0]['zero_crossing_rate'],.99)
        self.assertIsNone(p[0]['teacher_asr'])
    def test_consent(self):
        with self.assertRaises(PermissionError):
            timed_audio_packets(self.samples,replace(self.src,consent_id=''))
    def test_source_tamper(self):
        with self.assertRaises(ValueError):
            timed_audio_packets(self.samples[:-1]+[123],self.src)
    def test_gap(self):
        p=timed_audio_packets(self.samples,self.src)
        p[1]['sample_start']+=1
        with self.assertRaises(ValueError):
            validate_packet_sequence(p,self.src)
    def test_provisional_and_replay(self):
        p=timed_audio_packets(self.samples,replace(self.src,provisional=True))
        self.assertEqual(p[0]['provenance'],'PROVISIONAL')
        p[0]['consent_id']='wrong'
        with self.assertRaises(PermissionError):
            validate_packet_sequence(p,self.src)

if __name__=='__main__': unittest.main()
