import unittest
from v13.arithmetic_evidence import expectation

class ArithmeticEvidenceTests(unittest.TestCase):
    def test_source_exact(self):
        p=expectation('What is 2+2?')
        self.assertEqual(p['expected'],'4')
        self.assertEqual(p['authority'],'SOURCE_EXACT_ARITHMETIC_CHECK_ONLY')
        self.assertEqual(p['source_span'],[8,11])
    def test_decimal(self):
        self.assertEqual(expectation('Calculate 1.5+2.25')['expected'],'3.75')
    def test_not_math(self):
        for text in ('Hello', '2026-11-17', 'save a note: 2+2',
                     'What is 2**999999?', '3/0'):
            self.assertIsNone(expectation(text),text)
    def test_no_tool_authority(self):
        p=expectation('2+2')
        self.assertNotIn('tool',p)
        self.assertNotIn('permission',p)

if __name__=='__main__':unittest.main()
