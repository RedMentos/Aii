import tempfile
import json
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.contracts import packet
from v13.runtime import Runtime
from v13.b3pairs import load_pair, training_batch, SCHEMA
from v13.common import atomic_write, dumps, file_hash
from v13.operator import Operator


class FakeTokenizerRunner:
    def load(self, cancel_event, deadline):
        return None

    def _json(self, method, path, payload, deadline):
        return {"tokens": [{"id": i, "piece": ch} for i, ch in enumerate(payload["content"])]}


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
        text = self.r.store.read_source(source_ref)
        dim = 3 if role == "B1_DETAIL" else 2
        token_ids = list(range(len(text)))
        vectors = [[float(i + j + 1) for j in range(dim)] for i in token_ids]
        path = self.r.home / "data/blobs" / (role + ".json")
        atomic_write(path, dumps({"token_ids": token_ids, "vectors": vectors}))
        p = packet(
            "LatentTapPacket", role, self.event["event_id"],
            self.event["brain_generation_id"], [source_ref],
            role=role, source_ref=source_ref, tap_id=role + ".native.final",
            model_revision=role + ".rev1", runner_revision="fixture-runner",
            token_ids=token_ids, feature_path=str(path.relative_to(self.r.home)),
            feature_sha256=file_hash(path), shape=[len(token_ids), dim],
            role_state="INDEPENDENT_READ_ONLY_PREFILL",
            receiver_read_authority=0, receiver_injection_authority=0,
            body_learning_authority=0, metrics={}, local_prediction=None,
        )
        self.r.store.add_packet("LatentTapPacket", p)
        return p

    def _capture(self, event=None):
        def tap(role, e, source_ref, deadline):
            return self._tap(role, source_ref)
        with patch.object(self.r.cognition, "tap", side_effect=tap), \
             patch.object(self.r.pool, "get_tap", return_value=FakeTokenizerRunner()), \
             patch.object(self.r.pool, "unload"):
            return self.r.cognition.tap_pair(event or self.event, time.monotonic() + 10)

    def test_pair_uses_same_event_source_and_adaptive_gist_receiver(self):
        pair = self._capture()
        p = pair["packet"]
        self.assertEqual(p["packet_schema"], SCHEMA)
        self.assertEqual(p["event_id"], self.event["event_id"])
        self.assertEqual(p["source_ref"], self.event["source_ref"])
        self.assertEqual(p["dimensions"], {"B1_DETAIL": 3, "B2_GIST": 2})
        self.assertTrue(p["gist_readout"]["plan"]["lossless"])
        self.assertEqual(p["gist_readout"]["tap_packet_id"], p["tap_packet_ids"]["B2_GIST"])
        self.assertEqual(pair["receiver"]["gist_plan"]["mode"], "text")
        self.assertEqual(pair["authority"], {"native_read_only": True, "latent_injection": False, "body_learning": False})
        stored = self.r.store.one("SELECT payload FROM packets WHERE kind='B3PairedTapPacket' AND id=?", (p["packet_id"],))
        self.assertIsNotNone(stored)

        # Reopen the Store and rehydrate both hash-verified tap and Gist artifacts.
        self.r.close()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        restored = load_pair(self.r.cognition, p)
        self.assertEqual(restored["sender"]["states"], pair["sender"]["states"])
        self.assertEqual(restored["receiver"]["gist_states"], pair["receiver"]["gist_states"])
        batch = training_batch(self.r.cognition, [p], [1])
        source_text = self.r.store.read_source(self.event["source_ref"])
        self.assertEqual(batch["H"].shape, (1, len(source_text), 3))
        self.assertEqual(batch["Xr"].shape, (1, batch["receiver_max_slots"] * 2))
        self.assertEqual(batch["receiver_feature_mode"], "B2_GIST_ADAPTIVE_SLOTS_FLATTENED")
        self.assertEqual(batch["y"].tolist(), [1])
        reverse = training_batch(self.r.cognition, [p], [1], direction="B2_TO_B1")
        self.assertEqual(reverse["Xr"].shape, (1, 64 * 3))
        self.assertEqual(reverse["receiver_feature_mode"], "B1_DETAIL_FINE_NATIVE_SLOTS_FLATTENED")
        self.assertEqual(reverse["receiver_slot_counts"], [len(source_text)])
        self.assertEqual(reverse["sender_role"], "B2_GIST")
        self.assertIn("B1 native fine token slots", reverse["claim_limit"])
        gist_path = self.r.home / p["gist_readout"]["feature_path"]
        original = gist_path.read_text()
        gist_path.write_text(original + " ")
        with self.assertRaisesRegex(ValueError, "Gist artifact hash mismatch"):
            load_pair(self.r.cognition, p)

    def test_rejects_tokenizer_piece_drift(self):
        def tap(role, event, source_ref, deadline):
            return self._tap(role, source_ref)
        class DriftRunner(FakeTokenizerRunner):
            def _json(self, method, path, payload, deadline):
                return {"tokens": [{"id": i + 1, "piece": ch} for i, ch in enumerate(payload["content"])]}
        with patch.object(self.r.cognition, "tap", side_effect=tap), \
             patch.object(self.r.pool, "get_tap", return_value=DriftRunner()), \
             patch.object(self.r.pool, "unload"):
            with self.assertRaisesRegex(ValueError, "do not belong to this native tap"):
                self.r.cognition.tap_pair(self.event, time.monotonic() + 10)
        self.assertEqual(self.r.store.rows("SELECT * FROM packets WHERE kind='B3PairedTapPacket'"), [])

    def test_b3_pairs_command_reports_collection_not_training_authority(self):
        pair = self._capture()
        report = json.loads(Operator(self.r).run(":b3 pairs"))
        self.assertEqual(report["paired_native_samples"], 1)
        self.assertEqual(report["required_for_l1_training"], 64)
        self.assertEqual(report["remaining"], 63)
        self.assertTrue(report["task_labels_and_L0_baselines_required"])
        self.assertEqual(report["latent_injection_authority"], 0)

    def test_operator_pair_command_queues_same_event_for_both_bodies(self):
        event = self.r.store.event(self.r.session, "Operator paired tap source.")
        with patch.object(self.r, "last_answer", return_value={"event_id": event["event_id"]}), \
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
        with patch.object(self.r.cognition, "tap", side_effect=tap), \
             patch.object(self.r.pool, "get_tap", return_value=FakeTokenizerRunner()), \
             patch.object(self.r.pool, "unload"):
            with self.assertRaisesRegex(ValueError, "source span mismatch"):
                self.r.cognition.tap_pair(self.event, time.monotonic() + 10)
        self.assertEqual(self.r.store.rows("SELECT * FROM packets WHERE kind='B3PairedTapPacket'"), [])


if __name__ == "__main__":
    unittest.main()
