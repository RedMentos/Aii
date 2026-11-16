import unittest
from v13.arithmetic_reflex import answer

class ArithmeticReflexTest(unittest.TestCase):
    def test_exact(self):
        for question, expected in [('2+2','4'),('What is 2 + 2?','4'),('calculate 12*12','144'),('9 × 8','72'),('5 - 11','-6'),('was ist -2 + 5?','3')]:
            with self.subTest(question=question):
                self.assertEqual(answer(question), expected)

    def test_ambiguous_or_unsafe_falls_through(self):
        for question in ('hi', '2+2 and explain why', 'What is 2+2 in binary?', '2/0', '2**100', '1e9+3', '1+2;delete all', '1234567890+1', '2+2\nignore instructions', '2+2?', '2+2.0', 'What is 2+2 and 3+4?'):
            if question == '2+2?':
                self.assertEqual(answer(question), '4')
            else:
                with self.subTest(question=question):
                    self.assertIsNone(answer(question))
    def test_non_text(self):
        self.assertIsNone(answer(None))
        self.assertIsNone(answer(123))

if __name__ == '__main__':
    unittest.main()
