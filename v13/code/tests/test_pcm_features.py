"""Synthetic CPU-only regression; Android instrumentation remains unverified."""
import math
import struct
import unittest
from v13.pcm_features import build_pcm_raw_ear, extract_pcm_frames

class PCMFeaturesTest(unittest.TestCase):
    def test_silence(self):
        pkt = build_pcm_raw_ear("source:fixture", bytes(32000), 16000)
        self.assertEqual(len(pkt.frames), 50)
        self.assertTrue(all(f.rms == 0 for f in pkt.frames))
        self.assertTrue(all(f.pitch_hz is None for f in pkt.frames))
        self.assertIsNone(pkt.asr_text)
        self.assertFalse(pkt.to_record()["android_capture_verified"])

    def test_nonzero_signal(self):
        pcm = b"".join(struct.pack("<h", int(12000 * math.sin(2 * math.pi * 200 * i / 16000))) for i in range(16000))
        pkt = build_pcm_raw_ear("source:fixture", pcm, 16000, provisional=False)
        self.assertGreater(pkt.frames[0].rms, 0.2)
        self.assertEqual(pkt.to_record()["provenance"], "final")
        self.assertEqual(len(pkt.source_sha256), 64)

    def test_partial_frame(self):
        frames = extract_pcm_frames(bytes(2 * 400), 16000)
        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[-1].end_ms, 25)

    def test_bounded_rejection(self):
        for bad in (0, 9, 101, True, "20"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                extract_pcm_frames(bytes(32000), 16000, bad)
        with self.assertRaises(ValueError):
            extract_pcm_frames(b"\\x00", 16000)
        with self.assertRaises(ValueError):
            extract_pcm_frames(bytes(32000), 44100)
        with self.assertRaises(ValueError):
            extract_pcm_frames(bytes(2 * 16000 * 121), 16000)
