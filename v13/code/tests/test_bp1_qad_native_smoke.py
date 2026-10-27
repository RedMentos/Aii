"""QAD C3 native smoke contracts; no model weights or native runtime in these tests."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from scripts import bp1_qad_native_smoke as N


def sample(mode, sha):
    return {"mode": mode, "model_sha256": sha,
            "records": [{"prompt": q, "response": "answer", "seconds": 0.1,
                         "new_tokens": 2, "vmhwm_kib": 100} for q in N.PROMPTS]}


class NativeSmokeSoftwareTests(unittest.TestCase):
    def test_batch_encoding_is_normalized_to_tensor(self):
        class Tensor:
            pass
        class Torch:
            Tensor = Tensor
        class BatchEncoding:
            def __getitem__(self, key):
                self_key = key
                if self_key != "input_ids":
                    raise KeyError(key)
                return tensor
        tensor = Tensor()
        self.assertIs(N.tensor_input_ids(BatchEncoding(), Torch), tensor)
        self.assertIs(N.tensor_input_ids(tensor, Torch), tensor)
        with self.assertRaisesRegex(ValueError, "not a torch tensor"):
            N.tensor_input_ids({"input_ids": [1, 2]}, Torch)

    def test_registered_prompts_immutable(self):
        self.assertEqual(len(N.PROMPTS), 4)
        self.assertEqual(N.PROMPTS[0], "What is 2 + 2?")
        self.assertEqual(N.MAX_TOKENS, 24)
        self.assertEqual(N.SEED, 13)

    def test_matching_reports_remain_diagnostic(self):
        r = N.compare(sample("QAD_FP32_TRANSFORMERS", N.MASTER_SHA),
                      sample("QAD_Q4_GGUF_LLAMA_CPP", N.GGUF_SHA))
        self.assertEqual(r["exact_text_matches"], 4)
        self.assertFalse(r["tensor_parity_proven"])
        self.assertFalse(r["learned_utility_proven"])
        self.assertFalse(r["training_executed"])

    def test_response_difference_not_parity_failure(self):
        a = sample("QAD_FP32_TRANSFORMERS", N.MASTER_SHA)
        b = sample("QAD_Q4_GGUF_LLAMA_CPP", N.GGUF_SHA)
        b["records"][1]["response"] = "other"
        self.assertEqual(N.compare(a, b)["exact_text_matches"], 3)

    def test_mismatched_model_hash_rejected(self):
        a = sample("QAD_FP32_TRANSFORMERS", "f"*64)
        with self.assertRaisesRegex(ValueError, "model source hashes"):
            N.compare(a, sample("QAD_Q4_GGUF_LLAMA_CPP", N.GGUF_SHA))

    def test_mismatched_prompt_pair_rejected(self):
        a = sample("QAD_FP32_TRANSFORMERS", N.MASTER_SHA)
        b = sample("QAD_Q4_GGUF_LLAMA_CPP", N.GGUF_SHA)
        b["records"][0]["prompt"] = "wrong"
        with self.assertRaisesRegex(ValueError, "prompt pair"):
            N.compare(a, b)

    def test_incomplete_native_records_rejected(self):
        a = sample("QAD_FP32_TRANSFORMERS", N.MASTER_SHA)
        a["records"].pop()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            N.compare(a, sample("QAD_Q4_GGUF_LLAMA_CPP", N.GGUF_SHA))

    def test_sha_stream_and_exclusive_write(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "model"
            p.write_bytes(b"mock")
            self.assertEqual(N.sha(p), "ec864fe99b539704b8872ac591067ef22d836a8d942087f2dba274b301ebe6e5")
            dest = Path(d) / "report.json"
            N.save_exclusive(dest, {"gates": N.GATES})
            with self.assertRaises(FileExistsError):
                N.save_exclusive(dest, {"overwrite": True})
            self.assertEqual(json.loads(dest.read_text())["gates"]["jepa_weight"], 0)

    def test_stop_only_owned_process(self):
        proc = Mock()
        proc.poll.return_value = None
        N.stop(proc)
        proc.terminate.assert_called_once()
        proc.wait.assert_called_once()
        proc.kill.assert_not_called()

    def test_stop_escalates_only_after_timeout(self):
        proc = Mock()
        proc.poll.return_value = None
        proc.wait.side_effect = [subprocess.TimeoutExpired("test", 12), 0]
        N.stop(proc)
        proc.kill.assert_called_once()
        self.assertEqual(proc.wait.call_count, 2)


if __name__ == "__main__":
    unittest.main()
