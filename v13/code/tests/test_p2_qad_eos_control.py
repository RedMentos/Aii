"""Source-only adversarial tests for preregistered GGUF ignore_eos control."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p2_qad_eos_control.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("p2_eos", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def fixtures():
    old = [{"prompt": p, "input_ids": [i + 1, i + 2],
            "hf_first": 7, "gguf_first": 9,
            "gguf_top5": [7, 9, 10]}
           for i, p in enumerate(audit.PROMPTS)]
    new = [{"prompt": p, "input_ids": [i + 1, i + 2],
            "gguf_first": 7, "gguf_top5": [7, 9, 10]}
           for i, p in enumerate(audit.PROMPTS)]
    return old, new


class EOSControlTests(unittest.TestCase):
    def test_control_descriptive_not_promotion(self):
        old, new = fixtures()
        x = audit.summarize(old, new)
        self.assertEqual(x["original_hf_vs_generated_equal"], 0)
        self.assertEqual(x["control_hf_vs_generated_equal"], 8)
        self.assertEqual(x["original_generated_vs_toplogprob_disagree"], 8)
        self.assertEqual(x["control_generated_vs_toplogprob_disagree"], 0)
        self.assertFalse(x["full_logit_rope_cache_adapter_or_utility_parity_proven"])
        self.assertEqual(x["new_hf_forward_calls"], 0)

    def test_no_posthoc_match_threshold(self):
        old, new = fixtures()
        new[0]["gguf_first"] = 9
        x = audit.summarize(old, new)
        self.assertEqual(x["status"], "EIGHT_NATIVE_EOS_CONTROL_DESCRIPTIVE_ONLY")
        self.assertEqual(x["control_hf_vs_generated_equal"], 7)

    def test_missing_row_red(self):
        old, new = fixtures()
        with self.assertRaisesRegex(ValueError, "eight paired"):
            audit.summarize(old, new[:-1])

    def test_prompt_change_red(self):
        old, new = fixtures()
        new[0]["prompt"] = "foreign"
        with self.assertRaisesRegex(ValueError, "unregistered"):
            audit.summarize(old, new)

    def test_input_ids_change_red(self):
        old, new = fixtures()
        new[0]["input_ids"] = [999]
        with self.assertRaisesRegex(ValueError, "unregistered"):
            audit.summarize(old, new)

    def test_noninteger_native_id_red(self):
        old, new = fixtures()
        new[0]["gguf_first"] = True
        with self.assertRaisesRegex(ValueError, "invalid control"):
            audit.summarize(old, new)

    def test_generated_token_absent_top5_red(self):
        old, new = fixtures()
        new[0]["gguf_first"] = 888
        with self.assertRaisesRegex(ValueError, "top-logprobs"):
            audit.summarize(old, new)

    def test_reference_hash_mismatch_before_network(self):
        with tempfile.TemporaryDirectory() as d:
            ref = Path(d) / "RESULT.json"
            ref.write_text('{"schema":"fake"}')
            with self.assertRaisesRegex(ValueError, "SHA256"):
                audit.frozen_rows(ref)

    def test_main_fail_closed_and_exclusive(self):
        with tempfile.TemporaryDirectory() as d:
            ref = Path(d) / "reference.json"
            ref.write_text("{}")
            gguf = Path(d) / "gguf.gguf"
            gguf.write_bytes(b"wrong")
            out = Path(d) / "out.json"
            self.assertEqual(audit.main(["--reference", str(ref), "--gguf", str(gguf),
                                         "--output", str(out)]), 2)
            self.assertEqual(json.loads(out.read_text())["status"], "EOS_CONTROL_RED")
            with self.assertRaises(FileExistsError):
                audit.main(["--reference", str(ref), "--gguf", str(gguf),
                            "--output", str(out)])


if __name__ == "__main__":
    unittest.main()
