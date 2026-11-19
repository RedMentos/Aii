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

    def test_reject_malformed_source_consent_and_clock(self):
        data = b'\\0\\0' * 800
        valid = dict(source_id='fixture', pcm16le=data, sample_rate=8000,
                     start_ms=1000, end_ms=1100, consent_id='test-consent', final=True)
        for patch in ({'source_id': 7}, {'source_id': 'bad\\nsource'},
                      {'consent_id': 1}, {'consent_id': 'bad\\rconsent'},
                      {'start_ms': True}, {'end_ms': '1100'},
                      {'pcm16le': bytearray(data)}, {'final': 'yes'}):
            with self.subTest(patch=patch), self.assertRaises((ValueError, PermissionError)):
                raw_ear_packet(AudioFrame(**dict(valid, **patch)))

    def test_jef_rejects_untrusted_packet_shape(self):
        packet = raw_ear_packet(self.frame(b'\\0\\0' * 800))
        for patch in ({'source_ref': None}, {'source_ref': {'consent_id': 'x'}},
                      {'acoustic_features': None}, {'status': 'UNKNOWN'}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                jef_audio_observation(dict(packet, **patch))

if __name__=='__main__':
    unittest.main()
