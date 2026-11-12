"""Synthetic nonsemantic PCM tests, host-only."""
import struct
import unittest
from v13.raw_ear_pcm import pcm16le_frames

class RawEarPcmTests(unittest.TestCase):
    def test_silence(self):
        frames = pcm16le_frames(bytes(640), 16000)
        self.assertEqual(len(frames), 1)
        self.assertEqual((frames[0].start_ms, frames[0].end_ms), (0, 20))
        self.assertEqual(frames[0].rms, 0)
        self.assertEqual(frames[0].zero_crossing_rate, 0)

    def test_two_frames_and_nonverbal_signal(self):
        signal = [10000 if i % 2 else -10000 for i in range(320)]
        frames = pcm16le_frames(bytes(640) + struct.pack('<320h', *signal), 16000)
        self.assertEqual(len(frames), 2)
        self.assertGreater(frames[1].rms, 0.3)
        self.assertGreater(frames[1].zero_crossing_rate, 0.99)
        self.assertEqual(frames[1].end_ms, 40)

    def test_reject_partial_or_misaligned(self):
        for pcm in (bytes(1), bytes(638)):
            with self.assertRaises(ValueError): pcm16le_frames(pcm, 16000)
        with self.assertRaises(ValueError): pcm16le_frames(bytes(640), 11025)

    def test_bounded_and_type_checked(self):
        with self.assertRaises(ValueError): pcm16le_frames(bytes(1280), 16000, max_duration_ms=20)
        with self.assertRaises(ValueError): pcm16le_frames(bytes(640), True)
        with self.assertRaises(ValueError): pcm16le_frames(bytearray(640), 16000)

if __name__ == '__main__': unittest.main()
