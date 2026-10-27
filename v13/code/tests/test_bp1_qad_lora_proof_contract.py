"""Independent BP1 V2 train-proof contract counterexamples; synthetic software only."""
import copy
import json
import math
import tempfile
import unittest
from pathlib import Path

from scripts import bp1_qad_lora_eval as E
from tests.test_bp1_qad_lora_eval import binding, train_proof


def complete_proof():
    p = train_proof()
    p["metrics"].update({
        "rank": 2, "alpha": 4.0, "targets": ["v_proj", "out_proj"],
        "anchor_weight": 0.0, "final_ce": 2.0,
        "resumed": False, "base_generation": "BP1_QAD_C3_TRAIN_ONLY_SHADOW",
        "trained_on": "master",
    })
    p["adapter"].update({
        "peft_sha256": "c" * 64, "gguf_bytes": 1024,
        "gguf_tensors": 4, "lora_b_tensors": 2,
    })
    return p


def verify(proof):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "train-proof.json"
        path.write_text(json.dumps(proof, sort_keys=True), encoding="utf-8")
        b = binding()
        b["train_proof_sha256"] = E.S.sha(path.read_bytes())
        return E.verify_train_proof(b, path)


class ProofContractReview(unittest.TestCase):
    def test_complete_declared_train_proof_is_accepted_but_not_native_evidence(self):
        self.assertTrue(verify(complete_proof()))

    def test_frozen_optimizer_metric_drift_rejected(self):
        mutations = {
            "rank": 99, "alpha": 1.0,
            "targets": ["v_proj", "fake_proj"],
            "anchor_weight": 0.5, "final_ce": float("nan"),
            "resumed": True, "base_generation": "OTHER",
            "trained_on": "other GGUF",
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                p = complete_proof()
                p["metrics"][field] = value
                with self.assertRaises(ValueError):
                    verify(p)

    def test_adapter_export_metadata_drift_rejected(self):
        mutations = {
            "peft_sha256": "not-sha", "gguf_bytes": 0,
            "gguf_tensors": 0, "lora_b_tensors": 0,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                p = complete_proof()
                p["adapter"][field] = value
                with self.assertRaises(ValueError):
                    verify(p)


if __name__ == "__main__":
    unittest.main()
