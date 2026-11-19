"""Bounded RAW EAR tests: synthetic PCM only; no microphone/Redmi claim."""
import math
import struct
import unittest
from v13.raw_ear import AudioFrame, raw_ear_packet, jef_audio_observation

class RawEarBounds(unittest.TestCase):
    def frame(self, data, rate=8000, consent='local-test'):
        return AudioFrame('synthetic-source', data, rate, 1000,
                          1000+round(len(data)/2/rate*1000), consent, True)

    def test_timed_envelope_and_jef_contract(self):
        samples=[int(10000*math.sin(2*math.pi*200*i/8000)) for i in range(800)]
        p=raw_ear_packet(self.frame(struct.pack('<800h',*samples)))
        self.assertEqual(len(p['acoustic_features']['envelope_20ms']),5)
        self.assertEqual(p['status'],'FINAL')
        j=jef_audio_observation(p)
        self.assertFalse(j['may_train'])
        self.assertIsNone(j['text'])

    def test_reject_missing_consent(self):
        with self.assertRaises(PermissionError):
            raw_ear_packet(self.frame(b'\0\0'*800,consent=''))

    def test_reject_oversize(self):
        with self.assertRaises(ValueError):
            raw_ear_packet(self.frame(b'\0\0'*(1024*1024+1)))

    def test_reject_overlong(self):
        with self.assertRaises(ValueError):
            raw_ear_packet(self.frame(b'\0\0'*(8000*31)))

if __name__=='__main__':
    unittest.main()
