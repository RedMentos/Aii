"""WP-T1 JEF_FAST_POLICY heads, C2 executive packet, re-entry focus and goal-directed re-entry (local fixtures, no models)."""
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
import numpy as np
from v13 import fastpolicy as fp
from v13.config import initialize
from v13.contracts import packet,validate
from v13.learning import POLICY_LABELS
from v13.operator import Operator
from v13.readout_worker import LABELS,train
from v13.runtime import Runtime

class Parsers(unittest.TestCase):
    def test_answer_type_and_memory_key(self):
        self.assertEqual(fp.answer_type('What is 12*7?'),'number')
        self.assertEqual(fp.answer_type('Is Aurora over budget?'),'yes_no')
        self.assertEqual(fp.answer_type('Summarize the Aurora report'),'summary')
        self.assertEqual(fp.answer_type('Write a python function for primes'),'code')
        self.assertEqual(fp.answer_type('hello there'),'free')
        k=fp.memory_key('What did Maria say about the Aurora budget in 2025?')
        self.assertEqual(k.split()[:3],['maria','aurora','2025']);self.assertNotIn('what',k.split())
        self.assertEqual(fp.memory_key('is it the one?'),'')
    def test_labels_are_one_contract(self):
        self.assertEqual(POLICY_LABELS,LABELS)
        for h in fp.HEADS:self.assertIn(h,POLICY_LABELS)
    def test_focus_question_kinds(self):
        off=lambda role,s,u='':{'role':role,'offer':{'summary':s,'uncertainty':u}}
        q=fp.focus_for('B2_GIST',[off('B1_DETAIL','Rent is 120'),off('B2_GIST','Rent is 200')],{'conflict':.8},'TARGETED_REENTRY')
        self.assertEqual(q['kind'],'RESOLVE_CONFLICT');self.assertIn('Rent is 120',q['question']);self.assertEqual(q['authority'],'EXECUTIVE_QUESTION_NOT_FACT')
        self.assertEqual(fp.focus_for('B1_DETAIL',[off('B1_DETAIL','x','date unclear')],{'conflict':0},'r')['kind'],'RESOLVE_UNCERTAINTY')
        self.assertEqual(fp.focus_for('B1_DETAIL',[off('B2_GIST','plan')],{'conflict':0},'r')['kind'],'VERIFY_PEER')
        self.assertEqual(fp.focus_for('B1_DETAIL',[],{},'r')['kind'],'FILL_GAP')

class ReadoutGate(unittest.TestCase):
    def test_new_heads_train_through_the_same_held_out_gate(self):
        for comp in fp.HEADS:
            with tempfile.TemporaryDirectory() as d:
                p=Path(d);k=len(LABELS[comp]);x=np.repeat(np.eye(k),6,axis=0);y=np.repeat(np.arange(k),6)
                inp={'component':comp,'config':initialize(p),'embeddings':x.tolist(),'labels':y.tolist(),'scaffold_labels':[0]*len(y),'context_hashes':[str(i) for i in range(len(y))]}
                m=train(inp,p);self.assertTrue(m['commit_eligible'],comp);self.assertGreater(m['effective_accuracy'],m['scaffold_accuracy'])
                inp['embeddings']=np.zeros_like(x).tolist();self.assertFalse(train(inp,p)['commit_eligible'],comp)  # no signal, no promotion

