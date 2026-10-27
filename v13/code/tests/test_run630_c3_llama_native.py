"""Run630 source-only preflight/negative controls, no model or native runner required."""
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from scripts import run630_c3_llama_native as R


def gguf(tensors=120):
    return b"GGUF" + struct.pack("<IQQ", 3, tensors, 2)


class Run630Contracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.master = self.root / "master"
        self.master.mkdir()
        (self.master / "model.safetensors").write_bytes(b"dummy")
        self.model = self.root / "model.gguf"
        self.model.write_bytes(gguf(272))
        self.adapter = self.root / "adapter.gguf"
        self.adapter.write_bytes(gguf())
        self.cohort = self.root / "COHORT.json"
        self.cohort.write_text("{}")
        self.server = self.root / "llama-server"
        self.server.write_text("#!/bin/sh\nexit 0\n")
        self.server.chmod(0o700)
        self.proof = self.root / "proof.json"
        self.good = {
            "schema": "V13_RUN628_C3_LORA_CPU_PROOF_V1",
            "evidence_scope": "LINUX_NATIVE_C3_MASTER_LORA_CPU_EXPERIMENT",
            "gates": dict(R.GATES),
            "production_weight_authority": 0,
            "body_jepa_proven": False,
            "master": {"sha256": R.MASTER_SHA},
            "cohort_sha256": R.COHORT_SHA,
            "adapter_gguf_sha256": R.ADAPTER_SHA,
            "adapter_nonzero_lora_b_elements": 46080,
            "metrics": {"steps": 2, "jepa_weight": 0, "master_learned_recall": 0.0},
        }
        self.proof.write_text(json.dumps(self.good))

    def tearDown(self):
        self.tmp.cleanup()

    def digest(self, path):
        path = Path(path)
        if path == self.master / "model.safetensors":
            return R.MASTER_SHA
        if path == self.adapter:
            return R.ADAPTER_SHA
        if path == self.cohort:
            return R.COHORT_SHA
        return "a" * 64

    def check(self):
        with patch.object(R, "sha256", side_effect=self.digest):
            return R.verify_inputs(self.master, self.model, self.adapter, self.proof, self.server, self.cohort)

    def test_valid_frozen_source_and_gguf_structure(self):
        x = self.check()
        self.assertEqual(x["adapter_gguf_header"]["tensors"], 120)
        self.assertEqual(x["master_sha256"], R.MASTER_SHA)

    def test_adapter_master_cohort_tamper_refused(self):
        for path, msg in [(self.adapter, "adapter SHA"), (self.cohort, "cohort SHA"),
                          (self.master / "model.safetensors", "master SHA")]:
            with self.subTest(path=str(path)):
                def bad(p):
                    return "0" * 64 if Path(p) == path else self.digest(p)
                with patch.object(R, "sha256", side_effect=bad):
                    with self.assertRaisesRegex(ValueError, msg):
                        R.verify_inputs(self.master, self.model, self.adapter, self.proof, self.server, self.cohort)

    def test_invalid_gguf_and_source_scope_refused(self):
        self.adapter.write_bytes(b"BAD!" + gguf()[4:])
        with self.assertRaisesRegex(ValueError, "GGUF magic"):
            self.check()
        self.adapter.write_bytes(gguf(119))
        with self.assertRaisesRegex(ValueError, "tensor count drift"):
            self.check()
        self.adapter.write_bytes(gguf())
        p = dict(self.good, evidence_scope="CLAIMED_PRODUCTION")
        self.proof.write_text(json.dumps(p))
        with self.assertRaisesRegex(ValueError, "source proof scope"):
            self.check()

    def test_negative_gates_and_zero_recall_immutable(self):
        for change in ({"gates": dict(R.GATES, STEP2="PASS")},
                       {"production_weight_authority": 1},
                       {"metrics": dict(self.good["metrics"], master_learned_recall=1.0)}):
            with self.subTest(change=change):
                self.proof.write_text(json.dumps(dict(self.good, **change)))
                with self.assertRaises(ValueError):
                    self.check()

    def test_unreviewed_or_nonabsolute_server_refused(self):
        self.server.rename(self.root / "untrusted-server")
        with self.assertRaisesRegex(ValueError, "reviewed absolute executable"):
            self.check()
        self.server = self.root / "untrusted-server"
        self.server.rename(self.root / "llama-server")
        self.server = Path("llama-server")
        with self.assertRaisesRegex(ValueError, "reviewed absolute executable"):
            self.check()

    def test_finite_topk_and_delta(self):
        a = {"token_id": 7, "logprobs": {7: -0.5, 8: -1.0}}
        b = {"token_id": 7, "logprobs": {7: -0.4, 8: -1.0}}
        self.assertAlmostEqual(R._compare(a, b)["max_abs_logprob_delta"], 0.1)
        self.assertTrue(R._compare(a, a)["same_first_token"])
        with patch.object(R, "_json", return_value={
            "content": "x", "completion_probabilities": [{"id": 7, "top_logprobs": [
                {"id": 7, "logprob": float("nan")}]}]}):
            with self.assertRaisesRegex(RuntimeError, "nonfinite"):
                R._sample("http://127.0.0.1:1234", "synthetic")

    def test_preflight_fails_before_any_native_spawn(self):
        self.proof.write_text(json.dumps(dict(self.good, production_weight_authority=1)))
        with patch.object(R, "_start", side_effect=AssertionError("must not spawn")):
            with self.assertRaisesRegex(ValueError, "negative gates"):
                with patch.object(R, "sha256", side_effect=self.digest):
                    R.run(self.master, self.model, self.adapter, self.proof, self.cohort,
                          self.server, self.root / "out")


if __name__ == "__main__":
    unittest.main()
