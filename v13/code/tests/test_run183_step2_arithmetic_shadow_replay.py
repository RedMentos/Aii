"""Run183 synthetic source-bound arithmetic and oracle-separation tests."""
import importlib.util
import json
from pathlib import Path
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/run183_step2_arithmetic_shadow_replay.py'
spec=importlib.util.spec_from_file_location('run183',SCRIPT)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def fixture(updated=False,missing=False):
    prior='Project A. Budget 100 euros. Deadline 5 days. Local-only requirement: true.'
    if missing:prior='Project A. Budget has not been provided.'
    current='Option A: cost 40 euros, duration 2 days, local true. Option B: cost 70 euros, duration 7 days, local false.'
    if updated:current+=' Updated rules, overriding the earlier rules: budget 75 euros, deadline 6 days, local-only requirement true.'
    budget=None if missing else (75 if updated else 100)
    return {'id':'A','prior':prior,'current':current,'oracle':{'options':[
        {'entity':'A','remaining':None if budget is None else budget-40},
        {'entity':'B','remaining':None if budget is None else budget-70}]}}


def answer(a,b):return json.dumps({'options':[{'entity':'A','remaining':a},{'entity':'B','remaining':b}]})


class ArithmeticTests(unittest.TestCase):
    def test_correct_source_arithmetic_no_alarm(self):
        self.assertEqual(m.check_answer(fixture(),answer(60,30))['reason'],'AGREES_WITH_SOURCE_ARITHMETIC')

    def test_wrong_remaining_has_exact_source_refs(self):
        f=fixture();x=m.check_answer(f,answer(30,20))
        self.assertEqual(x['status'],'SHADOW_ARITHMETIC_MISMATCH')
        self.assertEqual(x['mismatches']['A'],{'expected':60,'actual':30})
        for key,ref in [('budget',x['source_refs']['budget']),('A',x['source_refs']['options']['A'])]:
            self.assertEqual(f[ref['field']][ref['char_start']:ref['char_end']],ref['quote'])

    def test_updated_budget_overrides_prior(self):
        f=fixture(updated=True)
        self.assertEqual(m.check_answer(f,answer(35,5))['reason'],'AGREES_WITH_SOURCE_ARITHMETIC')
        self.assertEqual(m.check_answer(f,answer(60,30))['status'],'SHADOW_ARITHMETIC_MISMATCH')

    def test_unknown_budget_abstains(self):
        self.assertEqual(m.check_answer(fixture(missing=True),answer(60,30))['reason'],'SOURCE_UNAVAILABLE_OR_AMBIGUOUS')

    def test_duplicate_answer_entity_abstains(self):
        raw=json.dumps({'options':[{'entity':'A','remaining':60},{'entity':'A','remaining':30}]})
        self.assertEqual(m.check_answer(fixture(),raw)['reason'],'ANSWER_UNAVAILABLE_OR_AMBIGUOUS')

    def test_noninteger_remaining_abstains(self):
        self.assertEqual(m.check_answer(fixture(),answer(60.0,30))['status'],'ABSTAIN')

    def test_no_rights_on_any_path(self):
        for raw in (answer(60,30),answer(1,2),'not json'):
            x=m.check_answer(fixture(),raw)
            self.assertTrue(x['shadow_only'])
            self.assertFalse(x['delivery_authorized'])
            self.assertFalse(x['learning_authorized'])
            self.assertFalse(x['age_reopen_authorized'])

    def test_oracle_is_only_used_by_offline_scoring(self):
        f=fixture();data={'fixtures':[f], 'rows':[{'fixture':'A','variant':'b1_only','raw_answer':answer(30,20)},
                                               {'fixture':'A','variant':'b2_only','raw_answer':answer(60,30)}]}
        out=m.replay(data)
        self.assertEqual(out['counts']['tp'],1)
        self.assertEqual(out['counts']['tn'],1)
        self.assertFalse(out['delivery_authorized'])

    def test_inconsistent_frozen_oracle_is_rejected(self):
        f=fixture();f['oracle']['options'][0]['remaining']=999
        with self.assertRaisesRegex(ValueError,'disagrees with frozen oracle'):
            m.replay({'fixtures':[f],'rows':[{'fixture':'A','variant':'b1_only','raw_answer':answer(60,30)}]})


if __name__=='__main__':unittest.main()
