"""Run43 post-hoc software audit: oracle separation and tamper refusal."""
import copy
import hashlib
import unittest
from scripts import run43_tp27_source_tool_posthoc as r

RULE = ('Project Orion kickoff. '+'Admin notes. '*24+
        'Binding rules: Budget 160 euros. Deadline 8 days. Local-only requirement: true.')
SHEET = ('Project Orion supplier sheet. Option A: cost 115 euros, duration 6 days, local true. '
         'Option B: cost 90 euros, duration 5 days, local false.')
CURRENT = 'Project Orion: decide using earlier project rules and latest supplier sheet.'


def fixture():
    hist=[RULE,'Project Atlas archive index. No active project rules.',SHEET]
    events=[{'source_ref':{'source_id':f'src{i}','sha256':hashlib.sha256(t.encode()).hexdigest(),
                           'char_start':0,'char_end':len(t),'modality':'text'}} for i,t in enumerate(hist)]
    return ({'id':'Orion','type':'SPLIT','history':hist,'current':CURRENT,
             'oracle':{'action':'WRONG_ON_PURPOSE','options':[]}}, {'prior_events':events})


class PosthocTests(unittest.TestCase):
    def test_oracle_not_used_for_prediction(self):
        f,p=fixture()
        a=r.predict_fixture(f,p)
        f['oracle']={'action':'A','options':[{'remaining':45,'eligible':True},{'remaining':70,'eligible':False}]}
        b=r.predict_fixture(f,p)
        self.assertEqual(a,b)
        self.assertEqual(a['action'],'A')
        self.assertEqual(a['remaining'],[45,70])
        self.assertFalse(a['canonical_gate_pass'])

    def test_changed_source_hash_refused(self):
        f,p=fixture()
        p=copy.deepcopy(p);p['prior_events'][0]['source_ref']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'RUN43_HISTORY_SOURCE_TAMPER'):
            r.predict_fixture(f,p)

    def test_missing_original_cohort_refused(self):
        f,p=fixture()
        with self.assertRaisesRegex(ValueError,'RUN43_FIXTURE_COHORT'):
            r.replay({'fixtures':[f], 'preparations':[dict(p,fixture='Orion')]})


if __name__=='__main__': unittest.main()
