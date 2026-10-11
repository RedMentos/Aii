"""WP-N1 C4 focal loop, B4 workspace, Inquisition P1/P2 (WP-N2 scaffold) and C5 gate. No model needed.

Pure policy tests plus runtime tests on the real coordinator + SQLite with body offers replaced
by spies that write genuine OfferPackets. They prove control flow and state effects, not model quality.
"""
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from unittest.mock import Mock

from v13 import focal
from v13.contracts import packet,validate
from v13.operator import Operator
from v13.runtime import Runtime


def cand(i,kind='B1_DETAIL',text='',salience=0.,**t):
    terms=dict(goal=.5,utility=.8,sq=1.,uncertainty=.2)|t
    return focal.item(kind,i,[],text or i,'evt',salience=salience,**terms)


class Policy(unittest.TestCase):
    def test_disagreement_needs_shared_topic(self):
        self.assertGreaterEqual(focal.disagreement('The total budget is 391','The total budget is 400'),.4)
        self.assertEqual(focal.disagreement('The total budget is 391','Weather looks sunny 400'),0.)
        self.assertGreaterEqual(focal.disagreement('the plan is safe for users','the plan is not safe for users'),.4)
        self.assertEqual(focal.disagreement('the plan is safe','the plan is safe'),0.)

    def test_admission_capacity_threshold_redundancy_and_interrupt(self):
        a,b,c=cand('a',text='alpha beta gamma'),cand('b',text='delta epsilon'),cand('c',text='zeta eta',goal=0.,utility=0.,sq=0.)
        active,rest=focal.admit([a,b,c],2,.45)
        self.assertEqual([x['item_id'] for x in active],['a','b']);self.assertEqual(c['admission'],'BELOW_THRESHOLD')
        dup=cand('d',text='alpha beta gamma');active,_=focal.admit([cand('a',text='alpha beta gamma'),dup],2,.45)
        self.assertEqual(dup['priority_terms']['redundancy'],1.);self.assertNotIn(dup,active)
        loud=cand('z',text='urgent other thing',goal=0.,utility=0.,sq=0.,salience=.9)
        active,rest=focal.admit([cand('a',text='one'),cand('b',text='two'),loud],2,.45)
        self.assertIn(loud,active);self.assertEqual(loud['admission'],'SALIENCE_INTERRUPT')
        self.assertTrue(any(x.get('admission')=='DISPLACED_BY_SALIENCE_INTERRUPT' for x in rest))
        self.assertTrue(all(x['state_type']!='ACTIVE' for x in rest))

    def test_scale_links_follow_source_spans(self):
        ref=lambda a,b:{'source_id':'s','char_start':a,'char_end':b}
        g=focal.item('B2_GIST','g',[ref(0,100)],'x','e',uncertainty=0,salience=0,goal=0,utility=0,sq=0)
        f=focal.item('B1_DETAIL','f',[ref(10,20)],'y','e',uncertainty=0,salience=0,goal=0,utility=0,sq=0)
        far=focal.item('B1_DETAIL','h',[ref(200,210)],'z','e',uncertainty=0,salience=0,goal=0,utility=0,sq=0)
        focal.link_scales([g,f,far])
        self.assertEqual(g['children'],['f']);self.assertEqual(f['parents'],['g']);self.assertEqual(far['parents'],[])

    def test_decision_targets_reentry_else_incorporates(self):
        v={'bodies':['B1_DETAIL','B2_GIST']}
        self.assertEqual(focal.choose(v,'B1_DETAIL',1),('QUERY_A','TARGETED_REENTRY'))
        self.assertEqual(focal.choose(v,'B2_GIST',1)[0],'QUERY_B')
        self.assertEqual(focal.choose(v,'B1_DETAIL',0)[0],'INCORPORATE_AB')
        self.assertEqual(focal.choose({'bodies':[]},None,1)[0],'IGNORE')


