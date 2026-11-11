"""Synthetic production-table acoustic replay bridge tests (no Redmi claim)."""
import json
import math
import struct
import unittest

from v13.audio_a5 import audio_source_descriptor, persist_audio_percept
from v13.audio_store_bridge import replay_acoustic_packet
from v13.pcm_features import build_pcm_raw_ear


class TableFixture:
    """Mimics Store.one row shape; deliberately NOT a production DB."""
    def __init__(self, descriptor):
        self.descriptor = descriptor
        self.rows = {}
        self.revoked = False

    def read_source(self, ref):
        if self.revoked:
            raise ValueError("source revoked")
        return self.descriptor

    def add_packet(self, kind, packet):
        self.rows[packet["packet_id"]] = {
            "kind": kind, "event_id": packet["event_id"],
            "generation_id": packet["brain_generation_id"],
            "payload": json.dumps(packet, allow_nan=False)}
        return packet

    def one(self, sql, args):
        assert "FROM packets WHERE id=?" in sql
        return self.rows.get(args[0])


class AcousticStoreBridgeTests(unittest.TestCase):
    def setUp(self):
        rate = 16000
        samples = [round(12000 * math.sin(2 * math.pi * 440 * i / rate))
                   for i in range(3200)]
        pcm = struct.pack("<" + "h" * len(samples), *samples)
        self.raw = build_pcm_raw_ear("synthetic:440", pcm, rate, provisional=False)
        descriptor = audio_source_descriptor(self.raw)
        self.store = TableFixture(descriptor)
        ref = {"source_id": "synthetic", "sha256": "0" * 64,
               "char_start": 0, "char_end": len(descriptor), "modality": "text"}
        self.packet = persist_audio_percept(self.store, {
            "source_ref": ref, "event_id": "synthetic_event",
            "brain_generation_id": "synthetic_generation"}, self.raw)

    def test_replay_returns_shadow_views(self):
        result = replay_acoustic_packet(self.store, self.packet["packet_id"])
        self.assertEqual(result["authority"], "SHADOW")
        self.assertEqual(result["jef_control"]["frame_count"], 10)
        self.assertTrue(result["b1_detail"][0]["rms"] > 0)
        self.assertEqual(result["jef_control"]["action_authority"], 0)

    def test_revocation_and_descriptor_tamper_refused(self):
        self.store.revoked = True
        with self.assertRaisesRegex(ValueError, "revoked"):
            replay_acoustic_packet(self.store, self.packet["packet_id"])
        self.store.revoked = False
        self.store.descriptor = "v13.audio_pcm_sha256:" + "0" * 64 + "\\n"
        with self.assertRaisesRegex(ValueError, "descriptor"):
            replay_acoustic_packet(self.store, self.packet["packet_id"])

    def test_row_and_authority_tamper_refused(self):
        row = self.store.rows[self.packet["packet_id"]]
        row["event_id"] = "forged"
        with self.assertRaisesRegex(ValueError, "event/generation"):
            replay_acoustic_packet(self.store, self.packet["packet_id"])
        row["event_id"] = self.packet["event_id"]
        obj = json.loads(row["payload"])
        obj["training_authority"] = 1
        row["payload"] = json.dumps(obj)
        with self.assertRaisesRegex(ValueError, "learning/receiver"):
            replay_acoustic_packet(self.store, self.packet["packet_id"])


if __name__ == "__main__":
    unittest.main()
