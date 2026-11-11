"""A4/A5/B1/B2/JEF contract regression on synthetic PCM; host only, no Android proof."""
import math
import struct
import unittest

from v13.pcm_features import build_pcm_raw_ear
from v13.audio_a5 import audio_source_descriptor, persist_audio_percept
from v13.audio_views import acoustic_views


class FixtureStore:
    def __init__(self, descriptor):
        self.descriptor = descriptor
    def read_source(self, ref):
        return self.descriptor
    def add_packet(self, kind, value):
        return value


class AcousticIntegration(unittest.TestCase):
    def packet(self, pcm):
        raw = build_pcm_raw_ear("synthetic:a4-integration", pcm, 16000, provisional=False)
        descriptor = audio_source_descriptor(raw)
        ref = {"source_id": "src_synthetic", "sha256": "0"*64,
               "char_start": 0, "char_end": len(descriptor), "modality": "text"}
        return persist_audio_percept(FixtureStore(descriptor),
               {"source_ref": ref, "event_id": "evt_a4",
                "brain_generation_id": "gen_a4"}, raw)

    def test_onset_reaches_a4_with_b1_b2_jef(self):
        # 100 ms silence then 100 ms loud sine: genuine onset in frame RMS.
        samples = [0]*1600 + [int(20000*math.sin(2*math.pi*440*i/16000))
                                for i in range(1600)]
        pcm = struct.pack("<"+"h"*len(samples), *samples)
        packet = self.packet(pcm)
        views = acoustic_views(packet)
        self.assertEqual(views["authority"], "SHADOW")
        self.assertEqual(views["source_ref"], packet["source_ref"])
        self.assertEqual(views["jef_control"]["frame_count"], 10)
        self.assertEqual(views["jef_control"]["action_authority"], 0)
        self.assertTrue(views["a4_salience"])
        self.assertTrue(any(x["start_ms"] >= 100 for x in views["a4_salience"]))
        self.assertTrue(any(x["rms"] > 0 for x in views["b1_detail"]))
        self.assertTrue(any(x["rms"] > 0 for x in views["b2_gist"]))
        self.assertTrue(all(x["voiced_probability"] is None for x in views["b1_detail"]))

    def test_silence_does_not_claim_salience(self):
        views = acoustic_views(self.packet(bytes(6400)))
        self.assertEqual(views["a4_salience"], [])
        self.assertFalse(views["jef_control"]["android_capture_verified"])

    def test_a4_rejects_tampered_acoustic_evidence(self):
        packet = self.packet(bytes(6400))
        packet["segments"][0]["rms"] = .9
        with self.assertRaises(ValueError):
            acoustic_views(packet)


if __name__ == "__main__":
    unittest.main()
