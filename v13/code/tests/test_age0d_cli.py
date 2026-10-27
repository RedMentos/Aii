"""AGE0d local CLI transport checks: no raw text echo, no automatic delivery."""
import io
import json
import unittest
from scripts import age0d_cli as cli


class LocalCliTests(unittest.TestCase):
    def call(self, args, text=''):
        out = io.StringIO()
        code = cli.main(args, stdin=io.StringIO(text), stdout=out)
        return code, json.loads(out.getvalue()), out.getvalue()

    def test_demo_is_explicitly_synthetic(self):
        code, report, raw = self.call(['--demo'])
        self.assertEqual(code, 0)
        self.assertEqual(report['scope'], 'SYNTHETIC_DEMO_ONLY')
        self.assertEqual(report['status'], 'MISMATCH')
        self.assertFalse(report['delivery_allowed'])
        self.assertNotIn('What is', raw)

    def test_valid_private_stdin_correct_and_mismatch(self):
        for answer, status in (('4', 'CORRECT'), ('5', 'MISMATCH')):
            with self.subTest(answer=answer):
                question = 'What is 2 + 2?'
                data = json.dumps({'question': question, 'answer': answer})
                code, report, raw = self.call(['--stdin-json'], data)
                self.assertEqual(code, 0)
                self.assertEqual(report['status'], status)
                self.assertEqual(report['authority'], 'NONE')
                self.assertFalse(report['delivery_allowed'])
                self.assertNotIn(question, raw)

    def test_invalid_transport_fails_closed_without_raw_echo(self):
        inputs = [
            '{broken secret',
            'x' * (cli.MAX_INPUT_CHARS + 1),
            json.dumps({'question': 'What is 2 + 2?', 'answer': '5', 'private_note': 'secret'}),
            json.dumps({'question': 'What is 2 + 2?'}),
            json.dumps({'question': 42, 'answer': '5'}),
            'null',
        ]
        for data in inputs:
            with self.subTest(data=data[:15]):
                code, report, raw = self.call(['--stdin-json'], data)
                self.assertEqual(code, 2)
                self.assertEqual(report['status'], 'ABSTAIN')
                self.assertEqual(report['reason'], 'INVALID_INPUT')
                self.assertFalse(report['delivery_allowed'])
                self.assertNotIn('secret', raw)
                self.assertNotIn('What is', raw)

    def test_valid_transport_can_abstain_on_unsupported_math(self):
        code, report, raw = self.call(['--stdin-json'],
            json.dumps({'question': 'What is 1 / 3?', 'answer': '0.33'}))
        self.assertEqual(code, 0)
        self.assertEqual(report['status'], 'ABSTAIN')
        self.assertFalse(report['delivery_allowed'])
        self.assertNotIn('What is', raw)


if __name__ == '__main__':
    unittest.main()
