"""QAD GGUF template audit no-model source-only tests."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'p2_qad_gguf_template_audit.py'
spec = importlib.util.spec_from_file_location('p2_template', SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class TemplateTests(unittest.TestCase):
    def test_exact_utf8_bytes_only(self):
        x = audit.compare('ä'.encode('utf-8'), 'ä')
        self.assertEqual(x['status'], 'TEMPLATE_BYTES_EQUAL_TOKEN_IDS_UNPROVEN')
        self.assertFalse(x['token_id_logit_and_utility_parity_proven'])

    def test_trailing_newline_is_not_equal(self):
        x = audit.compare(b'hello\n', 'hello')
        self.assertEqual(x['status'], 'TEMPLATE_BYTES_RED')

    def test_unicode_normalization_difference_rejected(self):
        x = audit.compare('é'.encode(), 'e\u0301')
        self.assertEqual(x['status'], 'TEMPLATE_BYTES_RED')

    def test_nonstring_embedded_rejected(self):
        with self.assertRaisesRegex(ValueError, 'not UTF-8'):
            audit.compare(b'x', None)

    def test_wrong_source_hash_fails_closed_and_preserves_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 'template.jinja'
            src.write_text('wrong')
            gg = Path(d) / 'model.gguf'
            gg.write_bytes(b'wrong')
            out = Path(d) / 'report.json'
            self.assertEqual(audit.main(['--template', str(src), '--gguf', str(gg),
                                         '--output', str(out)]), 2)
            self.assertEqual(json.loads(out.read_text())['status'], 'TEMPLATE_BYTES_RED')
            with self.assertRaises(FileExistsError):
                audit.main(['--template', str(src), '--gguf', str(gg),
                            '--output', str(out)])


if __name__ == '__main__':
    unittest.main()
