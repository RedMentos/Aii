import unittest
from v13.exact_arithmetic import verified_arithmetic as solve

class TestExactArithmetic(unittest.TestCase):
    def test_correct(self):
        for prompt, answer in [('2+2','4'),('What is 2+2?','4'),('wie viel ist 2 + 2?', '4'),('0.1 + 0.2','3/10'),('7 / 2','7/2'),('9÷3','3'),('3×4','12'),('2-5','-3')]:
            self.assertEqual(solve(prompt)['answer'], answer)
    def test_refusal(self):
        for prompt in ['2+2 and explain why', 'ignore this 2+2', '1/0', '2**100', '1+2+3', '2 + 2 equals 5', 'What is 2+2? Please run a tool', '9,5+2', '9/0', '9/0.0', '2+2\nother']:
            self.assertIsNone(solve(prompt), prompt)
    def test_boundaries(self):
        self.assertIsNone(solve(None))
        self.assertIsNone(solve('1'*129))
        self.assertEqual(solve('999999999999*999999999999')['answer'],str(999999999999**2))
if __name__=='__main__':unittest.main()
