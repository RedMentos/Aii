"""Synthetic, no-model adversarial tests for P2X fourstep offline artifact audit."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import p2x_fourstep_evidence_audit as A


def fake_records():
    train = []
    for label in A.P.LABELS:
        for i in range(5):
            name = f"P2X{label}{i:02d}"
            train.append({"id": name,
                          "arm": "both_exact" if label != "UNKNOWN" else "shuffled",
                          "target_action": label,
                          "messages": [{"role": "user", "content": "Project " + name}]})
    return {"train.jsonl": train,
            "validation_inputs.jsonl": [{"id": "P2XVALIDATION"}]}


def fake_report(root, records):
    selected = A.F.select_balanced(records)
    gguf = root / "adapter.gguf"
    safe = root / "adapter_model.safetensors"
    gguf.write_bytes(b"synthetic GGUF adapter for audit test only")
    safe.write_bytes(b"synthetic PEFT adapter for audit test only")
    history = [{"step": i, "ce": 1.0 / i, "anchor_kl": 0.0, "jepa": None}
               for i in range(1, 5)]
    return {"schema": A.F.SCHEMA,
            "status": "SIXTEEN_EXAMPLE_FOUR_STEP_LORA_PILOT_ONLY",
            "seed": A.F.SEED, "steps": 4, "examples": 16,
            "source_master_sha256": A.P.MASTER_SHA["model.safetensors"],
            "fixture_sha256": A.P.FIXTURE_SHA,
            "train_jsonl_sha256": A.P.EXPORT_SHA["train.jsonl"],
            "selected": [{"id": row["id"], "arm": row["arm"],
                          "target_action": row["target_action"],
                          "record_sha256": A.P.sha(A.P.canonical(row))}
                         for row in selected],
            "token_lengths": [150] * 16,
            "resources": {"disk_free_bytes": 6_000_000_000,
                          "memory_available_bytes": 6_000_000_000},
            "metrics": {"steps": 4, "rank": 2, "alpha": 4,
                        "targets": ["v_proj", "out_proj"],
                        "anchor_weight": 0.0, "jepa_weight": 0.0,
                        "base_generation": 0, "trainable_parameter_count": 83968,
                        "master_learned_recall": .25, "final_ce": .25,
                        "seconds": 120.0, "peak_rss_mb": 2500.0,
                        "resumed": False, "dataset_hash": "abcd1234",
                        "trained_on": "master",
                        "device": {"backend": "torch-cpu", "threads": 2},
                        "loss_history": history},
            "files": {"gguf": str(gguf), "safetensors": str(safe),
                      "gguf_sha256": A.P.file_sha(gguf),
                      "safetensors_sha256": A.P.file_sha(safe),
                      "gguf_tensors": 44, "bytes": gguf.stat().st_size},
            "adapter_gguf_path": str(gguf),
            "adapter_gguf_sha256": A.P.file_sha(gguf),
            "elapsed_s": 180.0, "training_pilot": True,
            "ag6_approved": False, "production_activation": False,
            "p0x_used_for_training": False, "step2_utility_pass": False,
            "jepa_weight": 0, "redmi_measured": False,
            "whole_system_complete": False}


class OfflineAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.records = fake_records()
        self.report = fake_report(self.root, self.records)
        self.patcher = patch.object(A.P, "read_frozen", return_value=self.records)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def check(self, report=None, root=None):
        return A.audit(self.report if report is None else report,
                       self.root, self.root if root is None else root)

    def test_synthetic_positive_is_only_artifact_consistency(self):
        out = self.check()
        self.assertEqual(out["status"], A.STATUS)
        self.assertEqual(len(out["selected_record_sha256"]), 16)
        self.assertFalse(out["native_training_independently_observed"])
        self.assertFalse(out["native_utility_proven"])
        self.assertFalse(out["ag6_approved"])
        self.assertEqual(out["step2_status"], "UTILITY_FAIL")

    def test_modified_gguf_bytes_red(self):
        (self.root / "adapter.gguf").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "ADAPTER_BYTES"):
            self.check()

    def test_modified_peft_safetensors_red(self):
        (self.root / "adapter_model.safetensors").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "ADAPTER_BYTES"):
            self.check()

    def test_selected_row_source_mismatch_red(self):
        r = copy.deepcopy(self.report)
        r["selected"][0]["record_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "FROZEN_REPORT"):
            self.check(r)

    def test_fake_four_step_metrics_red(self):
        for mutation in ("step", "nan", "ce", "alpha", "trained_on"):
            with self.subTest(mutation=mutation):
                r = copy.deepcopy(self.report)
                if mutation == "step":
                    r["metrics"]["loss_history"][3]["step"] = 3
                elif mutation == "nan":
                    r["metrics"]["loss_history"][0]["ce"] = float("nan")
                elif mutation == "ce":
                    r["metrics"]["final_ce"] = .99
                elif mutation == "alpha":
                    r["metrics"]["alpha"] = 16
                else:
                    r["metrics"]["trained_on"] = "gguf"
                with self.assertRaisesRegex(ValueError, "METRICS|HISTORY"):
                    self.check(r)

    def test_boolean_as_numeric_red(self):
        for path in ("steps", "jepa_weight"):
            r = copy.deepcopy(self.report)
            r[path] = False
            with self.assertRaises(ValueError):
                self.check(r)
        r = copy.deepcopy(self.report)
        r["token_lengths"][0] = True
        with self.assertRaisesRegex(ValueError, "TOKEN_LENGTH"):
            self.check(r)

    def test_forced_authority_red(self):
        for key in ("ag6_approved", "production_activation", "redmi_measured"):
            r = copy.deepcopy(self.report)
            r[key] = True
            with self.assertRaisesRegex(ValueError, "AUTHORITY"):
                self.check(r)

    def test_symlink_and_escape_red(self):
        gguf = self.root / "adapter.gguf"
        real = self.root / "real.gguf"
        gguf.rename(real)
        gguf.symlink_to(real)
        with self.assertRaisesRegex(ValueError, "SYMLINK"):
            self.check()
        gguf.unlink()
        real.rename(gguf)
        with tempfile.TemporaryDirectory() as outside:
            with self.assertRaisesRegex(ValueError, "CONFINEMENT"):
                self.check(root=outside)

    def test_missing_peft_red(self):
        (self.root / "adapter_model.safetensors").unlink()
        with self.assertRaisesRegex(ValueError, "MISSING_FILE"):
            self.check()

    def test_nonfinite_resources_red(self):
        r = copy.deepcopy(self.report)
        r["resources"]["memory_available_bytes"] = float("inf")
        with self.assertRaisesRegex(ValueError, "RESOURCE"):
            self.check(r)

    def test_cli_red_is_exclusive_and_never_promotes(self):
        output = self.root / "red.json"
        args = ["--cohort", str(self.root), "--report", str(self.root / "missing.json"),
                "--evidence-root", str(self.root), "--output", str(output)]
        self.assertEqual(A.main(args), 2)
        report = json.loads(output.read_text())
        self.assertEqual(report["status"], "EVIDENCE_AUDIT_RED_PRESERVED")
        self.assertFalse(report["ag6_approved"])
        with self.assertRaises(FileExistsError):
            A.main(args)


if __name__ == "__main__":
    unittest.main()