class Runtimeheads(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name))
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def test_feedback_needs_a_stored_head_decision_and_valid_label(self):
        r=self.r;e=r.store.event(r.session,'What did Maria say about Aurora?')
        with self.assertRaises(ValueError):r.memory.feedback(e['event_id'],'memory','deep','learn')
        action,d=fp.head(r,'memory',e,'recall');self.assertEqual(action,'recall');self.assertFalse(d['learned'])
        self.assertEqual(d['context_ref'],e['source_ref'])
        with self.assertRaises(ValueError):r.memory.feedback(e['event_id'],'memory','everything','learn')
        r.memory.feedback(e['event_id'],'memory','deep','learn')
        self.assertEqual(r.memory.recall('What did Maria say about Aurora?',r.session),[])  # labels never become fact memory
        with self.assertRaises(ValueError):r.learner.shadow_readout('memory')  # RECORD_ONLY default: no optimizer
    def test_recall_plan_skip_and_deep(self):
        r=self.r;e=r.store.event(r.session,'What did Maria say about Aurora?')
        k=r.cfg['memory_top_k']
        self.assertEqual(fp.recall_plan(r,e,'What did Maria say about Aurora?')[:2],(k,'What did Maria say about Aurora?'))
        r.learner.decide=Mock(return_value={'learned':True,'action':'skip','packet_id':'x'});self.assertEqual(fp.recall_plan(r,e,'q')[0],0)
        r.learner.decide=Mock(return_value={'learned':True,'action':'deep','packet_id':'x'});top,cue,_=fp.recall_plan(r,e,'What did Maria say about Aurora?')
        self.assertEqual(top,min(8,k+fp.DEEP_EXTRA));self.assertTrue(cue.endswith(' maria aurora'),cue)
        r.learner.decide=Mock(side_effect=RuntimeError('broken'));self.assertEqual(fp.recall_plan(r,e,'q')[0],k)  # fallback = scaffold
    def test_recall_top_k_bounds(self):
        r=self.r
        for i in range(5):
            e=r.store.event(r.session,'note '+str(i));r.memory.feedback(e['event_id'],'fact','Aurora budget is '+str(100+i),key='Aurora budget')
        self.assertEqual(r.memory.recall('Aurora budget',r.session,top_k=0),[])
        self.assertLessEqual(len(r.memory.recall('Aurora budget',r.session,top_k=1)),1)
    def test_c2_packet_fields_and_native_fallback(self):
        r=self.r;e=r.store.event(r.session,'What is 12*7 for Maria?')
        c=fp.c2_packet(r,e,'What is 12*7 for Maria?','detail',{'source':'BOOT_SCAFFOLD'})
        self.assertEqual(c['tool']['tool'],'calc');self.assertEqual(c['tool']['args'],{'expression':'12*7'});self.assertEqual(c['answer_type'],'number')
        self.assertIn('maria',c['memory_key']);self.assertEqual(set(c['sources'].values()),{'BOOT'})
        row=json.loads(r.store.one("SELECT payload FROM packets WHERE kind='C2ExecutivePacket' AND event_id=?",(e['event_id'],))['payload'])
        validate('C2ExecutivePacket',row);self.assertEqual(row['truth_authority'],0)
        e2=r.store.event(r.session,'hello there')
        c2=fp.c2_packet(r,e2,'hello there','simple',{'native_control':{'route':'simple','answer_type':'list','tool':'rm_rf'}})
        self.assertEqual((c2['answer_type'],c2['sources']['answer_type']),('list','NATIVE_C2'));self.assertNotIn('tool',c2)  # unknown native tool ignored
        c3=fp.c2_packet(r,e2,'hello there','simple',{'native_control':{'answer_type':'poem'}});self.assertEqual(c3['answer_type'],'free')
    def test_channel_head_applies_only_when_learned(self):
        r=self.r;e=r.store.event(r.session,'Rent is 120')
        p=packet('OfferPacket','B1_DETAIL',e['event_id'],e['brain_generation_id'],[e['source_ref']],role='B1_DETAIL',based_on_state_version=0,
                 deadline_monotonic_ns=int((time.monotonic()+30)*1e9),evidence_refs=[],offer={'summary':'Rent is 120','quotes':[],'uncertainty':'low','needs_reentry':False},
                 confidence=0.,rejected_quotes=0,model_revision='test')
        r.store.add_packet('OfferPacket',p)
        ch=lambda m:json.loads(r.store.one('SELECT payload FROM packets WHERE id=?',(m['message_packet_id'],))['payload'])['channel']
        self.assertEqual(ch(r.cognition.communicate(p,'B2_GIST')),'SOURCE_EXACT')
        self.assertEqual(ch(r.cognition.communicate(p,'B2_GIST',fast={'learned':False,'action':'CONTROL'})),'SOURCE_EXACT')
        self.assertEqual(ch(r.cognition.communicate(p,'B2_GIST',fast={'learned':True,'action':'CONTROL'})),'CONTROL')
    def test_operator_status_and_focus_mode(self):
        op=Operator(self.r);st=json.loads(op.run(':fastpolicy'))
        self.assertEqual(set(st['heads']),{'wake','halt','skill','memory','channel'});self.assertEqual(st['focus']['mode'],'measure')
        op.run(':fastpolicy focus off');self.assertEqual(fp.focus_arm(self.r.store,'evt_x'),'off')
        with self.assertRaises(ValueError):op.run(':fastpolicy focus maybe')
        op.run(':fastpolicy focus measure')
        self.assertEqual({fp.focus_arm(self.r.store,'evt_'+str(i)) for i in range(20)},{'on','off'})

