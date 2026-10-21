"""WP-Z5: arm construction and verdict rules of scripts/z5_focal_controls.py (no model)."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import z5_focal_controls as Z
import utility_bench2 as U2
from v13.common import dumps

def rows(arm,passes,rep=1,ctx=None):
    return [{'rep':rep,'fixture':'t%02d'%i,'kind':'t','arm':arm,'pass':p,'context_hash':(ctx or arm)+str(i),'same_as_live':True} for i,p in enumerate(passes)]
def measure(n,all_sel=False,cand=3,slots=4):
    return [{'capacity_bound':cand>slots,'rejected':1,'displaced':0,'salience_interrupt':0,'candidates':cand,'reentry':1,'reentry_in_coalition':1,
             'coalition':2,'source_bound':2,'all_offers_selected':all_sel} for _ in range(n)]
RET=[{'sessions':1,'slots_saved':2,'slots_restored':2,'slots_source_bound':2}]

class Arms(unittest.TestCase):
    def test_question_split_and_retrieval_on_bench_tasks(self):
        for fid,text,nums,_ in U2.tasks():
            material,question=Z.split_question(text)
            self.assertTrue(question and material!=text,fid)
            got=Z.retrieve(text,4);self.assertLessEqual(len(got),4)
            for g in got:self.assertIn(g,material)  # verbatim quotes only
            if fid.startswith('long'):self.assertTrue(any(str(nums[0]) in g for g in got),fid)  # the buried figure is retrieved
    def test_fixed_slots_keep_newest_offer_per_body(self):
        offers=[{'role':'B1_DETAIL','packet_id':'a'},{'role':'B2_GIST','packet_id':'b'},{'role':'B1_DETAIL','packet_id':'c'}]
        self.assertEqual([p['packet_id'] for p in Z.latest_per_role(offers)],['c','b'])
    def test_layer_swap_replace_and_insert(self):
        head,anchor='\nInternal hypotheses: ','\nTask context: '
        body=[{'x':1}];sysmsg='S'+head+dumps(body)+anchor+'{}'
        self.assertEqual(Z.swap_layer(sysmsg,head,body,'',anchor),'S'+anchor+'{}')
        self.assertEqual(Z.swap_layer('S'+anchor+'{}',head,None,'\nR: []',anchor),'S\nR: []'+anchor+'{}')
        with self.assertRaises(ValueError):Z.swap_layer('S'+anchor,head,body,'',anchor)

class Verdict(unittest.TestCase):
    def test_full_context_win_needs_significance_and_noise_band(self):
        r=[]
        for rep in range(1,6):r+=rows('coalition_live',[True]*12,rep)+rows('coalition',[True]*12,rep)+rows('full_context',[True]*6+[False]*6,rep)
        v=Z.analyse(r,measure(60),RET)['verdict']
        self.assertEqual(v['beats_full_context'],'PASS');self.assertEqual(v['noise_band'],0);self.assertEqual(v['gate'],'PARTIAL')  # props 3/4 absent
    def test_capacity_never_binding_is_not_testable(self):
        r=rows('coalition_live',[True]*4)+rows('coalition',[True]*4)+rows('full_context',[False]*4)
        self.assertEqual(Z.analyse(r,measure(4,all_sel=True),RET)['verdict']['beats_full_context'],'NOT_TESTABLE_CAPACITY_NEVER_BINDS')
    def test_identical_results_fail(self):
        r=[]
        for rep in (1,2):r+=rows('coalition_live',[True,False]*5,rep)+rows('coalition',[True,False]*5,rep)+rows('full_context',[True,False]*5,rep)
        v=Z.analyse(r,measure(20),RET)['verdict'];self.assertEqual(v['beats_full_context'],'FAIL');self.assertEqual(v['gate'],'PARTIAL')

if __name__=='__main__':unittest.main()
