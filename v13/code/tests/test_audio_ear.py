import struct
import unittest
from v13.audio_ear import observe_pcm16


class TestAudio(unittest.TestCase):
    def test_silence(self):
        p = observe_pcm16(b'\0\0' * 800, 8000, 100, consent=True, source_id='s')
        self.assertEqual(p['segments'][0]['end_ms'], 200)
        self.assertEqual(p['segments'][0]['acoustic']['rms'], 0)
        self.assertIsNone(p['segments'][0]['transcript'])

    def test_signal(self):
        pcm = struct.pack('<4h', -10000, 10000, -10000, 10000)
        p = observe_pcm16(pcm, 8000, 0, consent=True, source_id='s')
        self.assertGreater(p['segments'][0]['acoustic']['zero_crossing_rate'], 0)

    def test_consent(self):
        with self.assertRaises(PermissionError):
            observe_pcm16(b'\0\0', 8000, 0, consent=False, source_id='s')

    def test_budget(self):
        with self.assertRaises(ValueError):
            observe_pcm16(b'\0\0' * 8001, 8000, 0, consent=True, source_id='s', max_seconds=1)

    def test_malformed(self):
        with self.assertRaises(ValueError):
            observe_pcm16(b'\0', 8000, 0, consent=True, source_id='s')


if __name__ == '__main__':
    unittest.main()
