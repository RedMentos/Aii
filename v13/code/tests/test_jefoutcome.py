"""WP-U1 outcome labels for the fast heads and the experience lifecycle read model (fixtures, no models)."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from v13 import fastpolicy as fp
from v13 import jefoutcome as jo
from v13.operator import Operator
from v13.runtime import Runtime

class Targets(unittest.TestCase):
    def test_derivation(self):
        coal=[{'source_kind':'B1_DETAIL','item_id':'o1'},{'source_kind':'MEMORY','item_id':'m1'}]
        t=jo.targets({'wake_decision':{'action':'both'}},coal,['m1','m2'])
        self.assertEqual(t,{'wake':'detail','memory':'recall'})
        self.assertEqual(jo.targets({'wake_decision':{'action':'both'}},[],['m1']),{'wake':'none','memory':'skip'})
        self.assertEqual(jo.targets({},[{'source_kind':'MEMORY','item_id':'m9'}],['m1'])['memory'],'deep')  # second recall reached the coalition
        self.assertEqual(jo.targets({'wake_decision':{'action':'none'}},coal,[]),{})  # not woken, nothing recalled: no label
        self.assertEqual(jo.targets({'skill':{'name':'s'}},[],[]),{'skill':'skill'})
        self.assertEqual(jo.targets({'skill':{'name':'s','vetoed_by':'x'}},[],[]),{})

class Store(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name))
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def labelled(self,text,meta,coal,mem):
        e=self.r.store.event(self.r.session,text)
        for comp,base in (('wake','both'),('memory','recall'),('skill','skill')):fp.head(self.r,comp,e,base)
        return e,jo.after_turn(self.r,e,meta,'FINAL',{'coalition':coal})
    def test_labels_are_stored_against_the_head_decision(self):
        e,got=self.labelled('Plan Aurora',{'wake_decision':{'action':'both'},'memory_ids':['m1']},[{'source_kind':'B2_GIST','item_id':'o'}],['m1'])
        self.assertEqual(got,{'wake':'gist','memory':'skip'})
        self.assertEqual(jo.after_turn(self.r,e,{},'ERROR',{'coalition':[]}),{})  # only FINAL turns teach
        rep=jo.report(self.r);self.assertEqual(rep['heads']['wake']['by_value'],{'gist':1});self.assertEqual(rep['heads']['memory']['differs_from_scaffold'],1)
        self.assertEqual(rep['mode'],'record')
    def test_training_rows_only_in_learn_mode_and_never_over_human_labels(self):
        rows=[]
        for i in range(3):
            e,_=self.labelled('Plan Aurora '+str(i),{'wake_decision':{'action':'both'},'memory_ids':['m1']},[],['m1'])
            rows.append(e)
        d=jo._decision(self.r.store,rows[0]['event_id'],'memory');rev=d['context_revision']
        self.assertEqual(jo.training_rows(self.r.store,'memory',rev,set()),[])
        Operator(self.r).run(':fastpolicy outcomes learn')
        tr=jo.training_rows(self.r.store,'memory',rev,set());self.assertEqual(len(tr),3)
        k,row,p=tr[0];self.assertEqual((row['value'],row['authority']),('skip','OUTCOME_SELF_LABEL'))
        self.assertEqual(self.r.store.read_source({'source_id':row['source_id'],'sha256':self.r.store.one('SELECT hash FROM sources WHERE id=?',(row['source_id'],))['hash'],'char_start':0,'char_end':4,'modality':'text'}),'skip')
        self.assertEqual(len(jo.training_rows(self.r.store,'memory',rev,{k})),2)  # a human label for that context wins
        with self.assertRaises(ValueError):Operator(self.r).run(':fastpolicy outcomes maybe')

    def _one_trainable_memory_outcome(self):
        e,_=self.labelled('Plan Aurora source integrity',
            {'wake_decision':{'action':'both'},'memory_ids':['m1']},[],['m1'])
        rev=jo._decision(self.r.store,e['event_id'],'memory')['context_revision']
        Operator(self.r).run(':fastpolicy outcomes learn')
        self.assertEqual(len(jo.training_rows(self.r.store,'memory',rev,set())),1)
        return e,rev

    def test_changed_outcome_value_without_changed_source_cannot_train(self):
        e,rev=self._one_trainable_memory_outcome()
        st,v=self.r.store.state(jo.KEY)
        label=next(x for x in st['labels'] if x['component']=='memory')
        self.assertEqual(label['value'],'skip')
        label['value']='recall'
        self.r.store.set_state(jo.KEY,st,expected=v)
        self.assertEqual(jo.training_rows(self.r.store,'memory',rev,set()),[])

    def test_same_text_user_source_cannot_impersonate_outcome_authority(self):
        e,rev=self._one_trainable_memory_outcome()
        other=self.r.store.source('skip','USER')
        st,v=self.r.store.state(jo.KEY)
        next(x for x in st['labels'] if x['component']=='memory')['source_id']=other['source_id']
        self.r.store.set_state(jo.KEY,st,expected=v)
        self.assertEqual(jo.training_rows(self.r.store,'memory',rev,set()),[])

    def test_corrupt_outcome_blob_cannot_train(self):
        e,rev=self._one_trainable_memory_outcome()
        st,_=self.r.store.state(jo.KEY)
        source_id=next(x for x in st['labels'] if x['component']=='memory')['source_id']
        h=self.r.store.one('SELECT hash FROM sources WHERE id=?',(source_id,))['hash']
        (self.r.store.home/'data/blobs'/h).write_bytes(b'corrupted fixture')
        self.assertEqual(jo.training_rows(self.r.store,'memory',rev,set()),[])


    def test_deleted_decision_context_source_cannot_train(self):
        e,rev=self._one_trainable_memory_outcome()
        ref=jo._decision(self.r.store,e['event_id'],'memory')['context_ref']
        with self.r.store.tx() as db:
            db.execute('UPDATE sources SET deleted=1 WHERE id=?',(ref['source_id'],))
        self.assertEqual(jo.training_rows(self.r.store,'memory',rev,set()),[])

    def test_corrupt_decision_context_blob_cannot_train(self):
        e,rev=self._one_trainable_memory_outcome()
        ref=jo._decision(self.r.store,e['event_id'],'memory')['context_ref']
        (self.r.store.home/'data/blobs'/ref['sha256']).write_bytes(b'corrupt context fixture')
        self.assertEqual(jo.training_rows(self.r.store,'memory',rev,set()),[])

    def test_same_content_foreign_context_source_cannot_train(self):
        e,rev=self._one_trainable_memory_outcome()
        decision=jo._decision(self.r.store,e['event_id'],'memory')
        original=decision['context_ref']
        replacement=self.r.store.source(self.r.store.read_source(original),'USER')
        self.assertEqual(replacement['sha256'],original['sha256'])
        self.assertNotEqual(replacement['source_id'],original['source_id'])
        decision['context_ref']=replacement
        with self.r.store.tx() as db:
            db.execute('UPDATE packets SET payload=? WHERE id=?',
                       (json.dumps(decision,ensure_ascii=False,separators=(',',':')),decision['packet_id']))
        self.assertEqual(jo.training_rows(self.r.store,'memory',rev,set()),[])


    def test_repeated_final_outcome_keeps_one_label_and_source(self):
        meta={'wake_decision':{'action':'both'},'memory_ids':['m1']}
        coalition=[{'source_kind':'B2_GIST','item_id':'o'}]
        e,got=self.labelled('one final event',meta,coalition,['m1'])
        self.assertEqual(got,{'wake':'gist','memory':'skip'})
        before=len((self.r.store.state(jo.KEY)[0] or {})['labels'])
        sources=self.r.store.one("SELECT COUNT(*) AS n FROM sources WHERE kind='OUTCOME_SELF_LABEL'")['n']
        replay=jo.after_turn(self.r,e,meta,'FINAL',{'coalition':coalition})
        self.assertEqual(replay,{})
        self.assertEqual(len(self.r.store.state(jo.KEY)[0]['labels']),before)
        self.assertEqual(self.r.store.one("SELECT COUNT(*) AS n FROM sources WHERE kind='OUTCOME_SELF_LABEL'")['n'],sources)

    def test_replayed_final_different_target_does_not_relabel(self):
        e,_=self.labelled('one final changed observation',
            {'wake_decision':{'action':'both'}},[{'source_kind':'B2_GIST','item_id':'o'}],[])
        jo.after_turn(self.r,e,{'wake_decision':{'action':'both'}},'FINAL',
                      {'coalition':[{'source_kind':'B1_DETAIL','item_id':'o2'}]})
        self.assertEqual(jo.report(self.r)['heads']['wake']['by_value'],{'gist':1})

    def test_replayed_final_cannot_undo_route_correction(self):
        from v13.agi.live import _save
        e=self.r.store.event(self.r.session,'skill replay')
        fp.head(self.r,'skill',e,'skill')
        _save(self.r.store,e['event_id'],skill='weekly_plan')
        meta={'skill':{'name':'weekly_plan'}}
        jo.after_turn(self.r,e,meta,'FINAL',{'coalition':[]})
        self.assertEqual(jo.on_route_correction(self.r.store,e['event_id'],'detail'),1)
        self.assertEqual(jo.after_turn(self.r,e,meta,'FINAL',{'coalition':[]}),{})
        self.assertEqual(jo.report(self.r)['heads']['skill']['by_value'],{'none':1})

    def test_distinct_final_events_keep_distinct_outcome_labels(self):
        meta={'wake_decision':{'action':'both'},'memory_ids':['m1']}
        self.labelled('distinct final one',meta,[],['m1'])
        self.labelled('distinct final two',meta,[],['m1'])
        self.assertEqual(jo.report(self.r)['heads']['memory']['by_value'],{'skip':2})

    def test_human_agreement_and_route_correction_flip(self):
        e,_=self.labelled('Plan Aurora',{'wake_decision':{'action':'both'},'memory_ids':['m1']},[],['m1'])
        self.r.memory.feedback(e['event_id'],'memory','skip','learn');self.assertEqual(jo.report(self.r)['heads']['memory']['human_agreement'],1.)
        from v13.agi.live import _save
        e2=self.r.store.event(self.r.session,'weekly plan');fp.head(self.r,'skill',e2,'skill');_save(self.r.store,e2['event_id'],skill='weekly_plan')
        jo.after_turn(self.r,e2,{'skill':{'name':'weekly_plan'}},'FINAL',{'coalition':[]})
        self.assertEqual(jo.on_route_correction(self.r.store,e2['event_id'],'detail'),1)
        self.assertEqual(jo.report(self.r)['heads']['skill']['by_value'],{'none':1})

class Lifecycle(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name))
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def test_stage_grows_with_traces(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        Operator(self.r).run(':observers off')
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={'test_seam':True},generate=lambda *a,**k:iter(['ok'])))
        self.r.learner.output_delta=Mock(return_value=None)
        self.r.submit('Hello there');until=time.monotonic()+10
        while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
        eid=self.r.last_answer()['event_id'];lc=jo.lifecycle(self.r,eid)
        self.assertTrue(lc['reached']['L0_CAPTURE']);self.assertTrue(lc['reached']['L1_SEGMENT_TAG']);self.assertFalse(lc['reached']['L9_PROMOTE'])
        self.r.memory.feedback(eid,'fact','Greeting is fine');self.assertTrue(jo.lifecycle(self.r,eid)['reached']['L2_COMPARE'])
        s=json.loads(Operator(self.r).run(':fastpolicy lifecycle'));self.assertEqual(s['experiences'],1)
        with self.assertRaises(ValueError):jo.lifecycle(self.r,'evt_missing')

if __name__=='__main__':unittest.main()
