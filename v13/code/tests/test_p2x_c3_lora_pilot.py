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

    @staticmethod
    def token_fake(prompt_ids, target_ids=2, rendered="RENDERED"):
        class FakeTokenizer:
            def __init__(self):
                self.calls = []
            def apply_chat_template(self, messages, **kwargs):
                self.calls.append(("template", kwargs))
                if kwargs.get("tokenize") is True:
                    # A two-key mapping is not a two-token prompt.
                    return {"input_ids": [1] * 600, "attention_mask": [1] * 600}
                return rendered
            def __call__(self, value, **kwargs):
                self.calls.append(("encode", kwargs))
                return {"input_ids": prompt_ids if value == "RENDERED" else target_ids}
        return FakeTokenizer()

    @staticmethod
    def with_fake_tokenizer(fake):
        return patch.dict(sys.modules, {"transformers": types.SimpleNamespace(
            AutoTokenizer=types.SimpleNamespace(from_pretrained=lambda *args, **kwargs: fake))})

    def test_token_length_truncation_red(self):
        fake = self.token_fake([1] * 511)
        with self.with_fake_tokenizer(fake):
            with self.assertRaisesRegex(ValueError, "truncation"):
                pilot.token_admission("/synthetic", pilot.select_pilot(fake_records()))

    def test_token_length_exact_512_boundary(self):
        fake = self.token_fake([1] * 510)
        with self.with_fake_tokenizer(fake):
            self.assertEqual(pilot.token_admission("/synthetic",
                pilot.select_pilot(fake_records())), [512] * 8)

    def test_token_length_uses_trainer_rendered_text_not_mapping_len(self):
        fake = self.token_fake([1] * 600)
        with self.with_fake_tokenizer(fake):
            with self.assertRaisesRegex(ValueError, "truncation"):
                pilot.token_admission("/synthetic", pilot.select_pilot(fake_records()))
        self.assertTrue(all(call[1].get("tokenize") is False for call in fake.calls
                            if call[0] == "template"))
        self.assertTrue(all(call[1].get("add_special_tokens") is False for call in fake.calls
                            if call[0] == "encode"))

    def test_token_admission_rejects_empty_or_malformed_ids(self):
        for prompt, target in (([], [2]), ([1], []), ([[1, 2]], [3]),
                               ([1, True], [2]), ([1, -1], [2]), ([1], [None])):
            with self.subTest(prompt=prompt, target=target):
                fake = self.token_fake(prompt, target)
                with self.with_fake_tokenizer(fake):
                    with self.assertRaisesRegex(ValueError, "malformed/empty"):
                        pilot.token_admission("/synthetic", pilot.select_pilot(fake_records()))

    def test_token_admission_rejects_malformed_render(self):
        fake = self.token_fake([1], rendered={"input_ids": [1]})
        with self.with_fake_tokenizer(fake):
            with self.assertRaisesRegex(ValueError, "malformed rendered"):
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
