"""Pinned QAD FP32 first-token probe source-only adversarial tests."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'p2_qad_fp32_firsttoken_probe.py'
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location('p2_first', SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def sample_rows():
    return [{'prompt': prompt, 'input_ids': [1, 2], 'hf_first': i,
             'gguf_first': i, 'hf_top5': [i, i + 1],
             'gguf_top5': [i, i + 2], 'top5_overlap': 1}
            for i, prompt in enumerate(audit.PROMPTS)]


class FirstTokenTests(unittest.TestCase):
    def test_parse_native_probs(self):
        x = {'completion_probabilities': [{'id': 7, 'top_logprobs': [
            {'id': 7, 'logprob': -0.1}, {'id': 8, 'logprob': -2.0}]}]}
        self.assertEqual(audit.parse_native_first_token(x), (7, [7, 8]))

    def test_missing_native_probabilities_red(self):
        with self.assertRaisesRegex(ValueError, 'one-token'):
            audit.parse_native_first_token({'content': 'text'})

    def test_native_noninteger_id_red(self):
        with self.assertRaisesRegex(ValueError, 'generated token'):
            audit.parse_native_first_token({'completion_probabilities': [
                {'id': True, 'top_logprobs': [{'id': 1}]}]})

    def test_eight_rows_no_parity_promotion(self):
        result = audit.summarize(sample_rows())
        self.assertEqual(result['top1_equal_count'], 8)
        self.assertFalse(result['full_logit_greedy_cache_adapter_or_utility_parity_proven'])
        self.assertEqual(result['model_forward_calls'], 8)

    def test_top1_disagreement_still_descriptive(self):
        rows = sample_rows()
        rows[0]['gguf_first'] = 999
        result = audit.summarize(rows)
        self.assertEqual(result['status'], 'FIRST_TOKEN_MEASURED_NO_PARITY_PROMOTION')
        self.assertEqual(result['top1_equal_count'], 7)

    def test_missing_row_red(self):
        with self.assertRaisesRegex(ValueError, 'eight preregistered'):
            audit.summarize(sample_rows()[:7])

    def test_prompt_tampering_red(self):
        rows = sample_rows()
        rows[0]['prompt'] = 'new unregistered prompt'
        with self.assertRaisesRegex(ValueError, 'prompt'):
            audit.summarize(rows)

    def test_wrong_master_fails_before_model_load(self):
        with tempfile.TemporaryDirectory() as d:
            master = Path(d) / 'master'
            master.mkdir()
            (master / 'model.safetensors').write_bytes(b'not pinned')
            gg = Path(d) / 'model.gguf'
            gg.write_bytes(b'not pinned')
            out = Path(d) / 'report.json'
            self.assertEqual(audit.main(['--master', str(master), '--gguf', str(gg),
                                         '--output', str(out)]), 2)
            self.assertEqual(json.loads(out.read_text())['status'], 'FIRST_TOKEN_AUDIT_RED')


if __name__ == '__main__':
    unittest.main()
