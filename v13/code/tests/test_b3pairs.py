import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.contracts import packet
from v13.runtime import Runtime
from v13.operator import Operator
from v13.b3pairs import load_pair, training_batch, SCHEMA
from v13.common import atomic_write, dumps, file_hash


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
        path = self.r.home / "data/blobs" / (role + ".json")
        atomic_write(path, dumps({"token_ids": [11, 22], "vectors": vectors}))
        p = packet(
            "LatentTapPacket", role, self.event["event_id"],
            self.event["brain_generation_id"], [source_ref],
            role=role, source_ref=source_ref, tap_id=role + ".native.final",
            model_revision=role + ".rev1", runner_revision="fixture-runner",
            token_ids=[11, 22], feature_path=str(path.relative_to(self.r.home)),
            feature_sha256=file_hash(path), shape=[2, dim],
            role_state="INDEPENDENT_READ_ONLY_PREFILL",
            receiver_read_authority=0, receiver_injection_authority=0,
            body_learning_authority=0, metrics={}, local_prediction=None,
        )
        self.r.store.add_packet("LatentTapPacket", p)
        return p

    def test_pair_uses_same_event_source_and_keeps_native_token_spaces_separate(self):
        def tap(role, event, source_ref, deadline):
            return self._tap(role, source_ref)
        with patch.object(self.r.cognition, "tap", side_effect=tap):
            pair = self.r.cognition.tap_pair(self.event, time.monotonic() + 10)
        p = pair["packet"]
        self.assertEqual(p["packet_schema"], SCHEMA)
        self.assertEqual(p["event_id"], self.event["event_id"])
        self.assertEqual(p["source_ref"], self.event["source_ref"])
        self.assertEqual(p["dimensions"], {"B1_DETAIL": 3, "B2_GIST": 2})
        self.assertEqual(pair["receiver"]["pooled"], [1.5, 2.5])
        self.assertEqual(pair["authority"], {"native_read_only": True, "latent_injection": False, "body_learning": False})
        stored = self.r.store.one("SELECT payload FROM packets WHERE kind='B3PairedTapPacket' AND id=?", (p["packet_id"],))
        self.assertIsNotNone(stored)

        # Reopen the Store and rehydrate the hash-verified native feature files.
        self.r.close()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        restored = load_pair(self.r.cognition, p)
        self.assertEqual(restored["sender"]["states"], pair["sender"]["states"])
        batch = training_batch(self.r.cognition, [p], [1])
        self.assertEqual(batch["H"].shape, (1, 2, 3))
        self.assertEqual(batch["mask"].tolist(), [[1., 1.]])
        self.assertEqual(batch["Xr"].shape, (1, 2))
        self.assertEqual(batch["y"].tolist(), [1])
        self.assertEqual(batch["claim_limit"], "paired native read-only taps + explicit task labels; no receiver injection")
        reverse = training_batch(self.r.cognition, [p], [1], direction="B2_TO_B1")
        self.assertEqual(reverse["H"].shape, (1, 2, 2))
        self.assertEqual(reverse["Xr"].shape, (1, 3))
        self.assertEqual(reverse["sender_role"], "B2_GIST")

    def test_operator_pair_command_queues_same_event_for_both_bodies(self):
        event = self.r.store.event(self.r.session, "Operator paired tap source.")
        with patch.object(self.r, "last_answer", return_value={"event_id": event["event_id"]}), \\
             patch.object(self.r, "enqueue") as enqueue:
            result = Operator(self.r).run(":tap pair")
        enqueue.assert_called_once_with("tap_pair", event)
        self.assertIn("Keine Injection, kein Lernen", result)

    def test_rejects_cross_source_pair(self):
        def tap(role, event, source_ref, deadline):
            if role == "B1_DETAIL":
                return self._tap(role, source_ref)
            other = self.r.store.source("different source", "USER_INPUT")
            return self._tap(role, other)
        with patch.object(self.r.cognition, "tap", side_effect=tap):
            with self.assertRaisesRegex(ValueError, "source span mismatch"):
                self.r.cognition.tap_pair(self.event, time.monotonic() + 10)
        self.assertEqual(self.r.store.rows("SELECT * FROM packets WHERE kind='B3PairedTapPacket'"), [])


if __name__ == "__main__":
    unittest.main()