class Reentry(unittest.TestCase):
    """Goal-directed re-entry through the real runtime turn (bodies scripted)."""
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.calls=[]
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def turn(self,text,route,script,focus='off',stage=1):
        op=Operator(self.r);op.run(':effort max');op.run(':fastpolicy focus '+focus)
        self.r._route=Mock(return_value=(route,{'source':'BOOT_SCAFFOLD','scaffold':route}))
        self.r.learner.decide=Mock(side_effect=lambda component,e,baseline,*a,**k:{'learned':False,'action':baseline});self.r.learner.output_delta=Mock(return_value=None)
        s=self.r.store;queue={k:list(v) for k,v in script.items()}
        def offer(role,e,version,deadline,peer=None,*,valid_until=None,focus=None):
            self.calls.append((role,focus['kind'] if focus else None))
            summary,quote,needs=queue[role].pop(0);src=s.read_source(e['source_ref']);refs=[]
            if quote:start=src.index(quote);refs=[e['source_ref']|{'char_start':e['source_ref']['char_start']+start,'char_end':e['source_ref']['char_start']+start+len(quote)}]
            p=packet('OfferPacket',role,e['event_id'],e['brain_generation_id'],[e['source_ref']],role=role,based_on_state_version=version,
                     deadline_monotonic_ns=int((valid_until or deadline)*1e9),evidence_refs=refs,offer={'summary':summary,'quotes':[quote] if quote else [],'uncertainty':'low','needs_reentry':needs},
                     confidence=0.,rejected_quotes=0,model_revision='test')
            s.add_packet('OfferPacket',p);return p
        self.r.cognition.offer=offer
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={'test_seam':True},generate=lambda *a,**k:iter(['ok'])))
        age={'stage':stage,'autonomous_effort_max':'high','focal_depth':3 if stage else 1,'deliberation':False,'tools':False,'long_loops':False,'resource_mode':'GREEN'}
        with patch('v13.effort.age_limits',return_value=age):
            self.r.submit(text);until=time.monotonic()+10
            while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
        row=self.r.last_answer();eid=row['event_id']
        return json.loads(row['metadata']),[json.loads(x['payload']) for x in s.rows("SELECT payload FROM packets WHERE kind='FocalCycle' AND event_id=? ORDER BY rowid",(eid,))]
    def test_two_reentries_when_each_still_needs_one(self):
        script={'B1_DETAIL':[('Rent is 120','rent 120',False),('Rent is 120 and food 271','food 271',True)],'B2_GIST':[('Monthly plan',None,True),('Plan totals 391 for rent and food',None,False)]}
        meta,cycles=self.turn('Plan the month: rent 120, food 271','both',script)
        self.assertEqual([c[0] for c in self.calls],['B1_DETAIL','B2_GIST','B1_DETAIL','B2_GIST'])
        self.assertEqual([c['decision'] for c in cycles][:2],['QUERY_A','QUERY_B'])
        self.calls.clear();self.turn('Plan the month: rent 120, food 271','both',script,stage=0)  # Age 0: one focal cycle, one re-entry
        self.assertEqual([c[0] for c in self.calls],['B1_DETAIL','B2_GIST','B1_DETAIL'])
    def test_stable_trajectory_stops_the_chain(self):
        script={'B1_DETAIL':[('Rent is 120','rent 120',False),('Rent is 120','rent 120',True)],'B2_GIST':[('Monthly plan',None,True),('never asked',None,False)]}
        meta,cycles=self.turn('Plan the month: rent 120','both',script)
        self.assertEqual([c[0] for c in self.calls],['B1_DETAIL','B2_GIST','B1_DETAIL'])  # budget 2, but the re-entry changed nothing
        self.assertEqual(fp.report(self.r)['focus']['off']['stable'],1)
    def test_focus_question_reaches_the_body_and_is_counted(self):
        script={'B1_DETAIL':[('Rent is 120','rent 120',False),('Rent is 120 checked','rent 120',False)],'B2_GIST':[('Monthly plan overview',None,True)]}
        self.turn('Plan the month: rent 120','both',script,focus='on')
        self.assertEqual(self.calls[2][0],'B1_DETAIL',self.calls);self.assertIn(self.calls[2][1],{'RESOLVE_CONFLICT','VERIFY_PEER'})
        q=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='QueryPacket' ORDER BY rowid DESC LIMIT 1")['payload']) if self.r.store.one("SELECT 1 FROM packets WHERE kind='QueryPacket'") else None
        self.assertIsNone(q)  # bodies are scripted here; the QueryPacket path is covered by cognition.offer itself
        self.assertEqual(fp.report(self.r)['focus']['on']['n'],1)

if __name__=='__main__':unittest.main()
