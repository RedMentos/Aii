"""Synthetic adversarial checks; no native/heldout utility is inferred."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from scripts import bp1_qad_v2_raw_audit as A


def pack(value):
    return (json.dumps(value, sort_keys=True) + "\n").encode()


class RawAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ds = self.root / "dataset.zip"
        self.native = self.root / "native.zip"
        self.refs = [{"row_id": f"R{i}", "arm": arm, "source_sha256": A.sha(f"source{i}".encode()),
                      "prompt": f"prompt{i}-{arm}", "target": "NOT_SENT"}
                     for i in range(11) for arm in ("no_offer", "offer")]
        ds = b"".join(pack(r) for r in self.refs)
        with zipfile.ZipFile(self.ds, "w") as z:
            z.writestr("bp1-output/heldout_paired.jsonl", ds)
        self.patch = patch.object(A, "DATASET_SHA", A.sha(ds))
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.proof = {"train_sha256": A.TRAIN_SHA, "train_rows": 25,
                      "native_training_executed": True, "heldout_files_opened": False,
                      "production_weight_authority": 0, "model_utility_proven": False,
                      "config": {"jepa_weight": 0, "max_steps": 2},
                      "master": {"master_sha256": A.MASTER_SHA},
                      "adapter": {"gguf_sha256": A.sha(b"adapter"), "lora_b_nonzero": 3},
                      "metrics": {"loss_history": [{"ce": 0.9}, {"ce": 0.6}]}}
        self.binding = {"dataset_sha256": A.sha(ds), "train_sha256": A.TRAIN_SHA,
                        "base_master_sha256": A.MASTER_SHA, "base_gguf_sha256": A.BASE_SHA,
                        "runner_sha256": A.RUNNER_SHA, "train_proof_sha256": A.sha(pack(self.proof)),
                        "adapter_gguf_sha256": A.sha(b"adapter"), "scales": {"base": 0.0, "candidate": 1.0},
                        "seed": 13, "temperature": 0, "production_weight_authority": 0,
                        "gates": dict(A.GATES)}
        self.predictions = [{"row_id": r["row_id"], "arm": r["arm"], "model": m,
                             "source_sha256": r["source_sha256"],
                             "prompt_sha256": A.sha(r["prompt"].encode()), "response": "{}"}
                            for m in ("base", "candidate") for r in self.refs]
        self.extra = {}
        self.build()

    def build(self):
        b, p = pack(self.binding), b"".join(pack(r) for r in self.predictions)
        entries = {"HEAD.txt": b"abc123\n", "BP1_QAD_TRAIN_PROOF.json": pack(self.proof),
                   "V2_BINDING.json": b, "RUN_BINDING.json": b,
                   "predictions.jsonl": p, "V2_PARTIAL_OR_FINAL_PREDICTIONS.jsonl": p,
                   "V2_SERVER_RAW.log": b"owned server\n",
                   "FINAL_MANIFEST.json": pack({"predictions_sha256": A.sha(p),
                      "binding_sha256": A.sha(b), "rows": 44, "source_pairs": 11,
                      "heldout_targets_sent_to_model": False, "model_utility_proven": False,
                      "gates": dict(A.GATES)}),
                   "V2_SCORES.json": pack({"predictions_sha256": A.sha(p),
                      "binding_sha256": A.sha(b), "model_utility_proven": False,
                      "gates": dict(A.GATES)})}
        entries.update({k + "_EXIT.txt": b"0\n" for k in A.EXITS})
        entries.update(self.extra)
        with zipfile.ZipFile(self.native, "w") as z:
            for name, value in entries.items():
                z.writestr(name, value)
        self.zip_sha = A.sha(self.native.read_bytes())

    def audit(self):
        return A.audit(self.native, self.ds, "abc123", self.zip_sha)

    def test_good_fixture_never_promotes(self):
        report = self.audit()
        self.assertEqual(report["responses"], 44)
        self.assertFalse(report["candidate_utility_proven"])

    def test_original_zip_sha_mismatch(self):
        with self.assertRaisesRegex(ValueError, "ZIP SHA"):
            A.audit(self.native, self.ds, "abc123", "0" * 64)

    def test_nonzero_native_exit(self):
        self.extra["V2_EXIT.txt"] = b"2\n"
        self.build()
        with self.assertRaisesRegex(ValueError, "V2 exit"):
            self.audit()

    def test_source_identity_tamper(self):
        self.predictions[0]["source_sha256"] = "f" * 64
        self.build()
        with self.assertRaisesRegex(ValueError, "source identity"):
            self.audit()

    def test_duplicate_prediction(self):
        self.predictions[1] = copy.deepcopy(self.predictions[0])
        self.build()
        with self.assertRaisesRegex(ValueError, "duplicate prediction"):
            self.audit()

    def test_adapter_zero_delta(self):
        self.proof["adapter"]["lora_b_nonzero"] = 0
        self.binding["train_proof_sha256"] = A.sha(pack(self.proof))
        self.build()
        with self.assertRaisesRegex(ValueError, "no adapter delta"):
            self.audit()

    def test_negative_gate_promotion(self):
        self.binding["gates"]["STEP2"] = "PASS"
        self.build()
        with self.assertRaisesRegex(ValueError, "negative gate"):
            self.audit()

    def test_zip_path_escape(self):
        self.extra["../escape"] = b"bad"
        self.build()
        with self.assertRaisesRegex(ValueError, "unsafe ZIP"):
            self.audit()

    def test_private_weight_in_raw_zip(self):
        self.extra["adapter.gguf"] = b"secret"
        self.build()
        with self.assertRaisesRegex(ValueError, "private weights"):
            self.audit()


if __name__ == "__main__":
    unittest.main()
