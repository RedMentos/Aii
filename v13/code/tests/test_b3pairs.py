import tempfile
import json
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.contracts import packet, validate
from v13.runtime import Runtime
from v13.b3pairs import load_pair, training_batch, SCHEMA
from v13.common import atomic_write, dumps, file_hash
from v13.operator import Operator


class FakeTokenizerRunner:
    def __init__(self, pieces=None, token_ids=None):
        self.pieces = pieces
        self.token_ids = token_ids

    def load(self, cancel_event, deadline):
        return None

    def _json(self, method, path, payload, deadline):
        if self.pieces is None:
            return {"tokens": [{"id": i, "piece": ch} for i, ch in enumerate(payload["content"])]}
        if "".join(self.pieces) != payload["content"]:
            raise ValueError("fixture pieces do not reproduce source")
        ids = self.token_ids if self.token_ids is not None else list(range(len(self.pieces)))
        return {"tokens": [{"id": token_id, "piece": piece}
                           for token_id, piece in zip(ids, self.pieces)]}


class PairedNativeTapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.event = self.r.store.event(self.r.session, "Shared source span for both native bodies.")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _tap(self, role, source_ref=None, event=None, token_ids=None):
        event = event or self.event
        source_ref = source_ref or event["source_ref"]
        text = self.r.store.read_source(source_ref)
        dim = 3 if role == "B1_DETAIL" else 2
        token_ids = list(range(len(text))) if token_ids is None else list(token_ids)
        vectors = [[float(i + j + 1) for j in range(dim)] for i in range(len(token_ids))]
        path = self.r.home / "data/blobs" / (role + ".json")
        atomic_write(path, dumps({"token_ids": token_ids, "vectors": vectors}))
        p = packet(
            "LatentTapPacket", role, event["event_id"],
            event["brain_generation_id"], [source_ref],
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

    def _capture(self, event=None, b2_pieces=None):
        b2_ids = None if b2_pieces is None else list(range(1000, 1000 + len(b2_pieces)))

        def tap(role, e, source_ref, deadline):
            ids = b2_ids if role == "B2_GIST" and b2_ids is not None else None
            return self._tap(role, source_ref, e, token_ids=ids)

        runners = ([FakeTokenizerRunner(b2_pieces, b2_ids), FakeTokenizerRunner()]
                   if b2_pieces is not None else
                   [FakeTokenizerRunner(), FakeTokenizerRunner()])
        with patch.object(self.r.cognition, "tap", side_effect=tap), \
             patch.object(self.r.pool, "get_tap", side_effect=runners), \
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
        self.assertTrue(p["fine_readout"]["plan"]["lossless"])
        self.assertEqual(p["fine_readout"]["tap_packet_id"], p["tap_packet_ids"]["B1_DETAIL"])
        self.assertEqual(len(p["fine_readout"]["plan"]["slots"]), p["token_counts"]["B1_DETAIL"])
        self.assertEqual(p["native_token_readout"]["tap_id"], p["tap_ids"]["B2_GIST"])
        self.assertEqual(p["native_token_readout"]["native_tokens"], p["gist_readout"]["plan"]["native_tokens"])
        self.assertEqual(len(p["native_token_readout"]["slots"]), p["token_counts"]["B2_GIST"])
        self.assertTrue(p["native_token_readout"]["lossless"])
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
        self.assertEqual(restored["reverse_receiver"]["fine_plan"], pair["reverse_receiver"]["fine_plan"])
        self.assertEqual(restored["receiver"]["native_token_plan"], pair["receiver"]["native_token_plan"])
        batch = training_batch(self.r.cognition, [p], [1])
        source_text = self.r.store.read_source(self.event["source_ref"])
        self.assertEqual(batch["H"].shape, (1, len(source_text), 3))
        self.assertEqual(batch["Xr"].shape, (1, batch["receiver_max_slots"] * 2))
        self.assertEqual(batch["receiver_feature_mode"], "B2_GIST_ADAPTIVE_SLOTS_FLATTENED")
        self.assertEqual(batch["token_alignment_contract"], "CHARACTER_INTERVAL_INTERSECTION;NO_TOKEN_INDEX_EQUIVALENCE")
        self.assertEqual(batch["source_span_alignments"][0]["covered_chars"], len(source_text))
        self.assertEqual(batch["source_span_alignments"][0]["coverage_ratio"], 1.0)
        self.assertFalse(batch["receiver_input_embedding_rows_available"])
        self.assertEqual(batch["y"].tolist(), [1])
        reverse = training_batch(self.r.cognition, [p], [1], direction="B2_TO_B1")
        self.assertEqual(reverse["Xr"].shape, (1, 64 * 3))
        self.assertEqual(reverse["receiver_feature_mode"], "B1_DETAIL_FINE_NATIVE_SLOTS_FLATTENED")
        self.assertEqual(reverse["receiver_slot_counts"], [len(source_text)])
        self.assertEqual(reverse["sender_role"], "B2_GIST")
        self.assertEqual(reverse["source_span_alignments"][0]["covered_chars"], len(source_text))
        self.assertEqual(reverse["sender_token_ids"][0], p["native_token_readout"]["token_ids"])
        self.assertEqual(reverse["receiver_token_ids"][0], p["fine_readout"]["plan"]["token_ids"])
        self.assertIn("B1 fine token slots", reverse["claim_limit"])
        gist_path = self.r.home / p["gist_readout"]["feature_path"]
        original = gist_path.read_text()
        gist_path.write_text(original + " ")
        with self.assertRaisesRegex(ValueError, "Gist artifact hash mismatch"):
            load_pair(self.r.cognition, p)


    def test_b2_native_token_spans_align_different_tokenizers_by_source_characters(self):
        source_text = self.r.store.read_source(self.event["source_ref"])
        pieces = ["Shared", " source", " span", " for", " both", " native", " bodies", "."]
        self.assertEqual("".join(pieces), source_text)
        pair = self._capture(b2_pieces=pieces)
        packet_value = pair["packet"]
        native = packet_value["native_token_readout"]
        self.assertEqual(native["token_ids"], list(range(1000, 1000 + len(pieces))))
        self.assertEqual(len(native["slots"]), len(pieces))
        self.assertEqual(native["slots"][0]["source_ref"]["char_start"],
                         self.event["source_ref"]["char_start"])
        self.assertEqual(native["slots"][-1]["source_ref"]["char_end"],
                         self.event["source_ref"]["char_end"])

        forward = training_batch(self.r.cognition, [packet_value], [1])
        alignment = forward["source_span_alignments"][0]
        self.assertEqual(alignment["method"], "CHARACTER_INTERVAL_INTERSECTION")
        self.assertEqual(alignment["covered_chars"], len(source_text))
        self.assertEqual(alignment["source_chars"], len(source_text))
        self.assertGreater(alignment["overlap_pair_count"], len(pieces))
        self.assertEqual(forward["sender_token_ids"][0], list(range(len(source_text))))
        self.assertEqual(forward["receiver_token_ids"][0], native["token_ids"])
        first_receiver_id = native["token_ids"][0]
        first_receiver_overlaps = [
            row for row in alignment["pairs"] if row["receiver_token_id"] == first_receiver_id
        ]
        self.assertGreater(len(first_receiver_overlaps), 1)

        reverse = training_batch(self.r.cognition, [packet_value], [1], direction="B2_TO_B1")
        self.assertEqual(reverse["sender_token_ids"][0], native["token_ids"])
        self.assertEqual(reverse["receiver_token_ids"][0], list(range(len(source_text))))
        self.assertEqual(reverse["source_span_alignments"][0]["covered_chars"], len(source_text))

    def test_b3_packet_rejects_b2_native_token_span_gap(self):
        pair = self._capture()
        broken = json.loads(json.dumps(pair["packet"]))
        broken["native_token_readout"]["slots"][0]["source_ref"]["char_end"] -= 1
        with self.assertRaisesRegex(ValueError, "B3 pair B2 native token source coverage"):
            validate("B3PairedTapPacket", broken)

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
        duplicate_capture = self._capture()
        self.assertEqual(pair["body_pair_id"], duplicate_capture["body_pair_id"])
        self.assertEqual(load_pair(self.r.cognition, pair["packet"])["body_pair_id"], pair["body_pair_id"])
        with self.assertRaisesRegex(ValueError, "duplicate body_pair_id"):
            training_batch(self.r.cognition, [pair["packet"], duplicate_capture["packet"]], [1, 1])
        repeated_text_event = self.r.store.event(self.r.session, "Shared source span for both native bodies.")
        repeated_text_capture = self._capture(repeated_text_event)
        self.assertNotEqual(pair["body_pair_id"], repeated_text_capture["body_pair_id"])
        with self.assertRaisesRegex(ValueError, "same exact source span"):
            training_batch(self.r.cognition, [pair["packet"], repeated_text_capture["packet"]], [1, 1])
        report = json.loads(Operator(self.r).run(":b3 pairs"))
        self.assertEqual(report["paired_native_samples"], 1)
        self.assertEqual(report["captured_pair_packets"], 3)
        self.assertEqual(report["ignored_legacy_packets"], 0)
        self.assertEqual(report["unique_body_pair_ids"], 2)
        self.assertEqual(report["required_for_l1_training"], 64)
        self.assertEqual(report["remaining"], 63)
        self.assertEqual(report["b1_detail_fine_slots"]["budget"], 64)
        self.assertGreater(report["b1_detail_fine_slots"]["min"], report["b2_gist_adaptive_slots"]["min"])
        self.assertFalse(report["pair_collection_threshold_met"])
        self.assertTrue(report["task_labels_and_L0_baselines_required"])
        self.assertTrue(report["shadow_trainer_available"])
        self.assertEqual(report["l1_utility_gate"], "NOT_EVALUATED_BY_PAIR_COLLECTION_STATUS")
        self.assertEqual(report["latent_injection_authority"], 0)

    def test_rejects_b1_fine_tokenizer_piece_drift(self):
        def tap(role, event, source_ref, deadline):
            return self._tap(role, source_ref)
        class DriftRunner(FakeTokenizerRunner):
            def _json(self, method, path, payload, deadline):
                return {"tokens": [{"id": i + 1, "piece": ch} for i, ch in enumerate(payload["content"])]}
        with patch.object(self.r.cognition, "tap", side_effect=tap), \
             patch.object(self.r.pool, "get_tap", side_effect=[FakeTokenizerRunner(), DriftRunner()]), \
             patch.object(self.r.pool, "unload"):
            with self.assertRaisesRegex(ValueError, "B1 Fine tokenizer pieces"):
                self.r.cognition.tap_pair(self.event, time.monotonic() + 10)
        self.assertEqual(self.r.store.rows("SELECT * FROM packets WHERE kind='B3PairedTapPacket'"), [])

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
