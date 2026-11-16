import unittest
import tempfile
import time
from pathlib import Path
from v13.exact_arithmetic import exact_arithmetic

class ExactArithmetic(unittest.TestCase):
    def test_supported_source_exact(self):
        cases = {'2+2':'4','What is 2+2?':'4','was ist 2 + 2?':'4',
                 'calculate 7*6':'42','0.1+0.2':'0.3','10/4':'2.5',
                 '8÷2':'4','5-9':'-4','2×3':'6'}
        for question, expected in cases.items():
            with self.subTest(question=question):
                self.assertEqual(exact_arithmetic(question), expected)

    def test_abstain_ambiguous_or_unsafe(self):
        for question in ('2+2 and explain why', 'what is 2+2 in binary?',
                         '1/0', '10/3', '-2+3', 'hello', '2**10000',
                         '1234567890+1', 'what is 2+2 and 3+3?',
                         'copy exactly: 2+2', '2+2; launch app'):
            with self.subTest(question=question):
                self.assertIsNone(exact_arithmetic(question))

class RuntimeArithmeticIntegration(unittest.TestCase):
    def test_real_turn_persists_exact_answer_without_native_model(self):
        from v13.runtime import Runtime
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(directory))
            try:
                event_id = runtime.submit('What is 2+2?')
                until = time.monotonic() + 12
                row = None
                while time.monotonic() < until:
                    row = runtime.store.one(
                        "SELECT * FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",
                        (event_id,))
                    if row and row['status'] in ('FINAL', 'ERROR', 'DEADLINE'):
                        break
                    time.sleep(.05)
                self.assertIsNotNone(row)
                self.assertEqual(row['status'], 'FINAL', row['text'])
                self.assertEqual(row['text'], '4')
            finally:
                runtime.close()

if __name__ == '__main__':
    unittest.main()
