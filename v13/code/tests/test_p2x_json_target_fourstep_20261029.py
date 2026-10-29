"""Source-only JSON-target consistency controls; never a native LoRA proof."""
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from scripts import p2x_c3_json_target_fourstep as F
from scripts import p2x_c3_receiver_fourstep as BASE
from scripts import p2x_c3_lora_pilot as P
from scripts import p2x_disjoint_receiver_trainset as D


class JsonTargetFourStep(unittest.TestCase):
    def selected(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / "frozen"
            D.export(folder, P.FIXTURE_SHA)
            records = P.read_frozen(folder)
            return F.select_balanced(records)

    def test_exact_original_frozen_training_rows_and_no_validation(self):
        rows = self.selected()
        self.assertEqual(len(rows), 16)
        self.assertEqual({r["id"] for r in rows},
                         {r["id"] for r in BASE.select_balanced({
                             "train.jsonl": rows,
                             "validation_inputs.jsonl": []})})
        self.assertEqual({label: sum(r["target_action"] == label for r in rows)
                          for label in P.LABELS}, dict.fromkeys(P.LABELS, 4))
        for row in rows:
            self.assertNotIn("target_action", row["messages"][0]["content"])
            self.assertNotIn("oracle_action", row["messages"][0]["content"])
            self.assertEqual(json.loads(F.json_target(row["target_action"])),
                             {"action": row["target_action"]})
            self.assertEqual(F.json_target(row["target_action"]),
                             '{"action":"' + row["target_action"] + '"}')
        self.assertEqual(F.SEED, BASE.SEED)
        self.assertEqual(F.CFG, BASE.CFG)
        self.assertEqual(F.CFG["jepa_weight"], 0)

    def test_bad_label_is_refused_not_coerced(self):
        for bad in (None, True, False, 0, "a", "BAD", {"action": "A"}):
            with self.subTest(bad=repr(bad)), self.assertRaises(ValueError):
                F.json_target(bad)

    def test_token_admission_uses_json_object_and_end_marker(self):
        rows = self.selected()[:2]
        seen = []
        class FakeTokenizer:
            def apply_chat_template(self, messages, **kwargs):
                self_test.assertEqual(kwargs, {"add_generation_prompt": True,
                                                "tokenize": False})
                return "PROMPT"
            def __call__(self, text, **kwargs):
                seen.append(text)
                return {"input_ids": [1, 2, 3] if text == "PROMPT" else [4, 5]}
        class FakeAuto:
            @staticmethod
            def from_pretrained(path, local_files_only):
                self_test.assertTrue(local_files_only)
                return FakeTokenizer()
        self_test = self
        with patch.dict(sys.modules, {"transformers": types.SimpleNamespace(
                AutoTokenizer=FakeAuto)}):
            self.assertEqual(F.json_token_admission("/unused", rows), [5, 5])
        self.assertEqual(seen[::2], ["PROMPT"] * len(rows))
        self.assertEqual(seen[1::2], [
            F.json_target(r["target_action"]) + "<|im_end|>" for r in rows])

    def test_token_admission_rejects_truncation(self):
        rows = self.selected()[:1]
        class TooLong:
            def apply_chat_template(self, messages, **kwargs):
                return "PROMPT"
            def __call__(self, text, **kwargs):
                return {"input_ids": [1] * (F.CFG["max_tokens"] + 1)}
        class FakeAuto:
            @staticmethod
            def from_pretrained(path, local_files_only):
                return TooLong()
        with patch.dict(sys.modules, {"transformers": types.SimpleNamespace(
                AutoTokenizer=FakeAuto)}):
            with self.assertRaisesRegex(ValueError, "truncation"):
                F.json_token_admission("/unused", rows)


if __name__ == "__main__":
    unittest.main()
