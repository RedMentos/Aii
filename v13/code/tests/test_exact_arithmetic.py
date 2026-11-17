import unittest
from v13.exact_arithmetic import exact_arithmetic

class ExactArithmeticTests(unittest.TestCase):
    def test_exact(self):
        for query, expected in [('2+2','4'), (' 2 + 2? ','4'), ('-3 * 4','-12'),
                                ('7/2','7/2'), ('6÷3','2'), ('9×9=','81'),
                                ('1-8','-7'), ('1/3','1/3')]:
            with self.subTest(query=query):
                self.assertEqual(exact_arithmetic(query), expected)

    def test_abstain_to_full_brain(self):
        for query in ('What is 2+2?', 'Why is 2+2=4?', '2+2 and explain',
                      '2/0', '1+2+3', '2**3', '1e9+1', '9'*30+'+1', '', None):
            with self.subTest(query=query):
                self.assertIsNone(exact_arithmetic(query))

if __name__ == '__main__':
    unittest.main()
