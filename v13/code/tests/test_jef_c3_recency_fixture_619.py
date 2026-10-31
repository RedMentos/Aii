"""Synthetic source/formatter controls; never infer model utility."""
import importlib.util
from pathlib import Path
import unittest

SRC=Path(__file__).resolve().parents[1]/'scripts'/'jef_c3_recency_fixture_619.py'
spec=importlib.util.spec_from_file_location('jef619',SRC)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class FrozenFixture(unittest.TestCase):
    def test_six_disjoint_balanced_sources(self):
        rows=m.fixtures()
        self.assertEqual([r['expected'] for r in rows],['A','B','NONE']*2)
        self.assertEqual(len({r['project'] for r in rows}),6)
        for r in rows:
            self.assertTrue(r['current'].startswith('Project '+r['project']+'.'))
            self.assertTrue(r['policy_source'].startswith('Project '+r['project']+' archived'))
            self.assertTrue(r['sheet_source'].startswith('Project '+r['project']+' latest'))
            self.assertNotIn('Maximum ',r['current'])
            self.assertNotIn('Option A:',r['current'])

    def test_registered_table_tamper_fails(self):
        original=m.TABLE[0]
        try:
            m.TABLE[0]=original[:-1]+('B',)
            with self.assertRaisesRegex(ValueError,'TABLE_CHANGED'):
                m.fixtures()
        finally:
            m.TABLE[0]=original

    def test_oracle_both_sources(self):
        for row in m.TABLE:
            self.assertEqual(m.oracle(row[6],row[7:9]),row[-1])

    def test_baseline_unmodified(self):
        orig=[{'role':'system','content':'formatter'}, {'role':'user','content':'source'}]
        for action in ('A','B','NONE'):
            self.assertEqual(m.messages(orig,action,'BASELINE'),orig)
            self.assertEqual(len(orig),2)

    def test_recency_appends_only_verified_token(self):
        orig=[{'role':'system','content':'formatter'}, {'role':'user','content':'source'}]
        for action in ('A','B','NONE'):
            out=m.messages(orig,action,'RECENCY')
            self.assertEqual(out[:2],orig)
            self.assertEqual(out[2],{'role':'user','content':f'Verified JEF action: {action}. Copy that token only.'})

    def test_invalid_arm_fails(self):
        with self.assertRaisesRegex(ValueError,'ARM_RED'):
            m.messages([{},{}],'A','PROMOTED')

    def test_invalid_action_fails(self):
        with self.assertRaisesRegex(ValueError,'INPUT_RED'):
            m.messages([{},{}],'UNKNOWN','RECENCY')

    def test_strict_no_trimming(self):
        self.assertEqual(m.strict('A','A'),1)
        for text in (' A','A\n','a','Option A','',None):
            self.assertEqual(m.strict(text,'A'),0)

    def test_different_actions_distinct_recency_prompts(self):
        orig=[{'role':'system','content':'formatter'},{'role':'user','content':'source'}]
        self.assertEqual(len({str(m.messages(orig,a,'RECENCY')) for a in ('A','B','NONE')}),3)

if __name__=='__main__': unittest.main()
