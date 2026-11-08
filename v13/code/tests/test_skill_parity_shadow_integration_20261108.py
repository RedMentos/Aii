"""Real Runtime controls for source-bound AG4 shadow route observations."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts.ag4_outcome_crosspath_candidate import build_sources as build_ag4
from scripts.c5_outcome_credit_candidate import build_sources as build_c5
from scripts.correction_association_integration_candidate import build_sources as build_memory
from scripts.skill_parity_shadow_integration_candidate import build_sources as build_parity


CODE = Path(__file__).resolve().parents[1]
PROBE = r'''
import json, sys, tempfile, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from v13 import inputs, skill_parity_shadow_candidate as parity
from v13.agi import hub
from v13.operator import Operator
from v13.runtime import Runtime

mode = sys.argv[1]
enabled_mode = mode in ('on','cascade')
def wire(r):
    r.sleep.cycle.set_policy('enabled', 'off')
    r._route = Mock(return_value=('detail', {'source':'TEST_ROUTE_SEAM'}))
    r.pool.get = Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},
                                                    generate=lambda *a,**k:iter(['2 + 2 = 5'])))
    r.learner.output_delta = Mock(return_value=None)
def turn(r):
    eid = r.submit('Run a budget check for me')
    deadline = time.monotonic()+10
    while not r.idle() and time.monotonic()<deadline: time.sleep(.005)
    row=r.last_answer()
    if not row or row['event_id']!=eid or row['status']!='FINAL': raise RuntimeError('turn failed')
    return eid, row

with tempfile.TemporaryDirectory() as home:
    r=Runtime(Path(home)); wire(r)
    try:
        session=r.session; lib=hub(r).skills
        lib.propose('budget_check',[{'route':'detail'}],trigger='budget check')
        initial=parity.capture_enabled(r.store)
        try: parity.set_capture_enabled(r.store,True)
        except PermissionError: no_authority=True
        else: no_authority=False
        if enabled_mode: Operator(r).run(':skilllive parity-shadow on')
        events=[]
        for _ in range(3): events.append(turn(r)[0])
        after_three=lib.get('budget_check')
        if mode=='baseline':
            print(json.dumps({'initial':initial,'no_authority':no_authority,
                              'stage':after_three['stage'],'uses':after_three['uses'],
                              'parity':after_three['parity'],'answer':r.last_answer()['text']}))
        else:
            r._route=Mock(return_value=('gist',{'source':'TEST_ROUTE_SEAM'}))
            events.append(turn(r)[0])
            after_four=lib.get('budget_check')
            inputs.record_rating(r.store,events[0],8,'IMPLICIT_CHAT')
            inputs.record_rating(r.store,events[0],2,'EXPLICIT_NOTE')
            low=parity.view(r.store,session)
            inputs.record_rating(r.store,events[0],8,'EXPLICIT_NOTE')
            corrected=parity.view(r.store,session)
            if enabled_mode:
                memory_id=r.memory.feedback(events[0],'fact','corrected budget result',key='budget result')
                fact_source=r.store.one('SELECT source_id FROM memories WHERE id=?',(memory_id,))['source_id']
                fact_seen=parity.view(r.store,session)
                packet=r.store.one("SELECT id,payload FROM packets WHERE event_id=? AND kind='HumanDecision' "
                                   "AND json_extract(payload,'$.source_ref.source_id')=?",(events[0],fact_source))
                altered=json.loads(packet['payload']);altered['producer_component']='FORGED'
                with r.store.tx() as c:c.execute('UPDATE packets SET payload=? WHERE id=?',(json.dumps(altered),packet['id']))
                fact_tampered=parity.view(r.store,session)
                with r.store.tx() as c:c.execute('UPDATE packets SET payload=? WHERE id=?',(packet['payload'],packet['id']))
                with r.store.tx() as c:c.execute('UPDATE sources SET kind=? WHERE id=?',('USER',fact_source))
                fact_wrong_kind=parity.view(r.store,session)
                with r.store.tx() as c:c.execute('UPDATE sources SET kind=? WHERE id=?',('HUMAN_DECISION',fact_source))
                with r.store.tx() as c:c.execute('UPDATE sources SET deleted=1 WHERE id=?',(fact_source,))
                fact_revoked=parity.view(r.store,session)
            else: fact_seen=fact_tampered=fact_wrong_kind=fact_revoked=None
            duplicate=parity.observe_final(r.store,events[0],'detail')['status'] if enabled_mode else 'OFF'
            try: parity.observe_final(r.store,events[0],'simple') if enabled_mode else None
            except ValueError: wrong_route_rejected=True
            else: wrong_route_rejected=not enabled_mode
            state_present=r.store.state(parity.KEY)[0] is not None
            r.close();r=Runtime(Path(home));wire(r)
            restored=parity.view(r.store,session); still_enabled=parity.capture_enabled(r.store)
            if enabled_mode:
                Operator(r).run(':skilllive parity-shadow off')
                turn(r)
                after_off=parity.view(r.store,session)
                # Later turns in this fixture include the first turn in context;
                # older turns cannot depend on the last event.
                target=events[0] if mode=='cascade' else events[-1]
                source=r.store.one('SELECT source_id FROM events WHERE id=?',(target,))['source_id']
                with r.store.tx() as c:c.execute('UPDATE sources SET deleted=1 WHERE id=?',(source,))
                revoked=parity.view(r.store,session)
                lib=hub(r).skills
                lib.set_stage('budget_check','RETIRED')
                lib.propose('budget_check',[{'route':'gist'}],trigger='budget check')
                replaced=parity.view(r.store,session)
            else:
                after_off=revoked=replaced=None
            r.store.set_state(parity.POLICY_KEY,{'revision':'bad','enabled':'yes'})
            try: parity.capture_enabled(r.store)
            except ValueError: corrupt_rejected=True
            else: corrupt_rejected=False
            try: parity.set_capture_enabled(r.store,True,'EXPLICIT_HUMAN')
            except ValueError: corrupt_enable_rejected=True
            else: corrupt_enable_rejected=False
            recovered=not parity.set_capture_enabled(r.store,False,'EXPLICIT_HUMAN')
            print(json.dumps({'initial':initial,'no_authority':no_authority,
                'stage':after_four['stage'],'uses':after_four['uses'],'successes':after_four['successes'],
                'parity':after_four['parity'],'instance_recorded':'human_credit_instance' in after_four,
                'answer':r.last_answer()['text'],
                'state_present':state_present,'low':low,'corrected':corrected,'duplicate':duplicate,
                'wrong_route_rejected':wrong_route_rejected,'restored':restored,'still_enabled':still_enabled,
                'after_off':after_off,'revoked':revoked,'replaced':replaced,
                'fact_seen':fact_seen,'fact_tampered':fact_tampered,'fact_wrong_kind':fact_wrong_kind,
                'fact_revoked':fact_revoked,
                'corrupt_rejected':corrupt_rejected,'corrupt_enable_rejected':corrupt_enable_rejected,
                'recovered':recovered,
                'learning_mode':r.cfg['learning_mode'],'updates':len(r.store.rows('SELECT * FROM updates'))}))
    finally:r.close()
'''
FAULT_PROBE = r'''
import json, tempfile, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from v13 import actionlearn, inputs, skill_parity_shadow_candidate as parity
from v13.agi import hub
from v13.operator import Operator
from v13.runtime import Runtime
with tempfile.TemporaryDirectory() as home:
    r=Runtime(Path(home))
    try:
        r.sleep.cycle.set_policy('enabled','off')
        r._route=Mock(return_value=('detail',{'source':'TEST_ROUTE_SEAM'}))
        r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},
                                                     generate=lambda *a,**k:iter(['synthetic answer'])))
        r.learner.output_delta=Mock(return_value=None)
        lib=hub(r).skills;lib.propose('budget_check',[{'route':'detail'}],trigger='budget check')
        Operator(r).run(':skilllive parity-shadow on')
        real_log=r.store.log
        def log(kind,event_id,metrics):
            if kind=='skill_parity_shadow_unavailable':raise OSError('diagnostic failure')
            return real_log(kind,event_id,metrics)
        with patch.object(parity,'annotate_candidates',side_effect=RuntimeError('capture failure')), \
             patch.object(r.store,'log',side_effect=log):
            eid=r.submit('Run a budget check for me')
            deadline=time.monotonic()+10
            while not r.idle() and time.monotonic()<deadline:time.sleep(.005)
        row=r.last_answer()
        inputs.record_rating(r.store,eid,2,'EXPLICIT_NOTE')
        actions=actionlearn.C5Learning(r.store).report()['actions']
        correction=max((v['modulators'].get('human_correction',0) for v in actions.values()),default=0)
        print(json.dumps({'status':row['status'],'answer':row['text'],
                          'stage':lib.get('budget_check')['stage'],
                          'uses':lib.get('budget_check')['uses'],
                          'events':parity.view(r.store,r.session)['events'],
                          'c5_correction':correction}))
    finally:r.close()
'''
POSITIVE_PROBE = r'''
import json, tempfile, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from v13 import inputs, skill_parity_shadow_candidate as parity
from v13.agi import hub
from v13.operator import Operator
from v13.runtime import Runtime
with tempfile.TemporaryDirectory() as home:
    r=Runtime(Path(home))
    try:
        session=r.session;r.sleep.cycle.set_policy('enabled','off')
        r._route=Mock(return_value=('detail',{'source':'TEST_ROUTE_SEAM'}))
        r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},
                                                     generate=lambda *a,**k:iter(['2 + 2 = 5'])))
        r.learner.output_delta=Mock(return_value=None)
        lib=hub(r).skills
        lib.propose('chosen_route',[{'route':'detail'}],trigger='budget check')
        lib.set_stage('chosen_route','TRUSTED')
        lib.propose('shadow_route',[{'route':'detail'}],trigger='budget check')
        Operator(r).run(':skilllive parity-shadow on')
        eid=r.submit('Run a budget check for me')
        deadline=time.monotonic()+10
        while not r.idle() and time.monotonic()<deadline:time.sleep(.005)
        row=r.last_answer();meta=json.loads(row['metadata'])
        inputs.record_rating(r.store,eid,8,'EXPLICIT_NOTE')
        approved=lib.get('chosen_route')
        memory_id=r.memory.feedback(eid,'fact','2 + 2 = 4',key='arithmetic result')
        corrected=lib.get('chosen_route');conflict=parity.view(r.store,session)
        source=r.store.one('SELECT source_id FROM memories WHERE id=?',(memory_id,))['source_id']
        r.close();r=Runtime(Path(home));lib=hub(r).skills
        restored=lib.get('chosen_route');restored_view=parity.view(r.store,session)
        with r.store.tx() as c:c.execute('UPDATE sources SET deleted=1 WHERE id=?',(source,))
        revoked_view=parity.view(r.store,session)
        print(json.dumps({'status':row['status'],'used':meta.get('skill',{}).get('name'),
            'approved':[approved['uses'],approved['successes']],
            'corrected':[corrected['uses'],corrected['successes']],
            'restored':[restored['uses'],restored['successes']],
            'shadow_skill':lib.get('shadow_route')['stage'],
            'conflict':conflict,'restored_view':restored_view,'revoked_view':revoked_view,
            'updates':len(r.store.rows('SELECT * FROM updates'))}))
    finally:r.close()
'''


class SkillParityShadowIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.tmp.name)
        for mode, builder in (('baseline',build_ag4),('candidate',build_parity)):
            target=cls.root/mode
            shutil.copytree(CODE/'v13',target/'v13',ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(CODE/'specs',target/'specs')
            for build in (build_c5,build_memory,builder):
                for name,data in build(CODE/'v13').items():
                    (target/'v13'/name).write_bytes(data)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def scenario(self, mode):
        copy=self.root/('baseline' if mode=='baseline' else 'candidate')
        env=os.environ.copy();env['PYTHONPATH']=str(copy)
        proc=subprocess.run([sys.executable,'-c',PROBE,mode],cwd=copy,env=env,
                            text=True,capture_output=True,timeout=60)
        self.assertEqual(proc.returncode,0,proc.stderr)
        return json.loads(proc.stdout.strip().splitlines()[-1])

    def test_original_final_promotes_without_a_correctness_label(self):
        baseline=self.scenario('baseline')
        self.assertEqual((baseline['stage'],baseline['uses'],baseline['parity']),
                         ('SHADOW',3,[1.,1.,1.]))
        self.assertEqual(baseline['answer'],'2 + 2 = 5')

    def test_default_off_does_not_create_implicit_success(self):
        off=self.scenario('off')
        self.assertFalse(off['initial']);self.assertTrue(off['no_authority'])
        self.assertEqual((off['stage'],off['uses'],off['successes'],off['parity']),
                         ('CANDIDATE',0,0,[]))
        self.assertFalse(off['state_present'])
        self.assertFalse(off['instance_recorded'])
        self.assertEqual(off['corrected']['events'],0)
        self.assertTrue(off['corrupt_rejected'] and off['corrupt_enable_rejected'] and off['recovered'])
        self.assertEqual((off['learning_mode'],off['updates']),('RECORD_ONLY',0))

    def test_explicit_shadow_observes_and_revalidates_without_promotion(self):
        on=self.scenario('on')
        self.assertFalse(on['initial']);self.assertTrue(on['no_authority'])
        self.assertEqual((on['stage'],on['uses'],on['successes'],on['parity']),
                         ('CANDIDATE',0,0,[]))
        self.assertEqual(on['corrected']['learning_authority'],0)
        self.assertTrue(on['instance_recorded'])
        self.assertEqual(on['corrected']['events'],4)
        row=on['corrected']['by_skill']['budget_check']
        self.assertEqual((row['observations'],row['matches'],row['mismatches']),(4,3,1))
        self.assertEqual((row['explicit_positive'],row['explicit_negative'],row['implicit_rated']),(1,0,1))
        low=on['low']['by_skill']['budget_check']
        self.assertEqual((low['explicit_positive'],low['explicit_negative']),(0,1))
        fact=on['fact_seen']['by_skill']['budget_check']
        self.assertEqual((fact['fact_corrected'],fact['positive_and_fact_corrected']),(1,1))
        for label in ('fact_tampered','fact_wrong_kind','fact_revoked'):
            row=on[label]['by_skill']['budget_check']
            self.assertEqual((row['fact_corrected'],row['fact_source_unverified']),(0,1))
        self.assertEqual(on['duplicate'],'UNCHANGED')
        self.assertTrue(on['wrong_route_rejected']);self.assertTrue(on['still_enabled'])
        self.assertEqual(on['restored'],on['fact_revoked'])
        self.assertEqual(on['after_off']['events'],4)
        self.assertEqual((on['revoked']['events'],on['revoked']['excluded']),(3,1))
        self.assertEqual((on['replaced']['events'],on['replaced']['excluded']),(0,4))
        self.assertTrue(on['corrupt_rejected'] and on['corrupt_enable_rejected'] and on['recovered'])
        self.assertEqual((on['learning_mode'],on['updates']),('RECORD_ONLY',0))

    def test_modified_operator_source_is_rejected_without_writing_it(self):
        with tempfile.TemporaryDirectory() as home:
            source=Path(home)/'v13'
            shutil.copytree(CODE/'v13',source,ignore=shutil.ignore_patterns('__pycache__'))
            operator=source/'operator.py'
            original=operator.read_bytes()
            build_parity(source)
            self.assertEqual(operator.read_bytes(),original)
            operator.write_bytes(original+b'\n# changed\n')
            with self.assertRaises(ValueError):
                build_parity(source)

    def test_revoking_early_context_excludes_dependent_observations(self):
        result=self.scenario('cascade')
        self.assertEqual((result['revoked']['events'],result['revoked']['excluded']),(0,4))

    def test_shadow_capture_and_error_log_failure_do_not_block_turn_or_feedback(self):
        copy=self.root/'candidate'
        env=os.environ.copy();env['PYTHONPATH']=str(copy)
        proc=subprocess.run([sys.executable,'-c',FAULT_PROBE],cwd=copy,env=env,
                            text=True,capture_output=True,timeout=60)
        self.assertEqual(proc.returncode,0,proc.stderr)
        result=json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual((result['status'],result['answer']),('FINAL','synthetic answer'))
        self.assertEqual((result['stage'],result['uses'],result['events']),('CANDIDATE',0,0))
        self.assertGreater(result['c5_correction'],0)

    def test_fact_correction_retracts_selected_skill_and_marks_shadow_conflict(self):
        copy=self.root/'candidate'
        env=os.environ.copy();env['PYTHONPATH']=str(copy)
        proc=subprocess.run([sys.executable,'-c',POSITIVE_PROBE],cwd=copy,env=env,
                            text=True,capture_output=True,timeout=60)
        self.assertEqual(proc.returncode,0,proc.stderr)
        result=json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual((result['status'],result['used']),('FINAL','chosen_route'))
        self.assertEqual((result['approved'],result['corrected'],result['restored']),
                         ([1,1],[1,0],[1,0]))
        self.assertEqual(result['shadow_skill'],'CANDIDATE')
        conflict=result['conflict']['by_skill']['shadow_route']
        self.assertEqual((conflict['explicit_positive'],conflict['fact_corrected'],
                          conflict['positive_and_fact_corrected']),(1,1,1))
        self.assertEqual(result['restored_view'],result['conflict'])
        revoked=result['revoked_view']['by_skill']['shadow_route']
        self.assertEqual((revoked['fact_corrected'],revoked['fact_source_unverified']),(0,1))
        self.assertEqual(result['updates'],0)


if __name__=='__main__':
    unittest.main()