class Store(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.s=self.r.store
        self.e={'event_id':'evt_x','brain_generation_id':self.s.generation_id,'source_ref':self.s.source('Compute the total budget','USER')}
    def tearDown(self):self.r.close();self.tmp.cleanup()

    def test_c5_reproduces_route_table_and_gates_permissions(self):
        gate=focal.ActionGate(self.s)
        for route,want in {'simple':'C3_LANGUAGE','detail':'B1_DETAIL','gist':'B2_GIST','both':'B1_DETAIL'}.items():
            self.assertEqual(gate.select(self.e,route=route,direct=False,resource_state='NORMAL')['role'],want)
            self.assertEqual(gate.select(self.e,route=route,direct=False,resource_state='PRESSURE')['role'],'C3_LANGUAGE')
        self.assertEqual(gate.select(self.e,route='detail',direct=True,resource_state='NORMAL')['role'],'SOURCE_COPY')
        strong_b1=[dict(cand('o'),priority=1.)]
        sel=gate.select(self.e,route='simple',direct=False,resource_state='NORMAL',coalition=strong_b1,view={'uncertainty':.9,'conflict':.9})
        self.assertEqual(sel['role'],'C3_LANGUAGE')  # focal support stays inside the BOOT margin
        reasons={x['action_id']:x['reason'] for x in sel['suppressed']}
        self.assertEqual(reasons['EXTERNAL_TOOL'],'AGE_NO_TOOLS');self.assertEqual(reasons['ASK_USER'],'WAIT_VS_ACT_BIAS_BOOT')
        p=json.loads(self.s.one("SELECT payload FROM packets WHERE kind='ActionSelection' ORDER BY rowid DESC LIMIT 1")['payload'])
        validate('ActionSelection',p);self.assertEqual(p['route_prior'],'C3_LANGUAGE')

    def test_inquisition_age0_forced_p1_p2_and_age2_modes(self):
        inq=focal.Inquisition(self.s)
        a,b=cand('a',text='The total budget is 391'),cand('b','B2_GIST',text='The total budget is 400',sq=.2)
        for x in (a,b):x['origin_event_id']=self.e['event_id']
        view={'conflict':.6,'bodies':['B1_DETAIL','B2_GIST'],'memory_contradiction':0.,'salience':0.,'uncertainty':.2}
        steps,target=inq.run(self.e,[a,b],[a,b],view,deliberation=False,max_steps=6,trigger=['AB_DISAGREEMENT'])
        self.assertEqual([(x['mode'],x['speaker']) for x in steps],[('HYPOTHESIS','P1'),('CRITIQUE','P2')])
        self.assertEqual(steps[1]['verdict'],'CONTESTED');self.assertEqual(target,'B2_GIST')  # weaker evidence is re-queried
        self.assertEqual(a['fact_hypothesis_status'],'CONTESTED_HYPOTHESIS');self.assertGreaterEqual(b['uncertainty'],.6)
        self.assertEqual(inq.plan(True,view,['no swearing'],8),['HYPOTHESIS','CRITIQUE','VERIFY','COMPARE','CONSTRAINT_CHECK','HYPOTHESIS','CRITIQUE'])
        for row in self.s.rows("SELECT payload FROM packets WHERE kind='InquisitionStep'"):
            p=validate('InquisitionStep',json.loads(row['payload']));self.assertFalse(p['fact_authority'])
        with self.assertRaises(ValueError):validate('InquisitionStep',dict(p,speaker='P3'))


class FocalRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home);self.calls=[]

    def tearDown(self):
        self.r.close();self.tmp.cleanup()

    def wait(self):
        until=time.monotonic()+10
        while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
        self.assertTrue(self.r.idle());return self.r.last_answer()

    def turn(self,text,route,script,halt=None,mode='max'):
        """script: role -> list of (summary, quote|None, needs_reentry) consumed per call."""
        Operator(self.r).run(':effort '+mode)
        self.r._route=Mock(return_value=(route,{'source':'BOOT_SCAFFOLD','scaffold':route}))
        def decide(component,e,baseline,*a,**k):
            if component=='halt' and halt:return {'learned':True,'action':halt}
            return {'learned':False,'action':baseline}
        self.r.learner.decide=Mock(side_effect=decide);self.r.learner.output_delta=Mock(return_value=None)
        s=self.r.store;queue={k:list(v) for k,v in script.items()}
        def offer(role,e,version,deadline,peer=None,*,valid_until=None):
            self.calls.append((role,bool(peer)))
            summary,quote,needs=queue[role].pop(0);src=s.read_source(e['source_ref']);refs=[]
            if quote:start=src.index(quote);refs=[e['source_ref']|{'char_start':e['source_ref']['char_start']+start,'char_end':e['source_ref']['char_start']+start+len(quote)}]
            p=packet('OfferPacket',role,e['event_id'],e['brain_generation_id'],[e['source_ref']],role=role,based_on_state_version=version,
                     deadline_monotonic_ns=int((valid_until or deadline)*1e9),evidence_refs=refs,offer={'summary':summary,'quotes':[quote] if quote else [],'uncertainty':'low','needs_reentry':needs},
                     confidence=0.,rejected_quotes=0,model_revision='test')
            s.add_packet('OfferPacket',p);return p
        self.r.cognition.offer=offer
        runner=SimpleNamespace(role='C3_LANGUAGE',last_metrics={'test_seam':True},generate=lambda *a,**k:iter(['ok']))
        self.r.pool.get=Mock(return_value=runner)
        self.r.submit(text);row=self.wait();meta=json.loads(row['metadata'])
        eid=row['event_id']
        kinds=lambda k:[json.loads(x['payload']) for x in s.rows('SELECT payload FROM packets WHERE kind=? AND event_id=? ORDER BY rowid',(k,eid))]
        return meta,kinds

    def test_conflict_triggers_attended_second_recall(self):
        """WP-N5 MEMORY provider: a memory the user query misses but the disagreeing offers cue is recalled and competes."""
        e0=self.r.store.event(self.r.session,'note');mid=self.r.memory.feedback(e0['event_id'],'fact','391 Euro',key='391')
        text='Compute the total budget: rent 120 plus food 271'
        self.assertEqual(self.r.memory.recall(text,self.r.session),[])
        meta,kinds=self.turn(text,'both',{'B1_DETAIL':[('The total budget is 391','rent 120 plus food 271',False)],
                                          'B2_GIST':[('The total budget is 400',None,False),('The total budget is 391 after recheck','rent 120',False)]})
        reqs=[r for r in kinds('AttentionRequest') if r['target']=='MEMORY']
        self.assertEqual(len(reqs),1);self.assertEqual(reqs[0]['reason'],'recall')
        resp=[r for r in kinds('AttentionResponse') if r['request_packet_id']==reqs[0]['packet_id']][0]
        self.assertEqual(resp['status'],'GRANTED');self.assertEqual(resp['payload']['memory_ids'],[mid])
        from v13 import attention as A
        self.assertEqual(A.controller(self.r).report()['policy']['recall|MEMORY']['n'],1)  # outcome booked: did it reach the coalition?

    def test_conflict_runs_inquisition_and_targeted_reentry(self):
        text='Compute the total budget: rent 120 plus food 271'
        meta,kinds=self.turn(text,'both',{'B1_DETAIL':[('The total budget is 391','rent 120 plus food 271',False)],
                                          'B2_GIST':[('The total budget is 400',None,False),('The total budget is 391 after recheck','rent 120',False)]})
        self.assertEqual(self.calls,[('B1_DETAIL',False),('B2_GIST',True),('B2_GIST',True)])  # contested, weaker B2 re-queried
        cycles=kinds('FocalCycle');self.assertEqual(cycles[0]['decision'],'QUERY_B');self.assertIn('INQUISITION',cycles[0]['phase'])
        for c in cycles:validate('FocalCycle',c)
        self.assertEqual([x['speaker'] for x in kinds('InquisitionStep')],['P1','P2'])  # Age 0: forced simple sequence
        items=kinds('FocalItem');self.assertTrue(items);[validate('FocalItem',x) for x in items]
        self.assertTrue(all(x['fact_hypothesis_status']!='FACT' for x in items))
        self.assertEqual(meta['focal']['inquisition'],['PROPOSED','CONTESTED'])
        self.assertTrue(set(meta['selected_offer_ids'])<={x['packet_id'] for x in kinds('OfferPacket')})
        resp=kinds('AttentionResponse');self.assertTrue(any(x['status']=='GRANTED' and x['delivery']=='b2_gist_slots' for x in resp))
        sel=kinds('ActionSelection')[-1];self.assertEqual(sel['selected']['action_id'],'B1_DETAIL')

    def test_callosum_reentry_preserved_and_halt_readout_can_stop_it(self):
        script=lambda:{'B1_DETAIL':[('Rent is 120','rent 120',False),('Rent is 120 checked','rent 120',False)],'B2_GIST':[('Monthly plan overview',None,True)]}
        meta,_=self.turn('Plan the month: rent 120','both',script())
        self.assertEqual(self.calls,[('B1_DETAIL',False),('B2_GIST',True),('B1_DETAIL',True)])
        self.assertEqual(meta['halt_decision']['action'],'continue')
        self.calls.clear();meta,kinds=self.turn('Plan the month again: rent 120','both',script(),halt='halt')
        self.assertFalse(meta['halt_decision']['steering']);self.assertEqual(len(self.calls),3)  # WP-N2: unstable trajectory, readout cannot steer
        from v13.focal import FocalLoop
        with patch.object(FocalLoop,'_halt_ok',return_value=True):
            self.calls.clear();meta,kinds=self.turn('Plan the month again: rent 120','both',script(),halt='halt')
        self.assertEqual(self.calls,[('B1_DETAIL',False),('B2_GIST',True)]);self.assertEqual(kinds('FocalCycle')[0]['reason'],'HALT_READOUT')

    def test_workspace_retains_prior_items_without_reporting_them(self):
        self.turn('Compute rent 120 plus food 271','detail',{'B1_DETAIL':[('Total is 391','rent 120 plus food 271',False)]},mode='high')
        ws=json.loads(Operator(self.r).run(':focal'))['workspace']
        self.assertTrue(any(x['source_kind']=='B1_DETAIL' for x in ws['slots']))
        meta,kinds=self.turn('Is rent 120 plus food 271 really 391?','detail',{'B1_DETAIL':[('Yes, 391','rent 120 plus food 271',False)]},mode='high')
        prior=[x for x in kinds('WorkspaceSlot')]+[x for x in kinds('FocalItem') if x['fact_hypothesis_status']=='PRIOR_HYPOTHESIS']
        self.assertTrue(prior)
        current={x['packet_id'] for x in kinds('OfferPacket')}
        self.assertTrue(set(meta['selected_offer_ids'])<=current)
        st,_=self.r.store.state('C4_WORKSPACE:'+self.r.session,{})
        self.assertTrue(any(x['state_type'] in ('REACTIVATABLE','EPISODIC_POINTER') for x in st['slots']))

    def test_direct_and_no_body_turns_still_select_report(self):
        meta,kinds=self.turn('Hallo','simple',{},mode='disabled')
        self.assertEqual(meta['focal']['decision'],'IGNORE');self.assertEqual(kinds('ActionSelection')[0]['selected']['action_id'],'C3_LANGUAGE')
        meta,kinds=self.turn('Copy exactly: abc','simple',{},mode='disabled')
        self.assertNotIn('focal',meta);self.assertEqual(kinds('ActionSelection')[0]['selected']['action_id'],'SOURCE_COPY')


if __name__=='__main__':unittest.main()
