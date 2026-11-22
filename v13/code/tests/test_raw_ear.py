import unittest,struct
from v13.raw_ear import AudioFrame,raw_ear_packet,jef_audio_observation
class RawEarTests(unittest.TestCase):
    def frame(self,**changes):
        a=dict(source_id='synthetic:1',pcm16le=struct.pack('<160h',*([0]*160)),
          sample_rate=16000,start_ms=100,end_ms=110,consent_id='fixture-only',final=False)
        a.update(changes)
        return AudioFrame(**a)
    def test_timed_route(self):
        p=raw_ear_packet(self.frame());o=jef_audio_observation(p)
        self.assertEqual(o['kind'],'A5_AUDIO_OBSERVATION')
        self.assertEqual(o['status'],'PROVISIONAL')
        self.assertTrue(o['features']['silence_candidate'])
        self.assertIsNone(o['text'])
        self.assertFalse(o['may_train'])
    def test_final_no_training(self):
        p=raw_ear_packet(self.frame(final=True))
        self.assertEqual(p['status'],'FINAL')
        self.assertFalse(p['learning_eligible'])
    def test_consent(self):
        with self.assertRaises(PermissionError):raw_ear_packet(self.frame(consent_id=''))
    def test_duration(self):
        with self.assertRaises(ValueError):raw_ear_packet(self.frame(end_ms=300))
    def test_odd_pcm(self):
        with self.assertRaises(ValueError):raw_ear_packet(self.frame(pcm16le=b'\\x01'))
    def test_hash_and_energy(self):
        a=raw_ear_packet(self.frame())
        b=raw_ear_packet(self.frame(pcm16le=struct.pack('<160h',*([100]*160))))
        self.assertNotEqual(a['source_ref']['sha256'],b['source_ref']['sha256'])
        self.assertGreater(b['acoustic_features']['rms'],a['acoustic_features']['rms'])
    def test_untrusted(self):
        with self.assertRaises(ValueError):jef_audio_observation({'schema':'v13.a5.raw_ear/1'})
if __name__=='__main__':unittest.main()
