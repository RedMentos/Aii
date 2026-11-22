"""Pinned QAD native tokenizer-ID probe source-only tests; no server or weights."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'p2_qad_gguf_tokenize_probe.py'
spec = importlib.util.spec_from_file_location('p2_tokenize', SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class TokenizeTests(unittest.TestCase):
    def test_parse_integer_ids(self):
        self.assertEqual(audit.parse_ids({'tokens': [1, 2, 64014]}), [1, 2, 64014])

    def test_reject_malformed_response(self):
        with self.assertRaisesRegex(ValueError, 'invalid GGUF'):
            audit.parse_ids({'token': [1]})

    def test_reject_noninteger_ids(self):
        for v in (1.0, True, -1, '2'):
            with self.subTest(v=v), self.assertRaises(ValueError):
                audit.parse_ids({'tokens': [v]})

    def test_eight_exact_ids_no_logit_promotion(self):
        rows = [[i, 2] for i in range(8)]
        result = audit.compare(rows, rows)
        self.assertEqual(result['status'], 'EIGHT_TOKEN_IDS_EQUAL_NATIVE_NO_LOGIT_PARITY')
        self.assertFalse(result['full_tokenizer_chat_logit_utility_parity_proven'])
        self.assertEqual(result['model_forward_calls'], 0)

    def test_single_token_mismatch_red(self):
        rows = [[i, 2] for i in range(8)]
        changed = [list(x) for x in rows]
        changed[5][0] += 1
        result = audit.compare(rows, changed)
        self.assertEqual(result['status'], 'TOKEN_ID_MISMATCH_RED')
        self.assertEqual(result['equal_count'], 7)

    def test_missing_probe_red(self):
        with self.assertRaisesRegex(ValueError, 'eight-probe'):
            audit.compare([[1]] * 7, [[1]] * 7)

    def test_wrong_source_hash_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'tok.json'
            p.write_text('{}')
            out = Path(d) / 'result.json'
            self.assertEqual(audit.main(['--tokenizer-json', str(p),
                                         '--output', str(out)]), 2)
            self.assertEqual(json.loads(out.read_text())['status'], 'TOKEN_ID_MISMATCH_RED')
            with self.assertRaises(FileExistsError):
                audit.main(['--tokenizer-json', str(p), '--output', str(out)])


if __name__ == '__main__':
    unittest.main()
