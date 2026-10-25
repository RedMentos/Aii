"""Run182 AGE0d deterministic synthetic false-alarm and abstention tests."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/run182_answer_aware_shadow.py'
spec=importlib.util.spec_from_file_location('run182',SCRIPT)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
BUDGET='The approved budget for the clinic booking app is 58250 euros, including reserve.'
DATE='The original deadline was March 3. Correction: the deadline is moved from March 3 to May 22, and March 3 no longer applies.'


class ShadowTests(unittest.TestCase):
    def test_budget_wrong_explicit_claim_detected_with_exact_quote(self):
        x=m.check('What is the approved budget?','The budget is 55000 euros.',BUDGET,'src')
        self.assertEqual(x['status'],'SHADOW_MISMATCH')
        self.assertEqual(x['expected'],'58250')
        self.assertEqual(BUDGET[x['source_ref']['char_start']:x['source_ref']['char_end']],x['exact_source_quote'])
        self.assertFalse(x['delivery_authorized'])

    def test_budget_correct_no_alert(self):
        x=m.check('What is the budget?','The budget is 58250 euros.',BUDGET)
        self.assertEqual(x['reason'],'AGREES_WITH_SOURCE')

    def test_decimal_comma_budget_equivalence(self):
        source='The approved budget for the app is 42,50 euros.'
        self.assertEqual(m.check('What is the budget?','The budget is 42.5 euros.',source)['reason'],'AGREES_WITH_SOURCE')

    def test_revised_deadline_wrong_old_date_detected(self):
        x=m.check('What is the current deadline?','The deadline is March 3.',DATE)
        self.assertEqual((x['status'],x['expected'],x['answer_claim']),('SHADOW_MISMATCH','may 22','march 3'))

    def test_revised_deadline_correct_no_alert(self):
        self.assertEqual(m.check('What is the deadline?','The current deadline is May 22.',DATE)['status'],'ABSTAIN')

    def test_two_source_budgets_refuse(self):
        x=m.check('What is the budget?','The budget is 58250 euros.',BUDGET+' '+BUDGET)
        self.assertEqual(x['reason'],'SOURCE_MISSING_OR_AMBIGUOUS')

    def test_two_answer_claims_refuse(self):
        x=m.check('What is the budget?','The budget is 58250 euros. The budget is 50000 euros.',BUDGET)
        self.assertEqual(x['reason'],'ANSWER_MISSING_OR_AMBIGUOUS')

    def test_answer_without_explicit_value_refuses(self):
        self.assertEqual(m.check('What is the budget?','The source is unclear.',BUDGET)['reason'],'ANSWER_MISSING_OR_AMBIGUOUS')

    def test_unsupported_question_refuses(self):
        self.assertEqual(m.check('Who owns it?','Amara.',BUDGET)['reason'],'UNSUPPORTED_QUESTION')

    def test_invalid_input_refuses(self):
        self.assertEqual(m.check(None,'answer',BUDGET)['reason'],'INVALID_INPUT')

    def test_no_delivery_or_learning_on_any_case(self):
        for q,a,s in [('What is the budget?','The budget is 1 euros.',BUDGET),
                      ('What is the deadline?','The deadline is May 22.',DATE),
                      ('Who owns it?','Unknown.',BUDGET)]:
            x=m.check(q,a,s)
            self.assertTrue(x['shadow_only'])
            self.assertFalse(x['delivery_authorized'])
            self.assertFalse(x['learning_authorized'])
            self.assertFalse(x['age_reopen_authorized'])


if __name__=='__main__':unittest.main()
