"""B3 runtime consumer: source-disjoint adapter training from native-tap packets.

Fixtures are synthetic and prove the local store/weight/persistence contract only.
They do not count as native model or Redmi evidence.
"""
import hashlib
import json
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np

from v13.common import atomic_write, dumps, file_hash, uid
from v13.contracts import packet
from v13.runtime import Runtime
from v13.operator import Operator
from v13 import latent_runtime


class B3LatentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.revisions = {"B1_DETAIL": "b1-test-revision", "B2_GIST": "b2-test-revision"}
        self.r.models.revision = lambda role: self.revisions[role]
        self.rng = np.random.default_rng(7)
        self.events = []

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _tap(self, event, role, vectors):
        token_ids = list(range(1, len(vectors) + 1))
        path = self.r.home / "data" / "blobs" / (uid("tap-fixture") + ".json")
        atomic_write(path, dumps({"token_ids": token_ids, "vectors": vectors.tolist()}))
        revision = self.revisions[role]
        tap_id = "lfm2.result_norm.final.v1" if role == "B1_DETAIL" else "qwen35.result_norm.final.v1"
        p = packet(
            "LatentTapPacket", role, event["event_id"], event["brain_generation_id"],
            [event["source_ref"]],
            role=role,
            source_ref=event["source_ref"],
            tap_id=tap_id,
            model_revision=revision,
            runner_revision="b10964",
            token_ids=token_ids,
            feature_path=str(path.relative_to(self.r.home)),
            feature_sha256=file_hash(path),
            shape=[len(vectors), len(vectors[0])],
            role_state="INDEPENDENT_READ_ONLY_PREFILL",
            receiver_read_authority=0,
            receiver_injection_authority=0,
            body_learning_authority=0,
            metrics={"token_count": len(token_ids), "fixture": True},
        )
        self.r.store.add_packet("LatentTapPacket", p)
        return p

    def _offer(self, event, role):
        p = packet(
            "OfferPacket", role, event["event_id"], event["brain_generation_id"],
            [event["source_ref"]],
            role=role,
            based_on_state_version=0,
            deadline_monotonic_ns=time.monotonic_ns() + 10**9,
            evidence_refs=[event["source_ref"]],
            offer={
                "summary": "candidate summary",
                "quotes": [],
                "uncertainty": "low",
                "needs_reentry": False,
            },
            confidence=0.7,
            model_revision=self.revisions[role],
            native_metrics={"duration_s": 0.01},
        )
        self.r.store.add_packet("OfferPacket", p)
        return p

    def _make_pairs(self, count=20):
        for i in range(count):
            event = self.r.store.event(self.r.session, f"paired latent source {i} value {i * 17 + 3}")
            self.r.store.message(
                self.r.session, event["event_id"], "assistant", "final test answer", "FINAL", {}
            )
            self.events.append(event)

        ordered = sorted(
            self.events,
            key=lambda e: hashlib.sha256(
                ("B1_TO_B2:" + e["source_ref"]["sha256"]).encode()
            ).hexdigest(),
        )
        labels = {e["event_id"]: (i % 2) for i, e in enumerate(ordered)}
        for i, event in enumerate(self.events):
            label = labels[event["event_id"]]
            b1 = self.rng.normal(0.0, 0.15, size=(4, 6)).astype(np.float32)
            b2 = self.rng.normal(0.0, 0.8, size=(3, 5)).astype(np.float32)
            b1[:, 0] += 1.0 if label else -1.0
            self._tap(event, "B1_DETAIL", b1)
            self._tap(event, "B2_GIST", b2)
            offer_b1 = self._offer(event, "B1_DETAIL")
            offer_b2 = self._offer(event, "B2_GIST")
            coalition = [offer_b2["packet_id"]] if label else [offer_b1["packet_id"]]
            decision = "INCORPORATE_B" if label else "INCORPORATE_A"
            focal = packet(
                "FocalCycle", "C4_FOCAL", event["event_id"], event["brain_generation_id"],
                [event["source_ref"]],
                cycle=1,
                decision=decision,
                coalition=coalition,
                signals={},
                budget={},
            )
            self.r.store.add_packet("FocalCycle", focal)
        return labels

    def test_training_persists_source_disjoint_candidate_without_activating_it(self):
        labels = self._make_pairs()
        result = latent_runtime.train_candidate(self.r, "B1_TO_B2")
        self.assertEqual(result["status"], "CANDIDATE_SAVED_NOT_ACTIVATED")
        self.assertGreater(result["adapter_weight_updates"], 0)
        self.assertGreater(result["adapter_parameter_diff_l2"], 0.0)
        self.assertEqual(result["body_weight_updates"], 0)
        self.assertEqual(result["latent_authority"], 0)
        self.assertFalse(result["active_bridge_changed"])
        self.assertTrue(result["reload_identical"])
        self.assertEqual(result["l1_gate"]["verdict"], "FAIL")
        self.assertTrue(
            {"EXACT", "CONTROL", "SYMBOLIC", "LATENT_SHUFFLED", "LATENT_RANDOM"}.issubset(
                set(result["l1_gate"]["missing_baselines"])
            )
        )
        self.assertFalse((self.r.home / "b3" / "B1_TO_B2.json").exists())
        candidate = latent_runtime.list_candidates(self.r, "B1_TO_B2")["candidates"][0]
        self.assertEqual(candidate["candidate_id"], result["candidate_id"])
        manifest_path = self.r.home / "b3" / "candidates" / (result["candidate_id"] + ".json")
        manifest = json.loads(manifest_path.read_text())
        self.assertTrue(manifest["training_evidence"]["source_disjoint"])
        self.assertGreater(manifest["training_evidence"]["parameter_diff_count"], 0)
        self.assertGreater(manifest["training_evidence"]["parameter_diff_l2"], 0.0)
        self.assertEqual(
            set(manifest["training_evidence"]["train_source_hashes"]).intersection(
                manifest["training_evidence"]["holdout_source_hashes"]
            ),
            set(),
        )
        self.assertEqual(len(labels), 20)

    def test_probe_is_counterfactual_and_never_applies_latent_authority(self):
        self._make_pairs()
        trained = latent_runtime.train_candidate(self.r, "B1_TO_B2")
        event = self.events[-1]
        report = latent_runtime.probe_candidate(
            self.r, "B1_TO_B2", trained["candidate_id"], event["event_id"]
        )
        self.assertEqual(report["status"], "COUNTERFACTUAL_READOUT_ONLY")
        self.assertFalse(report["applied"])
        self.assertFalse(report["receiver_effect_proven"])
        self.assertEqual(report["latent_authority"], 0)
        self.assertEqual(report["body_learning_authority"], 0)
        self.assertFalse(report["semantic_truth_authority"])
        self.assertIsNone(report["hardware_proof_id"])
        self.assertTrue(np.isfinite(report["candidate_delta_l2"]))
        self.assertFalse(report["l1_gate_pass"])
        saved = list((self.r.home / "b3" / "probes").glob("*.json"))
        self.assertEqual(len(saved), 1)
        self.assertEqual(json.loads(saved[0].read_text())["probe_id"], report["probe_id"])

    def test_operator_commands_expose_train_probe_candidates_and_status(self):
        self._make_pairs()
        trained_text = Operator(self.r).run(":callosum train B1_TO_B2")
        trained = json.loads(trained_text)
        self.assertEqual(trained["status"], "CANDIDATE_SAVED_NOT_ACTIVATED")
        candidate_text = Operator(self.r).run(":callosum candidates B1_TO_B2")
        self.assertEqual(json.loads(candidate_text)["count"], 1)
        probe_text = Operator(self.r).run(
            ":callosum probe B1_TO_B2 " + trained["candidate_id"]
        )
        self.assertEqual(json.loads(probe_text)["status"], "COUNTERFACTUAL_READOUT_ONLY")
        status = json.loads(Operator(self.r).run(":callosum status"))
        self.assertIn("latent_lab", status)
        self.assertEqual(status["latent_lab"]["active_bridge_authority"], 0)
        self.assertIn("LATENT blocked", status["gate"])

    def test_insufficient_pairs_fail_closed(self):
        self._make_pairs(count=2)
        result = latent_runtime.train_candidate(self.r, "B1_TO_B2")
        self.assertEqual(result["status"], "INSUFFICIENT_PAIRED_NATIVE_TAPS")
        self.assertEqual(result["adapter_weight_updates"], 0)
        self.assertFalse((self.r.home / "b3" / "candidates").exists())

    def test_candidate_id_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            latent_runtime.probe_candidate(
                self.r, "B1_TO_B2", "../outside", self.events[0]["event_id"] if self.events else "evt_none"
            )


if __name__ == "__main__":
    unittest.main()
