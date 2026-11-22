"""Real staged Runtime checks for specific RECORD_ONLY controller paths."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts import stage_integrated_candidate

CODE = Path(__file__).resolve().parents[1]

PROBE = r'''
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from v13.runtime import Runtime
from v13.operator import Operator
from v13 import actionlearn, attention, callosum, deliberation, fastforward, inputs, jefbridge, reflex, workspace_learn
from v13.record_only_gate import updates_allowed

class ControllerGuard(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.r=Runtime(Path(self.temp.name))
        self.r.sleep.cycle.set_policy('enabled','off')
        self.r._route=Mock(return_value=('simple',{'source':'TEST'}))
        self.r.learner.output_delta=Mock(return_value=None)
        def gen(messages,*args,**kwargs):yield 'This is a fine answer.'
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},generate=gen))

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def turn(self,text='Explain the weather in a sentence'):
        eid=self.r.submit(text)
        end=time.monotonic()+15
        while not self.r.idle() and time.monotonic()<end:time.sleep(.01)
        self.assertTrue(self.r.idle())
        answer=self.r.last_answer()
        self.assertEqual(answer['status'],'FINAL',answer)
        event=json.loads(self.r.store.one('SELECT packet FROM events WHERE id=?',(eid,))['packet'])
        return event,answer

    def test_full_turn_feedback_and_dynamic_modes(self):
        r=self.r
        self.assertEqual(r.cfg['learning_mode'],'RECORD_ONLY')
        event,answer=self.turn()
        eid=event['event_id']
        f=fastforward.controller(r)
        self.assertEqual(f.report()['trained_on'],0)
        self.assertEqual(f.report()['procedures'],{})
        offer={'packet_id':'synthetic_offer_1','role':'B1_DETAIL',
               'offer':{'summary':'fine answer','uncertainty':'','needs_reentry':False},
               'confidence':.8,'evidence_refs':[]}
        focal={'coalition':[{'item_id':'synthetic_offer_1'}]}
        j=jefbridge.controller(r)
        packet=j.learn_turn(event,'question',[offer],answer['text'],focal,pre_offer_ids=['synthetic_offer_1'])
        self.assertIsNotNone(packet)
        self.assertEqual(j.report()['updates'],0)
        self.assertIsNotNone(r.store.one("SELECT id FROM packets WHERE kind='JEFBridgeTurn' AND event_id=?",(eid,)))

        # Real mode switches remain effective without recreating the Store.
        self.assertIn('SHADOW_UPDATE',Operator(r).run(':learning shadow'))
        j.learn_turn(event,'question',[offer],answer['text'],focal,pre_offer_ids=['synthetic_offer_1'])
        self.assertGreater(j.report()['updates'],0)
        saved=[turn for turn in j._load()[0]['turns'] if turn['event_id']==eid]
        self.assertEqual(len(saved),1)
        self.assertEqual([row['id'] for row in saved[0]['rows']],['synthetic_offer_1'])
        ff_x=fastforward.features('sample','simple','none')
        f.learn(eid,ff_x,3.,'FINAL',10)
        self.assertEqual(f.report()['trained_on'],1)
        selected=r.store.one("SELECT payload FROM packets WHERE kind='ActionSelection' AND event_id=? ORDER BY rowid DESC LIMIT 1",(eid,))
        self.assertIsNotNone(selected)
        selection=json.loads(selected['payload'])
        ctx=(selection.get('learning') or {}).get('context') or actionlearn.context(selection.get('route_hint'))
        action=selection['selected']['action_id']
        c=actionlearn.C5Learning(r.store)
        c.learn(ctx,action,eid,task_success=1.)
        self.assertIn(ctx+'|'+action,c._load()[0]['q'])
        self.assertIn('RECORD_ONLY',Operator(r).run(':learning record'))
        before_j=j._load()[0]['w'][:]
        before_c=c._load()[0]['q'].copy()
        before_ff=f._load()[0]['w'].copy()
        inputs.record_rating(r.store,eid,8,'IMPLICIT_CHAT')
        inputs.record_rating(r.store,eid,3,'EXPLICIT_NOTE')
        self.assertEqual(len(inputs.ratings(r.store)),2)
        self.assertEqual(j._load()[0]['w'],before_j)
        self.assertEqual(c._load()[0]['q'],before_c)
        self.assertEqual(f._load()[0]['w'],before_ff)
        self.assertEqual(f.learn(eid,ff_x,10.,'FINAL',20)['status'],'SKIPPED_RECORD_ONLY')
        self.assertEqual(f.consolidate()['status'],'SKIPPED_RECORD_ONLY')
        self.assertEqual(f.record_turn('x','none','FINAL',1.),'RECORD_ONLY')
        self.assertEqual(f._load()[0]['w'],before_ff)

        self.assertIn('SHADOW_UPDATE',Operator(r).run(':learning shadow'))
        inputs.record_rating(r.store,eid,10,'EXPLICIT_NOTE')
        self.assertNotEqual(j._load()[0]['w'],before_j)
        self.assertNotEqual(c._load()[0]['q'],before_c)
        r.cfg['learning_mode']='INVALID'
        before=j._load()[0]['w'][:]
        inputs.record_rating(r.store,eid,2,'EXPLICIT_NOTE')
        self.assertEqual(j._load()[0]['w'],before)
        self.assertFalse(updates_allowed(SimpleNamespace()))
        broken=SimpleNamespace(_v13_learning_config=lambda:1/0)
        self.assertFalse(updates_allowed(broken))

    def test_shadow_forecast_never_drives_timeout_reflex(self):
        f=fastforward.controller(self.r)
        st=fastforward.empty()
        st['n']=5
        st['w']['log_duration'][0]=6.
        self.r.store.set_state(fastforward.KEY,st)
        self.r._route=Mock(return_value=('both',{'source':'TEST'}))
        with patch.object(reflex.Reflex,'timeout_check',autospec=True,return_value=None) as check:
            self.turn('Please compare several different details')
        self.assertTrue(check.called)
        self.assertIsNone(check.call_args.args[3])
        st,_=f._load()
        st['mode']='ACTIVE'
        self.r.store.set_state(fastforward.KEY,st)
        with patch.object(reflex.Reflex,'timeout_check',autospec=True,return_value=None) as check:
            self.turn('Please compare these details again')
        self.assertTrue(check.called)
        self.assertGreater(check.call_args.args[3],1.)

    def test_attention_deliberation_callosum_and_workspace_boundaries(self):
        r=self.r
        e=r.store.event(r.session,'source')
        eid=e['event_id']
        a=attention.Attention(r.store)
        request=a.request(eid,'JEF','MEMORY','recall',priority=.8)
        response=a.admit(eid,[request])[0]
        self.assertEqual(a.outcome(response['packet_id'],1.)['status'],'SKIPPED_RECORD_ONLY')
        self.assertEqual(a._load()[0]['policy'],{})
        d=deliberation.Deliberation(r.store)
        steps=[{'mode':'HYPOTHESIS','verdict':'PROPOSED'}]
        d.record(eid,['CONFLICT'],'ANSWER',1,steps)
        self.assertEqual(d.report()['mode_values'],{})
        self.assertEqual(d.outcome(eid,1.)['status'],'SKIPPED_RECORD_ONLY')
        c=callosum.Callosum(r.store)
        c.note(eid,'message','B1_DETAIL','B2_GIST','SOURCE_EXACT','SOURCE_EXACT',False,0.)
        before=c._load()[0]['dirs']
        self.assertEqual(c.outcome(eid,[],'FINAL')['status'],'SKIPPED_RECORD_ONLY')
        self.assertEqual(c.on_rating(eid,1.)['status'],'SKIPPED_RECORD_ONLY')
        self.assertEqual(c._load()[0]['dirs'],before)
        item={'source_kind':'MEMORY','state_type':'ACTIVE','turns_retained':1,'payload_ref':'source'}
        workspace_learn.observe(r.store,[item],[],[],[item])
        st,_=workspace_learn._load(r.store)
        self.assertEqual(st['kinds'],{})
        self.assertEqual(st['dropped'][0]['ref'],'source')
        Operator(r).run(':learning shadow')
        self.assertGreater(a.outcome(response['packet_id'],1.)['mean'],0.)
        d.record(eid,['CONFLICT'],'ANSWER',1,steps)
        self.assertTrue(d.report()['mode_values'])
        self.assertEqual(c.on_rating(eid,1.)['updated'],1)
        workspace_learn.observe(r.store,[item],[],[],[])
        self.assertGreater(workspace_learn._load(r.store)[0]['kinds']['MEMORY']['n_retained'],0)

if __name__=='__main__':unittest.main()
'''


class StageControllerChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='v13-record-only-stage-')
        cls.stage = Path(cls.temp.name) / 'stage'
        stage_integrated_candidate.stage(CODE, cls.stage)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_stage(self, *args):
        env = dict(os.environ, PYTHONPATH=str(self.stage), PYTHONDONTWRITEBYTECODE='1')
        result = subprocess.run([sys.executable, *args], cwd=self.stage, env=env,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_real_runtime_feedback_and_controller_paths(self):
        self.run_stage('-c', PROBE)

    def test_existing_fastforward_suite_in_staged_tree(self):
        self.run_stage('-m', 'unittest', 'discover', '-s', str(self.stage / 'tests'),
                       '-p', 'test_fastforward_reflex.py', '-v')


if __name__ == '__main__':
    unittest.main()
