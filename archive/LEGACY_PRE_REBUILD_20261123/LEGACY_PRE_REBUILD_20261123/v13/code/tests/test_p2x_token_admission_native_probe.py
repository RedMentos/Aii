"""Adversarial source-only tests for P2X native tokenizer admission probe."""
import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "p2x_token_native_probe", SCRIPTS / "p2x_token_admission_native_probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class FakeTokenizer:
    def apply_chat_template(self, *args, **kwargs):
        return {"input_ids": [1] * 20, "attention_mask": [1] * 20}
    def __call__(self, *args, **kwargs):
        return {"input_ids": [2, 3]}


def selected():
    return [{"id": "P2X" + format(i, "016X"), "arm": "both_exact",
             "target_action": "A", "messages": [
                 {"role": "user", "content": "synthetic long prompt " + str(i)}]}
            for i in range(8)]


def encode(tok, text, target=None):
    if target is None:
        return [1] * 20, None
    return [1] * 20 + [2, 3], [-100] * 20 + [2, 3]


class ProbeTests(unittest.TestCase):
    def test_mapping_length_not_prompt_token_length(self):
        rows = probe.compare_lengths(FakeTokenizer(), selected(), [22] * 8,
                                     encode, expected_old=(4,) * 8)
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[0]["old_container_len"], 2)
        self.assertEqual(rows[0]["corrected_total"], 22)
        self.assertTrue(rows[0]["old_is_mapping"])

    def test_old_report_mismatch_red(self):
        with self.assertRaisesRegex(ValueError, "not reproduced"):
            probe.compare_lengths(FakeTokenizer(), selected(), [22] * 8,
                                  encode, expected_old=(5,) * 8)

    def test_corrected_count_mismatch_red(self):
        with self.assertRaisesRegex(ValueError, "mismatch"):
            probe.compare_lengths(FakeTokenizer(), selected(), [21] * 8,
                                  encode, expected_old=(4,) * 8)

    def test_bad_coverage_red(self):
        with self.assertRaisesRegex(ValueError, "count"):
            probe.compare_lengths(FakeTokenizer(), selected()[:7], [22] * 7,
                                  encode, expected_old=(4,) * 7)

    def test_trainer_truncation_red(self):
        def truncating(tok, text, target=None):
            if target is None:
                return [1] * 20, None
            return [1] * 21, [-100] * 19 + [2, 3]
        with self.assertRaisesRegex(ValueError, "mismatch"):
            probe.compare_lengths(FakeTokenizer(), selected(), [22] * 8,
                                  truncating, expected_old=(4,) * 8)


if __name__ == "__main__":
    unittest.main()
