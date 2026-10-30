import unittest
from pathlib import Path
from step2_expression_diagnostic_20261030 import equation_diagnostic, audit_original_zip

F = {'budget': 196, 'a': 'Dawn', 'a_cost': 137, 'b': 'Dusk', 'b_cost': 185}
ZIP = Path(__file__).with_name('NATIVE_40996792157.zip')

class ExpressionSensitivityTests(unittest.TestCase):
    def test_explicit_math_both_correct(self):
        r = equation_diagnostic(F, '*Option Dawn:* €196 - €137 = €59\n*Option Dusk:* €196 - €185 = €11')
        self.assertEqual((r['a']['status'],r['b']['status']),('CORRECT','CORRECT'))

    def test_wrong_result_not_credited(self):
        self.assertEqual(equation_diagnostic(F,'Dusk: 196 - 185 = 12')['b']['status'],'WRONG')

    def test_reversed_operands_rejected(self):
        self.assertEqual(equation_diagnostic(F,'Dawn: 137 - 196 = 59')['a']['status'],'INVALID_OPERANDS')

    def test_cost_echo_not_credited(self):
        self.assertEqual(equation_diagnostic(F,'Dawn costs 137 Euro; Dusk costs 185 Euro')['a']['status'],'MISSING')

    def test_two_option_line_ambiguous(self):
        r = equation_diagnostic(F,'Dawn and Dusk: 196 - 137 = 59')
        self.assertEqual((r['a']['status'],r['b']['status']),('AMBIGUOUS','AMBIGUOUS'))

    def test_conflicting_equations_veto(self):
        r = equation_diagnostic(F,'Dawn: 196 - 137 = 59\nDawn: 196 - 137 = 58')
        self.assertEqual(r['a']['status'],'CONTRADICTORY')

    def test_duplicate_identical_equation_not_conflict(self):
        r = equation_diagnostic(F,'Dawn: 196 - 137 = 59\nDawn: 196 - 137 = 59')
        self.assertEqual(r['a']['status'],'CORRECT')

    def test_no_cross_line_inheritance(self):
        r = equation_diagnostic(F,'Dawn:\n196 - 137 = 59')
        self.assertEqual(r['a']['status'],'MISSING')

    def test_invalid_input(self):
        with self.assertRaises(ValueError): equation_diagnostic(F,None)

    def test_original_zip_bound_posthoc_only(self):
        r=audit_original_zip(ZIP)
        self.assertEqual(r['original_scores_out_of_18_unchanged'],{'A_C3_ONLY':0,'B_DEFAULT_BOTH':10,'C_ARITH_BOTH':9})
        self.assertTrue(r['posthoc_only'])
        self.assertFalse(r['step2_gate_promoted'])
        self.assertIn({'fixture':'Prism','arm':'A_C3_ONLY','option':'a'},r['lexical_missing_but_equation_correct'])
        self.assertIn({'fixture':'Prism','arm':'A_C3_ONLY','option':'b'},r['lexical_missing_but_equation_correct'])

if __name__ == '__main__':unittest.main()
