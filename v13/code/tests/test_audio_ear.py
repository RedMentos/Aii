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
from v13.audio_pcm_memory import pcm16_sample_buffer, zeroize_pcm16_buffer


class TestPCMBufferHygiene(unittest.TestCase):
    def test_observer_accepts_mutable_and_view_buffers_without_consuming_input(self):
        pcm = bytearray(struct.pack("<8h", -1000, 1000, -2000, 2000, -3000, 3000, -4000, 4000))
        original = bytes(pcm)
        expected = observe_pcm16(original, 8000, 25, consent=True, source_id="source")
        self.assertEqual(
            observe_pcm16(pcm, 8000, 25, consent=True, source_id="source"),
            expected,
        )
        self.assertEqual(
            observe_pcm16(memoryview(pcm), 8000, 25, consent=True, source_id="source"),
            expected,
        )
        self.assertEqual(bytes(pcm), original)

    def test_sample_copy_is_overwritten_and_owned_input_can_be_zeroized(self):
        pcm = bytearray(struct.pack("<4h", 100, -200, 300, -400))
        with pcm16_sample_buffer(pcm) as samples:
            retained_reference = samples
            self.assertEqual(list(samples), [100, -200, 300, -400])
        self.assertEqual(list(retained_reference), [0, 0, 0, 0])
        self.assertTrue(zeroize_pcm16_buffer(pcm))
        self.assertEqual(bytes(pcm), bytes(len(pcm)))
