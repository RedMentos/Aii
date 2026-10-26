"""WP-Z2k: newest_quoted rule reader and its runner."""
import importlib.util
import json
from pathlib import Path
import unittest
from v13.agi import eligibility as E
ROOT=Path(__file__).resolve().parents[1]
OLD='Project Kaus kickoff notes. Budget 70 euros. Deadline 5 days. Local-only requirement: true.'
NEW='Project Kaus status note. The steering group revised one rule on Monday. New budget 80 euros. All other project rules are unchanged.'
SHEET='Option A: cost 75 euros, duration 3 days, local true. Option B: cost 65 euros, duration 6 days, local true.'
CUR='Project Kaus. Decide between Option A and Option B from the latest supplier data sheet.'
OPTS=[{'entity':'A','cost':75,'days':3,'local':True},{'entity':'B','cost':65,'days':6,'local':True}]
OLDR={'budget':70,'deadline':5,'local_only':True}

def load():
    spec=importlib.util.spec_from_file_location('step2_z2k_test_copy',ROOT/'scripts/step2_z2k_reader.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class Reader(unittest.TestCase):
    def test_default_and_guard_unchanged(self):
        self.assertEqual(E.decide(OLDR,OPTS,CUR,[OLD,NEW,SHEET])['action'],'NONE')
        d=E.decide(OLDR,OPTS,CUR,[OLD,NEW,SHEET],history=[OLD,NEW,SHEET]);self.assertEqual((d['action'],d['read_newest']),('UNKNOWN',[]))
        with self.assertRaises(ValueError):E.decide(OLDR,OPTS,CUR,[],rule_reader='first')
    def test_newest_quoted_value_replaces_stale_extraction(self):
        d=E.decide(OLDR,OPTS,CUR,[OLD,NEW,SHEET],history=[OLD,NEW,SHEET],rule_reader='newest_quoted')
        self.assertEqual((d['action'],d['read_newest'],d['rejected']),('A',['budget'],[]));self.assertTrue(d['revision'].endswith('+recency+newest'))
    def test_newest_must_be_quoted(self):
        d=E.decide(OLDR,OPTS,CUR,[OLD,SHEET],history=[OLD,NEW,SHEET],rule_reader='newest_quoted')  # revision only in memory, not quoted
        self.assertEqual((d['action'],d['read_newest']),('UNKNOWN',[]))
        self.assertIsNone(E.newest_quoted('budget',CUR,[OLD,SHEET],[OLD,NEW]))
    def test_current_source_wins_and_conflict_stays_unknown(self):
        self.assertEqual(E.newest_quoted('budget',CUR+' Budget 90 euros.',[OLD,NEW],[OLD,NEW]),90)
        self.assertIsNone(E.newest_quoted('budget',CUR+' Budget 90 euros. Budget 95 euros.',[OLD,NEW],[OLD,NEW]))
    def test_model_null_filled_only_from_evidence(self):
        d=E.decide({'budget':None,'deadline':None,'local_only':None},OPTS,CUR,[OLD,NEW,SHEET],history=[OLD,NEW,SHEET],rule_reader='newest_quoted')
        self.assertEqual(d['action'],'A');self.assertEqual(sorted(d['read_newest']),['budget','deadline','local_only'])
    def test_tool_entry(self):
        args=dict(current=CUR,a_cost=75,a_days=3,a_local=True,b_cost=65,b_days=6,b_local=True,quotes='\n'.join([OLD,NEW,SHEET]),budget=70,deadline=5,local_only=True,history='\n'.join([OLD,NEW,SHEET]))
        self.assertEqual(E.tool(**args)['action'],'UNKNOWN');self.assertEqual(E.tool(**args,rule_reader='newest_quoted')['action'],'A')

class Runner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.z=load()
    def opts(self,f):return [{k:o[k] for k in ('entity','cost','days','local')} for o in f['oracle']['options']]
    def test_fresh_and_settings(self):
        z=self.z;ids={f['id'] for f in z.FIXTURES};used={x[0] for m in (z.i,z.h,z.g,z.z) for x in m.EPISODES}
        import step2_z2j_sources as j
        used|={x[0] for x in j.EPISODES}
        self.assertEqual(len(ids),10);self.assertFalse(ids&used);self.assertEqual(z.SEEDS,(38,39,40))
        for arm,c in (('A4','all'),('S4','sources')):
            s=z.z.z2b.settings(arm,38);self.assertEqual((s['b2_quote_choices'],s['b2_quote_slots'],s['b2_context_chars']),(c,4,1536))
    def test_episodes(self):
        for f in self.z.FIXTURES:
            for rule,values in f['superseded_all'].items():
                for v in values:
                    st=f['rules']|{rule:v};self.assertNotEqual(E.recipe(st['budget'],st['deadline'],st['local_only'],self.opts(f))[0],f['oracle']['action'],f['id'])
            old=dict(zip(('budget','deadline','local_only'),next(x[2] for x in self.z.EPISODES if x[0]==f['id'])))
            d=E.decide(old,self.opts(f),f['current'],f['history'],history=self.z.g.history_of(f),rule_reader='newest_quoted')
            self.assertEqual(d['action'],f['oracle']['action'],f['id'])
    def test_reader_pairs_and_gate(self):
        z=self.z;f=z.FIX['Kaus'];msg=[{'role':'user','content':json.dumps({'current_source':f['current'],'analysts':[{'role':'B2_GIST','verified_quotes':f['history']}]})}]
        tool={'rows':[{'fixture':'Kaus','variant':'both_exact','answer':json.dumps({'action':'NONE'}),'tool':{'extracted':{'project':'Kaus',**OLDR,'options':self.opts(f)}}}]}
        p=z.reader_pairs({'rows':[{'fixture':'Kaus','variant':'both_exact','consumer_messages':msg}]},tool)[0]
        self.assertEqual((p['on'],p['reader'],p['oracle'],p['read_newest']),('UNKNOWN','A','A',['budget']))
        self.assertEqual(z.gate({})['status'],'INCOMPLETE')

if __name__=='__main__':unittest.main()
