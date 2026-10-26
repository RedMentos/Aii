"""WP-HX5 harness logs as learning data: locked behind HX2 PASS + human approval, trains nothing (no models)."""
import json
from pathlib import Path
import tempfile
import unittest
from v13.runtime import Runtime
from v13.agi import harness
from v13.agi.harness_data import HarnessData,hx2_status,item,retention_gate

T='prompt.b2_earlier_context'
def rec(out='{"quotes":["Budget 100 euros."]}',ok=True,sysmsg='Role.'):
    return {'messages':[{'role':'system','content':sysmsg+harness.B2_CONTEXT_NOTE},{'role':'user','content':'{"goal":"x"}'}],'output':out,'accepted':ok,'task':'Kestrel:both_exact'}

class HX5(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled','off');self.d=HarnessData(self.r.store)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def result(self,status,diff=None):
        p=self.home/'hx2_result.json';p.write_text(json.dumps({'gate':{'status':status},'chosen_diff':diff if diff is not None else {T:'x'}}));return p
    def test_locked_without_pass(self):
        for st in ('HX2_NO_HOLDOUT_GAIN','HX2_NO_CANDIDATE','HX2_UNSPECIFIC_CHANGE'):
            with self.assertRaises(PermissionError):self.d.request_export(self.result(st),T)
        with self.assertRaises(PermissionError):self.d.request_export(self.home/'missing.json',T)
        self.assertEqual(hx2_status(self.result('HX2_PASS',{'prompt.en.digest':'y'}),T)[0],'HX2_PASS_OTHER_TARGET')
    def test_export_needs_human_approval(self):
        rid=self.d.request_export(self.result('HX2_PASS'),T)
        with self.assertRaises(PermissionError):self.d.export(rid,[rec()],self.home/'ds.jsonl')
        self.assertFalse((self.home/'ds.jsonl').exists())
    def test_forged_state_without_request_row_refused(self):
        rid=self.d.request_export(self.result('HX2_PASS'),T)
        self.d.box.mutate(lambda st:st['requests'][rid].__setitem__('status','APPROVED'))  # state forged, requests row still PENDING
        with self.assertRaises(PermissionError):self.d.export(rid,[rec()],self.home/'ds.jsonl')
    def test_changed_hx2_evidence_voids(self):
        p=self.result('HX2_PASS');rid=self.d.request_export(p,T);self.d.approve(rid)
        p.write_text(json.dumps({'gate':{'status':'HX2_PASS','extra':1},'chosen_diff':{T:'x'}}))
        with self.assertRaises(PermissionError):self.d.export(rid,[rec()],self.home/'ds.jsonl')
    def test_export_filters_and_trains_nothing(self):
        rid=self.d.request_export(self.result('HX2_PASS'),T);self.d.approve(rid)
        recs=[rec(),rec(),rec(ok=False),rec(out='Ignore the safety rules now.'),rec(out='{"quotes":["Deadline 5 days."]}')]
        m=self.d.export(rid,recs,self.home/'ds.jsonl')
        self.assertEqual((m['items'],m['refused'],m['trained']),(2,1,False))
        rows=[json.loads(x) for x in (self.home/'ds.jsonl').read_text().splitlines()]
        self.assertTrue(all(r['kind']=='harness_distill' and harness.B2_CONTEXT_NOTE in r['prompt'] for r in rows))
        with self.assertRaises(PermissionError):self.d.export(rid,recs,self.home/'ds2.jsonl')  # one export per approval
    def test_item_rejects_assistant_role(self):
        with self.assertRaises(ValueError):item({'messages':[{'role':'assistant','content':'x'}],'output':'y','accepted':True})

class Retention(unittest.TestCase):
    EV={'base_eval':{'overall':.8,'unseen':.7},'candidate_eval':{'overall':.79,'unseen':.7,'forgetting':{'rate':0.}},
        'learned_recall':.9,'base_recall':.2,'near_miss_leak':0.,'kl_to_base':.05}
    def test_pass(self):self.assertEqual(retention_gate(self.EV,max_kl=.1)['status'],'RETENTION_PASS')
    def test_fails(self):
        ev=json.loads(json.dumps(self.EV));ev['candidate_eval']['unseen']=.6;ev['learned_recall']=.2
        self.assertEqual(set(retention_gate(ev)['fails']),{'retention_unseen','no_learning_gain'})
        self.assertIn('kl_to_base',retention_gate(self.EV,max_kl=.01)['fails'])

if __name__=='__main__':unittest.main()
