"""Adversarial source-only tests for default-off P2X C3 LoRA pilot admission."""
import hashlib
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p2x_c3_lora_pilot.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("p2x_lora_pilot", SCRIPT)
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def fake_records():
    train = []
    for label in pilot.LABELS:
        for i in range(126):
            arm = "both_exact" if label != "UNKNOWN" else "b1_only"
            train.append({"id": "P2X" + format(100 + 1000 * pilot.LABELS.index(label) + i, "016X"),
                          "arm": arm, "target_action": label,
                          "messages": [{"role": "user", "content": "Synthetic B1/B2 source text"}]})
    val = [{"id": "P2X" + format(10000 + i, "016X"),
            "arm": "both_exact", "messages": [{"role": "user", "content": "val"}]}
           for i in range(360)]
    return {"train.jsonl": train, "validation_inputs.jsonl": val,
            "validation_answers.jsonl": []}


class PilotTests(unittest.TestCase):
    def test_select_exact_two_per_label(self):
        selected = pilot.select_pilot(fake_records())
        self.assertEqual(len(selected), 8)
        self.assertEqual({x: sum(r["target_action"] == x for r in selected)
                          for x in pilot.LABELS}, {x: 2 for x in pilot.LABELS})

    def test_selection_deterministic(self):
        self.assertEqual(pilot.select_pilot(fake_records()), pilot.select_pilot(fake_records()))

    def test_selected_validation_overlap_red(self):
        records = fake_records()
        records["validation_inputs.jsonl"][0]["id"] = records["train.jsonl"][0]["id"]
        with self.assertRaisesRegex(ValueError, "identity"):
            pilot.select_pilot(records)

    def test_negative_action_leak_red(self):
        records = fake_records()
        records["train.jsonl"][0]["arm"] = "shuffled"
        with self.assertRaisesRegex(ValueError, "negative arm"):
            pilot.select_pilot(records)

    def test_model_facing_target_leak_red(self):
        records = fake_records()
        records["train.jsonl"][0]["messages"][0]["content"] = "target_action=A"
        with self.assertRaisesRegex(ValueError, "label leak"):
            pilot.select_pilot(records)

    def test_file_hash_streamed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "file"
            p.write_bytes(b"abcd" * 10000)
            self.assertEqual(pilot.file_sha(p), hashlib.sha256(p.read_bytes()).hexdigest())

    def test_source_hash_mismatch_red(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            for name in pilot.MASTER_SHA:
                (p / name).write_bytes(b"wrong")
            with self.assertRaisesRegex(ValueError, "source SHA256"):
                pilot.source_admission(p)

    def test_frozen_cohort_manifest_mismatch_red(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "manifest.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "manifest"):
                pilot.read_frozen(p)

    def test_token_length_truncation_red(self):
        fake = types.SimpleNamespace(
            apply_chat_template=lambda *args, **kwargs: [1] * 512,
            __call__=lambda *args, **kwargs: {"input_ids": [2, 3]})
        with patch.dict(sys.modules, {"transformers": types.SimpleNamespace(
                AutoTokenizer=types.SimpleNamespace(from_pretrained=lambda *args, **kwargs: fake))}):
            with self.assertRaisesRegex(ValueError, "truncation"):
                pilot.token_admission("/synthetic", pilot.select_pilot(fake_records()))

    def test_main_red_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "result.json"
            args = ["--cohort", str(Path(d) / "missing"), "--master", str(Path(d) / "missing"),
                    "--work", str(Path(d) / "work"), "--output", str(out)]
            self.assertEqual(pilot.main(args), 2)
            self.assertEqual(json.loads(out.read_text())["status"], "PILOT_RED_PRESERVED")
            with self.assertRaises(FileExistsError):
                pilot.main(args)


if __name__ == "__main__":
    unittest.main()
