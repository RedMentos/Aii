import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.contracts import packet
from v13.runtime import Runtime
from v13.b3pairs import capture_pair, SCHEMA


class PairedNativeTapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.event = self.r.store.event(self.r.session, "Shared source span for both native bodies.")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _tap(self, role, source_ref=None):
        source_ref = source_ref or self.event["source_ref"]
        dim = 3 if role == "B1_DETAIL" else 2
        vectors = [[float(i + j + 1) for j in range(dim)] for i in range(2)]
        p = packet(
            "LatentTapPacket", role, self.event["event_id"],
            self.event["brain_generation_id"], [source_ref],
            role=role, source_ref=source_ref, tap_id=role + ".native.final",
            model_revision=role + ".rev1", runner_revision="fixture-runner",
            token_ids=[11, 22], feature_path="data/blobs/" + role + ".json",
            feature_sha256="a" * 64, shape=[2, dim],
            role_state="INDEPENDENT_READ_ONLY_PREFILL",
            receiver_read_authority=0, receiver_injection_authority=0,
            body_learning_authority=0, metrics={}, local_prediction=None,
        )
        self.r.store.add_packet("LatentTapPacket", p)
        return p, {"token_ids": [11, 22], "vectors": vectors}

    def test_pair_uses_same_event_source_and_keeps_native_token_spaces_separate(self):
        rows = {}
        def tap(role, event, source_ref, deadline):
            p, data = self._tap(role, source_ref)
            rows[p["packet_id"]] = data
            return p
        with patch.object(self.r.cognition, "tap", side_effect=tap), \
             patch.object(self.r.cognition, "read_tap", side_effect=lambda p: rows[p["packet_id"]]):
            pair = capture_pair(self.r.cognition, self.event, time.monotonic() + 10)
        p = pair["packet"]
        self.assertEqual(p["schema"], SCHEMA)
        self.assertEqual(p["event_id"], self.event["event_id"])
        self.assertEqual(p["source_ref"], self.event["source_ref"])
        self.assertEqual(p["dimensions"], {"B1_DETAIL": 3, "B2_GIST": 2})
        self.assertEqual(pair["receiver"]["pooled"], [1.5, 2.5])
        self.assertEqual(pair["authority"], {"native_read_only": True, "latent_injection": False, "body_learning": False})
        stored = self.r.store.one("SELECT payload FROM packets WHERE kind='B3PairedTapPacket' AND id=?", (p["packet_id"],))
        self.assertIsNotNone(stored)

    def test_rejects_cross_source_pair(self):
        count = {"n": 0}
        def tap(role, event, source_ref, deadline):
            count["n"] += 1
            if role == "B1_DETAIL":
                return self._tap(role, source_ref)[0]
            other = self.r.store.source("different source", "USER_INPUT")
            return self._tap(role, other)[0]
        with patch.object(self.r.cognition, "tap", side_effect=tap), \
             patch.object(self.r.cognition, "read_tap", return_value={"token_ids": [11, 22], "vectors": [[1.0], [2.0]]}):
            with self.assertRaisesRegex(ValueError, "source span mismatch"):
                capture_pair(self.r.cognition, self.event, time.monotonic() + 10)
        self.assertEqual(self.r.store.rows("SELECT * FROM packets WHERE kind='B3PairedTapPacket'"), [])

if __name__ == "__main__":
    unittest.main()
