"""End-to-end synthetic RAW EAR/A5/B1/B2/JEF replay smoke (host-only).

Run from v13/code: python -m unittest tests.test_audio_e2e_smoke -v
No Android microphone, model, or action permissions are implied.
"""
import json
import math
import os
import struct
import tempfile
import unittest
from pathlib import Path

from v13.pcm_features import build_pcm_raw_ear
from v13.audio_a5 import audio_source_descriptor, persist_audio_percept
from v13.audio_views import acoustic_views


class DiskStore:
    """Minimal JSON fixture, NOT a replacement for the production event store."""
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write_source(self, descriptor):
        (self.root / "source.txt").write_text(descriptor, encoding="utf-8")

    def read_source(self, ref):
        return (self.root / "source.txt").read_text(encoding="utf-8")

    def add_packet(self, kind, value):
        if kind != "PerceptPacket":
            raise ValueError("unexpected packet kind")
        with (self.root / "packet.json").open("w", encoding="utf-8") as handle:
            json.dump(value, handle, allow_nan=False, sort_keys=True)
        return value

    def reload_packet(self):
        return json.loads((self.root / "packet.json").read_text(encoding="utf-8"))


class AudioEndToEndSmoke(unittest.TestCase):
    def test_nonzero_pcm_to_persisted_replay_and_hemispheres(self):
        rate = 16000
        # 400 ms of deterministic 440 Hz signal, no microphone or model.
        samples = [round(12000 * math.sin(2 * math.pi * 440 * i / rate))
                   for i in range(rate * 400 // 1000)]
        pcm = struct.pack("<" + "h" * len(samples), *samples)
        raw = build_pcm_raw_ear("synthetic:440hz", pcm, rate, provisional=False)
        descriptor = audio_source_descriptor(raw)
        ref = {"source_id": "synthetic_src", "sha256": "0" * 64,
               "char_start": 0, "char_end": len(descriptor), "modality": "text"}
        event = {"source_ref": ref, "event_id": "synthetic_event",
                 "brain_generation_id": "synthetic_generation"}
        with tempfile.TemporaryDirectory() as tmp:
            store = DiskStore(tmp)
            store.write_source(descriptor)
            packet = persist_audio_percept(store, event, raw)
            self.assertEqual(packet["modality"], "audio_acoustic")
            # A separate store instance simulates process restart/reload.
            reopened = DiskStore(tmp)
            replay = reopened.reload_packet()
            self.assertEqual(packet, replay)
            views = acoustic_views(replay, max_detail=32, gist_bins=4)
            self.assertEqual(views["jef_control"]["duration_ms"], 400)
            self.assertEqual(views["jef_control"]["frame_count"], 20)
            self.assertEqual(len(views["b1_detail"]), 20)
            self.assertEqual(len(views["b2_gist"]), 4)
            self.assertTrue(any(x["rms"] > 0.1 for x in views["b1_detail"]))
            self.assertTrue(all(x["covered_ms"] == 100 for x in views["b2_gist"]))
            self.assertTrue(all(x["rms"] is not None for x in views["b2_gist"]))
            self.assertTrue(all(x["voiced_probability"] is None
                                and x["non_speech_probability"] is None
                                and x["pitch_hz"] is None
                                for x in views["b1_detail"]))
            self.assertEqual(views["authority"], "SHADOW")
            self.assertEqual(views["jef_control"]["training_authority"], 0)
            self.assertEqual(views["jef_control"]["action_authority"], 0)
            # Even after persistence, corrupt RAW EAR/A5 divergence must fail.
            replay["segments"][0]["rms"] = 0.99
            with self.assertRaises(ValueError):
                acoustic_views(replay)

    def test_provisional_never_persists(self):
        raw = build_pcm_raw_ear("synthetic:silence", bytes(3200), 16000,
                                provisional=True)
        descriptor = audio_source_descriptor(raw)
        ref = {"source_id": "synthetic_src", "sha256": "0" * 64,
               "char_start": 0, "char_end": len(descriptor), "modality": "text"}
        with tempfile.TemporaryDirectory() as tmp:
            store = DiskStore(tmp)
            store.write_source(descriptor)
            with self.assertRaisesRegex(ValueError, "provisional"):
                persist_audio_percept(store, {"source_ref": ref,
                    "event_id": "evt", "brain_generation_id": "gen"}, raw)
            self.assertFalse((Path(tmp) / "packet.json").exists())


if __name__ == "__main__":
    unittest.main()
