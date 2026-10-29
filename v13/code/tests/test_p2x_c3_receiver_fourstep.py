"""P2X 16-example four-step native LoRA admission/negative tests, no model calls."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import p2x_c3_receiver_fourstep as M


def records():
    train = []
    for label in M.P.LABELS:
        for i in range(5):
            arm = "both_exact" if label != "UNKNOWN" else "c3_only"
            train.append({"id": f"P2X{label}{i:02d}", "arm": arm,
                          "target_action": label,
                          "messages": [{"role": "user", "content": f"Project P2X{label}{i:02d}. A B."}]})
    return {"train.jsonl": train,
            "validation_inputs.jsonl": [{"id": "P2XVALIDATION"}]}


class SelectionTests(unittest.TestCase):
    def test_balanced_unique_source_disjoint_selection(self):
        rows = M.select_balanced(records())
        self.assertEqual(len(rows), 16)
        self.assertEqual(len({r["id"] for r in rows}), 16)
        self.assertEqual({a: sum(r["target_action"] == a for r in rows)
                          for a in M.P.LABELS}, {a: 4 for a in M.P.LABELS})
        self.assertTrue(all((r["arm"] == "both_exact") == (r["target_action"] != "UNKNOWN")
                            for r in rows))
        self.assertEqual(rows, M.select_balanced(records()))

    def test_wrong_source_arm_rejected(self):
        data = records()
        for row in data["train.jsonl"]:
            if row["target_action"] == "A":
                row["arm"] = "shuffled"
        with self.assertRaisesRegex(ValueError, "source-arm"):
            M.select_balanced(data)

    def test_validation_overlap_rejected(self):
        data = records()
        data["validation_inputs.jsonl"] = [{"id": "P2XA00"}]
        with self.assertRaisesRegex(ValueError, "heldout"):
            M.select_balanced(data)

    def test_target_leak_rejected(self):
        data = records()
        for row in data["train.jsonl"]:
            if row["target_action"] == "B":
                row["messages"][0]["content"] += " oracle_action"
        with self.assertRaisesRegex(ValueError, "target leak"):
            M.select_balanced(data)

    def test_new_seed_and_locked_learning_authority(self):
        self.assertEqual(M.SEED, 2026102924)
        self.assertEqual(M.CFG["max_steps"], 4)
        self.assertEqual(M.CFG["min_steps"], 4)
        self.assertEqual(M.CFG["rank"], 2)
        self.assertEqual(M.CFG["jepa_weight"], 0)
        self.assertEqual(M.CFG["anchor_weight"], 0)
        self.assertEqual(M.CFG["targets"], ("v_proj", "out_proj"))


class NoNativeMockRunTests(unittest.TestCase):
    def fake_metrics(self, steps=4):
        return {"steps": steps, "loss_history": [{"step": i, "ce": 2.0 / i}
                                                  for i in range(1, steps + 1)],
                "jepa_weight": 0.0, "rank": 2,
                "targets": ["v_proj", "out_proj"],
                "trainable_parameter_count": 83968, "final_ce": 0.5}

    def test_mock_run_checks_16_records_and_four_steps(self):
        with tempfile.TemporaryDirectory() as d:
            adapter = Path(d) / "adapter.gguf"
            adapter.write_bytes(b"synthetic-adapter")
            class FakeTrainer:
                def __init__(self, **kw):
                    self.cfg = kw["cfg"]
                def fit(self, items, base_generation, deadline):
                    self_test.assertEqual(len(items), 16)
                    self_test.assertEqual(self.cfg["max_steps"], 4)
                    self_test.assertEqual(base_generation, 0)
                    return {"artifact": str(adapter), "hash": M.P.file_sha(adapter),
                            "metrics": self_test.fake_metrics(),
                            "files": {"gguf_tensors": 44}}
            self_test = self
            with (patch.object(M.P, "read_frozen", return_value=records()),
                  patch.object(M.P, "source_admission", return_value="master-sha") as admit,
                  patch.object(M.P, "resource_admission", return_value={"ok": True}),
                  patch.object(M.P, "token_admission", return_value=[160] * 16),
                  patch("v13.lora_trainer.LoraTrainer", FakeTrainer)):
                result = M.run(d, d, d, 60)
            self.assertEqual(admit.call_count, 2)
            self.assertEqual(result["status"], "SIXTEEN_EXAMPLE_FOUR_STEP_LORA_PILOT_ONLY")
            self.assertEqual(len(result["selected"]), 16)
            self.assertEqual(result["metrics"]["steps"], 4)
            self.assertFalse(result["production_activation"])
            self.assertFalse(result["step2_utility_pass"])

    def test_wrong_step_count_rejected_without_native(self):
        with tempfile.TemporaryDirectory() as d:
            adapter = Path(d) / "adapter.gguf"
            adapter.write_bytes(b"synthetic-adapter")
            class FakeTrainer:
                def __init__(self, **kw):
                    pass
                def fit(self, *a, **kw):
                    return {"artifact": str(adapter), "hash": M.P.file_sha(adapter),
                            "metrics": self_test.fake_metrics(steps=3),
                            "files": {"gguf_tensors": 44}}
            self_test = self
            with (patch.object(M.P, "read_frozen", return_value=records()),
                  patch.object(M.P, "source_admission", return_value="master-sha"),
                  patch.object(M.P, "resource_admission", return_value={"ok": True}),
                  patch.object(M.P, "token_admission", return_value=[160] * 16),
                  patch("v13.lora_trainer.LoraTrainer", FakeTrainer)):
                with self.assertRaisesRegex(ValueError, "training/metrics"):
                    M.run(d, d, d, 60)

    def test_cli_red_result_exclusive_and_no_activation(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "report.json"
            with patch.object(M, "run", side_effect=ValueError("synthetic_failure")):
                self.assertEqual(M.main(["--cohort", d, "--master", d, "--work", d,
                                         "--output", str(out)]), 2)
            data = json.loads(out.read_text())
            self.assertEqual(data["status"], "FOURSTEP_RED_PRESERVED")
            self.assertFalse(data["production_activation"])
            self.assertEqual(data["jepa_weight"], 0)
            with patch.object(M, "run", side_effect=ValueError("synthetic_failure")):
                with self.assertRaises(FileExistsError):
                    M.main(["--cohort", d, "--master", d, "--work", d,
                            "--output", str(out)])


if __name__ == "__main__":
    unittest.main()
