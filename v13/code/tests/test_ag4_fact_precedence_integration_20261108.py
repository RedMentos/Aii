"""Real Runtime/SQLite tests for source-checked human-outcome precedence."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts.ag4_fact_precedence_integration_candidate import build_sources as build_precedence
from scripts.c5_outcome_credit_candidate import build_sources as build_c5
from scripts.correction_association_integration_candidate import build_sources as build_memory
from scripts.skill_parity_shadow_integration_candidate import build_sources as build_previous
from test_multiorgan_correction_candidate_20261108 import PROBE as MULTIORGAN_PROBE


CODE=Path(__file__).resolve().parents[1]
PROBE=r'''
import json,sys,tempfile,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import Mock,patch
from v13 import inputs,skilllive,skill_parity_shadow_candidate as parity
from v13.ag4_fact_precedence_candidate import routed_eligible,PENDING_KEY
from v13.agi import hub,live
from v13.operator import Operator
from v13.runtime import Runtime

mode=sys.argv[1]
candidate_version=sys.argv[2]=='candidate'
def setup(home):
    r=Runtime(Path(home));r.sleep.cycle.set_policy('enabled','off')
    r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},
                                                 generate=lambda *a,**k:iter(['2 + 2 = 5'])))
    r.learner.output_delta=Mock(return_value=None)
    lib=hub(r).skills
    lib.propose('math_route',[{'route':'simple'}],trigger='math check');lib.set_stage('math_route','TRUSTED')
    lib.propose('math_shadow',[{'route':'simple'}],trigger='math check')
    Operator(r).run(':skilllive parity-shadow on')
    Operator(r).run(':c5 feedback-shadow on')
    eid=r.submit('Please do a math check')
    deadline=time.monotonic()+10
    while not r.idle() and time.monotonic()<deadline:time.sleep(.005)
    row=r.last_answer()
    if not row or row['event_id']!=eid or row['status']!='FINAL':raise RuntimeError('turn failed')
    return r,lib,eid
def stats(lib):
    sk=lib.get('math_route');return [sk['uses'],sk['successes']]

if mode=='race':
    trials=[]
    for _ in range(5):
        with tempfile.TemporaryDirectory() as home:
            r,lib,eid=setup(home)
            try:
                barrier=Barrier(2)
                def rating():barrier.wait();return inputs.record_rating(r.store,eid,8,'EXPLICIT_NOTE')
                def fact():barrier.wait();return r.memory.feedback(eid,'fact','2 + 2 = 4',key='result')
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures=[pool.submit(rating),pool.submit(fact)]
                    for future in futures:future.result()
                trials.append(stats(lib))
            finally:r.close()
    print(json.dumps({'trials':trials}))
else:
    with tempfile.TemporaryDirectory() as home:
        r,lib,eid=setup(home)
        try:
            if mode=='binding_tamper':
                row=r.store.one("SELECT id,metadata FROM messages WHERE event_id=? AND role='assistant'",(eid,))
                meta=json.loads(row['metadata']);meta['skill']['human_binding']['instance']='forged'
                with r.store.tx() as c:c.execute('UPDATE messages SET metadata=? WHERE id=?',(json.dumps(meta),row['id']))
                inputs.record_rating(r.store,eid,8,'EXPLICIT_NOTE')
                print(json.dumps({'stats':stats(lib),'rating':inputs.ratings(r.store)[-1]['score']}))
            elif mode=='atomic_failure':
                inputs.record_rating(r.store,eid,8,'EXPLICIT_NOTE')
                before=stats(lib);before_marker=live._load(r.store,eid)
                with r.store.tx() as c:
                    c.execute("CREATE TEMP TRIGGER fail_live_state BEFORE INSERT ON states "
                              "WHEN NEW.key LIKE 'agi-live:%' BEGIN SELECT RAISE(ABORT,'injected'); END")
                memory_id=r.memory.feedback(eid,'fact','2 + 2 = 4',key='result')
                after_failure=stats(lib);marker_unchanged=(live._load(r.store,eid)==before_marker)
                source=r.store.one('SELECT source_id FROM memories WHERE id=?',(memory_id,))['source_id']
                with r.store.tx() as c:c.execute('DROP TRIGGER fail_live_state')
                live.on_feedback(r.store,eid,'fact','2 + 2 = 4',memory_id,source,'result')
                print(json.dumps({'before':before,'after_failure':after_failure,
                                  'marker_unchanged':marker_unchanged,'after_retry':stats(lib)}))
            elif mode=='pending_atomic_failure':
                with r.store.tx() as c:
                    c.execute("CREATE TEMP TRIGGER fail_live_state BEFORE INSERT ON states "
                              "WHEN NEW.key LIKE 'agi-live:%' BEGIN SELECT RAISE(ABORT,'injected'); END")
                memory_id=r.memory.feedback(eid,'fact','2 + 2 = 4',key='result')
                after_failure=stats(lib);pending_after_failure=r.store.state(PENDING_KEY)[0]
                guard_after_failure=routed_eligible(r.store,'math_route')
                source=r.store.one('SELECT source_id FROM memories WHERE id=?',(memory_id,))['source_id']
                with r.store.tx() as c:c.execute('DROP TRIGGER fail_live_state')
                live.on_feedback(r.store,eid,'fact','2 + 2 = 4',memory_id,source,'result')
                pending_after_retry=r.store.state(PENDING_KEY)[0] is not None
                guard_after_retry=routed_eligible(r.store,'math_route')
                r.close();r=Runtime(Path(home));lib=hub(r).skills
                print(json.dumps({'after_failure':after_failure,'pending_after_failure':pending_after_failure,
                    'guard_after_failure':guard_after_failure,'pending_after_retry':pending_after_retry,
                    'guard_after_retry':guard_after_retry,'guard_after_restart':routed_eligible(r.store,'math_route'),
                    'after_restart':stats(lib)}))
            elif mode=='skipped_fact_hook':
                with patch('v13.agi.live.on_feedback',side_effect=RuntimeError('hook unavailable')):
                    r.memory.feedback(eid,'fact','2 + 2 = 4',key='result')
                print(json.dumps({'stats':stats(lib),'pending':r.store.state(PENDING_KEY)[0],
                                  'eligible':routed_eligible(r.store,'math_route')}))
            elif mode=='skipped_rating_hook':
                with patch('v13.agi.live.on_rating',side_effect=RuntimeError('hook unavailable')):
                    inputs.record_rating(r.store,eid,8,'EXPLICIT_NOTE')
                before=stats(lib);guard_before=routed_eligible(r.store,'math_route')
                live.on_rating(r.store,eid,8,origin='EXPLICIT_NOTE')
                print(json.dumps({'before':before,'guard_before':guard_before,
                                  'after':stats(lib),'guard_after':routed_eligible(r.store,'math_route')}))
            elif mode=='fact_first':
                r.memory.feedback(eid,'fact','2 + 2 = 4',key='result')
                before=stats(lib);guard_before=routed_eligible(r.store,'math_route') if candidate_version else None
                inputs.record_rating(r.store,eid,8,'EXPLICIT_NOTE')
                print(json.dumps({'after_fact':before,'after_positive':stats(lib),
                                  'guard_after_fact':guard_before,
                                  'guard_after_positive':routed_eligible(r.store,'math_route') if candidate_version else None}))
            elif mode=='fact_learn_only':
                r.memory.feedback(eid,'fact','2 + 2 = 4',permission='learn',key='result')
                print(json.dumps({'stats':stats(lib),'eligible':routed_eligible(r.store,'math_route')}))
            elif mode=='forget_then_rate':
                memory_id=r.memory.feedback(eid,'fact','2 + 2 = 4',key='result')
                before=stats(lib);guard_before=routed_eligible(r.store,'math_route')
                r.memory.forget(memory_id)
                guard_after_forget=routed_eligible(r.store,'math_route')
                inputs.record_rating(r.store,eid,8,'EXPLICIT_NOTE')
                print(json.dumps({'before':before,'guard_before':guard_before,
                                  'guard_after_forget':guard_after_forget,'after':stats(lib),
                                  'guard_after_rating':routed_eligible(r.store,'math_route')}))
            elif mode=='stale':
                inputs.record_rating(r.store,eid,2,'EXPLICIT_NOTE');before=stats(lib)
                live.on_rating(r.store,eid,8,origin='EXPLICIT_NOTE')
                print(json.dumps({'before':before,'after_stale':stats(lib),
                                  'rating':inputs.ratings(r.store)[-1]['score']}))
            elif mode=='implicit':
                inputs.record_rating(r.store,eid,8,'IMPLICIT_CHAT');implicit=stats(lib)
                inputs.record_rating(r.store,eid,2,'EXPLICIT_NOTE');explicit=stats(lib)
                inputs.record_rating(r.store,eid,8,'IMPLICIT_CHAT')
                print(json.dumps({'implicit':implicit,'explicit':explicit,'after_implicit':stats(lib)}))
            elif mode=='duplicate_rating':
                from v13.agi.metacog import Metacognition
                inputs.record_rating(r.store,eid,8,'EXPLICIT_NOTE')
                inputs.record_rating(r.store,eid,8,'EXPLICIT_NOTE')
                calibration=Metacognition(r.store).report('answer')['components']['answer']['n']
                r.close();r=Runtime(Path(home));lib=hub(r).skills
                inputs.record_rating(r.store,eid,8,'EXPLICIT_NOTE')
                print(json.dumps({'stats':stats(lib),'calibration':calibration}))
            elif mode=='no_confidence':
                live._save(r.store,eid,answer_confidence=None)
                inputs.record_rating(r.store,eid,8,'EXPLICIT_NOTE')
                print(json.dumps({'stats':stats(lib)}))
            elif mode=='metacog_fail':
                with patch('v13.agi.metacog.Metacognition.record_batch',side_effect=ValueError('invalid')):
                    inputs.record_rating(r.store,eid,8,'EXPLICIT_NOTE')
                after_rating=stats(lib)
                with patch('v13.agi.metacog.Metacognition.record',side_effect=ValueError('invalid')):
                    r.memory.feedback(eid,'fact','2 + 2 = 4',key='result')
                print(json.dumps({'after_rating':after_rating,'after_fact':stats(lib)}))
            elif mode=='turn_revoked':
                inputs.record_rating(r.store,eid,8,'EXPLICIT_NOTE')
                check=r.store.event(r.session,'Please do a math check')
                before=skilllive.automatic(r,check,'Please do a math check',{})
                source=r.store.one('SELECT source_id FROM events WHERE id=?',(eid,))['source_id']
                with r.store.tx() as c:c.execute('UPDATE sources SET deleted=1 WHERE id=?',(source,))
                inputs.record_rating(r.store,eid,2,'EXPLICIT_NOTE')
                check=r.store.event(r.session,'Please do a math check')
                after=skilllive.automatic(r,check,'Please do a math check',{})
                fallback=live.skill_route(r,check,'Please do a math check','detail',False,{})
                print(json.dumps({'before':before and before[0],'after':after,'fallback':fallback,
                                  'eligible':routed_eligible(r.store,'math_route'),
                                  'stats':stats(lib),'rating':inputs.ratings(r.store)[-1]['score']}))
            elif mode=='conflict_guard':
                lib.propose('other_route',[{'route':'gist'}],trigger='math check')
                lib.set_stage('other_route','TRUSTED')
                r.memory.feedback(eid,'fact','2 + 2 = 4',key='result')
                check=r.store.event(r.session,'Please do a math check')
                automatic=skilllive.automatic(r,check,'Please do a math check',{})
                fallback=live.skill_route(r,check,'Please do a math check','detail',False,{})
                print(json.dumps({'automatic':automatic,'fallback':fallback,
                                  'first_eligible':routed_eligible(r.store,'math_route'),
                                  'second_eligible':routed_eligible(r.store,'other_route')}))
            elif mode=='neutral':
                inputs.record_rating(r.store,eid,8,'EXPLICIT_NOTE');positive=stats(lib)
                inputs.record_rating(r.store,eid,5,'EXPLICIT_NOTE');first_neutral=stats(lib)
                inputs.record_rating(r.store,eid,5,'EXPLICIT_NOTE');repeat_neutral=stats(lib)
                inputs.record_rating(r.store,eid,2,'EXPLICIT_NOTE');negative=stats(lib)
                inputs.record_rating(r.store,eid,5,'EXPLICIT_NOTE');second_neutral=stats(lib)
                print(json.dumps({'positive':positive,'first_neutral':first_neutral,
                    'repeat_neutral':repeat_neutral,'negative':negative,'second_neutral':second_neutral,
                    'rating':inputs.ratings(r.store)[-1]['score']}))
            elif mode=='neutral_fact':
                inputs.record_rating(r.store,eid,8,'EXPLICIT_NOTE')
                r.memory.feedback(eid,'fact','2 + 2 = 4',key='result');before=stats(lib)
                inputs.record_rating(r.store,eid,5,'EXPLICIT_NOTE')
                print(json.dumps({'before':before,'after':stats(lib)}))
            else:
                inputs.record_rating(r.store,eid,8,'EXPLICIT_NOTE');positive=stats(lib)
                memory_id=r.memory.feedback(eid,'fact','2 + 2 = 4',key='result');fact=stats(lib)
                inputs.record_rating(r.store,eid,8,'EXPLICIT_NOTE');repeat=stats(lib)
                session=r.session;r.close();r=Runtime(Path(home));lib=hub(r).skills
                inputs.record_rating(r.store,eid,9,'EXPLICIT_NOTE');after_restart=stats(lib)
                view=parity.view(r.store,session)
                source=r.store.one('SELECT source_id FROM memories WHERE id=?',(memory_id,))['source_id']
                guard_before=routed_eligible(r.store,'math_route') if candidate_version else None
                with r.store.tx() as c:c.execute('UPDATE sources SET deleted=1 WHERE id=?',(source,))
                inputs.record_rating(r.store,eid,8,'EXPLICIT_NOTE');after_revocation=stats(lib)
                guard_after=routed_eligible(r.store,'math_route') if candidate_version else None
                marker=live._load(r.store,eid)
                print(json.dumps({'positive':positive,'fact':fact,'repeat':repeat,
                    'after_restart':after_restart,'after_revocation':after_revocation,
                    'conflict':view['by_skill']['math_shadow'],
                    'rating':inputs.ratings(r.store)[-1]['score'],
                    'guard_before':guard_before,'guard_after':guard_after,
                    'marker':{'disputed':marker.get('skill_disputed'),
                              'reason':marker.get('skill_feedback_reason')},
                    'updates':len(r.store.rows('SELECT * FROM updates'))}))
        finally:r.close()
'''


class AG4FactPrecedence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        for name,builder in (('baseline',build_previous),('candidate',build_precedence)):
            target=cls.root/name
            shutil.copytree(CODE/'v13',target/'v13',ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(CODE/'specs',target/'specs')
            for build in (build_c5,build_memory,builder):
                for path,data in build(CODE/'v13').items():
                    (target/'v13'/path).write_bytes(data)

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def scenario(self,mode,baseline=False):
        target=self.root/('baseline' if baseline else 'candidate')
        env=os.environ.copy();env['PYTHONPATH']=str(target)
        proc=subprocess.run([sys.executable,'-c',PROBE,mode,'baseline' if baseline else 'candidate'],cwd=target,env=env,
                            text=True,capture_output=True,timeout=60)
        self.assertEqual(proc.returncode,0,proc.stderr)
        return json.loads(proc.stdout.strip().splitlines()[-1])

    def test_original_repeated_positive_overwrites_fact_correction(self):
        result=self.scenario('sequence',baseline=True)
        self.assertEqual((result['positive'],result['fact'],result['repeat']),([1,1],[1,0],[1,1]))

    def test_current_fact_has_precedence_across_redelivery_restart_and_revocation(self):
        result=self.scenario('sequence')
        self.assertEqual(result['positive'],[1,1])
        self.assertEqual((result['fact'],result['repeat'],result['after_restart'],result['after_revocation']),
                         ([1,0],[1,0],[1,0],[1,0]))
        self.assertEqual(result['rating'],8)
        self.assertFalse(result['guard_before']);self.assertFalse(result['guard_after'])
        self.assertEqual(result['marker'],{'disputed':True,'reason':'FACT_PRECEDENCE'})
        conflict=result['conflict']
        self.assertEqual((conflict['explicit_positive'],conflict['fact_corrected'],
                          conflict['positive_and_fact_corrected']),(1,1,1))
        self.assertEqual(result['updates'],0)

    def test_fact_before_positive_still_blocks_success(self):
        result=self.scenario('fact_first')
        self.assertEqual((result['after_fact'],result['after_positive']),([0,0],[1,0]))
        self.assertFalse(result['guard_after_fact']);self.assertFalse(result['guard_after_positive'])

    def test_fact_marked_learn_is_only_pending_without_an_explicit_rating(self):
        result=self.scenario('fact_learn_only')
        self.assertEqual(result['stats'],[0,0])
        self.assertFalse(result['eligible'])

    def test_forgetting_fact_then_new_explicit_rating_resolves_pending_state(self):
        result=self.scenario('forget_then_rate')
        self.assertEqual((result['before'],result['after']),([0,0],[1,1]))
        self.assertFalse(result['guard_before']);self.assertFalse(result['guard_after_forget'])
        self.assertTrue(result['guard_after_rating'])

    def test_delayed_old_positive_cannot_override_current_negative_note(self):
        result=self.scenario('stale')
        self.assertEqual((result['before'],result['after_stale'],result['rating']),([1,0],[1,0],2))

    def test_implicit_feedback_does_not_credit_or_reverse_explicit_feedback(self):
        result=self.scenario('implicit')
        self.assertEqual((result['implicit'],result['explicit'],result['after_implicit']),
                         ([0,0],[1,0],[1,0]))

    def test_metacognition_failure_does_not_skip_actual_human_outcome(self):
        result=self.scenario('metacog_fail')
        self.assertEqual((result['after_rating'],result['after_fact']),([1,1],[1,0]))

    def test_repeated_real_rating_stays_single_through_restart(self):
        result=self.scenario('duplicate_rating')
        self.assertEqual(result['stats'],[1,1]);self.assertEqual(result['calibration'],1)

    def test_real_rating_credits_skill_without_metacognition_confidence(self):
        self.assertEqual(self.scenario('no_confidence')['stats'],[1,1])

    def test_tampered_turn_binding_keeps_rating_but_rejects_skill_credit(self):
        result=self.scenario('binding_tamper')
        self.assertEqual((result['stats'],result['rating']),([0,0],8))

    def test_revoked_turn_source_disables_both_skill_fast_paths(self):
        result=self.scenario('turn_revoked')
        self.assertEqual((result['before'],result['after'],result['fallback']),('simple',None,'detail'))
        self.assertFalse(result['eligible'])
        self.assertEqual((result['stats'],result['rating']),([1,1],2))

    def test_blocked_skill_does_not_hide_conflicting_trusted_skill(self):
        result=self.scenario('conflict_guard')
        self.assertEqual((result['automatic'],result['fallback']),(None,'detail'))
        self.assertFalse(result['first_eligible']);self.assertTrue(result['second_eligible'])

    def test_original_neutral_note_leaves_old_positive_credit(self):
        result=self.scenario('neutral',baseline=True)
        self.assertEqual((result['positive'],result['first_neutral']),([1,1],[1,1]))

    def test_neutral_note_retracts_previous_positive_or_negative_once(self):
        result=self.scenario('neutral')
        self.assertEqual((result['positive'],result['first_neutral'],result['repeat_neutral']),
                         ([1,1],[0,0],[0,0]))
        self.assertEqual((result['negative'],result['second_neutral'],result['rating']),
                         ([1,0],[0,0],5))

    def test_neutral_note_does_not_erase_verified_fact_correction(self):
        result=self.scenario('neutral_fact')
        self.assertEqual((result['before'],result['after']),([1,0],[1,0]))

    def test_store_abort_rolls_back_both_states_and_retry_succeeds(self):
        result=self.scenario('atomic_failure')
        self.assertEqual((result['before'],result['after_failure'],result['after_retry']),([1,1],[1,1],[1,0]))
        self.assertTrue(result['marker_unchanged'])

    def test_pending_write_abort_keeps_fact_blocked_until_retry_and_restart(self):
        result=self.scenario('pending_atomic_failure')
        self.assertEqual((result['after_failure'],result['after_restart']),([0,0],[0,0]))
        self.assertIsNone(result['pending_after_failure'])
        self.assertTrue(result['pending_after_retry'])
        self.assertFalse(result['guard_after_failure'])
        self.assertFalse(result['guard_after_retry']);self.assertFalse(result['guard_after_restart'])

    def test_skipped_fact_hook_still_blocks_automatic_skill_reuse(self):
        result=self.scenario('skipped_fact_hook')
        self.assertEqual(result['stats'],[0,0]);self.assertIsNone(result['pending'])
        self.assertFalse(result['eligible'])

    def test_skipped_rating_hook_blocks_reuse_until_source_checked_retry(self):
        result=self.scenario('skipped_rating_hook')
        self.assertEqual((result['before'],result['after']),([0,0],[1,1]))
        self.assertFalse(result['guard_before']);self.assertTrue(result['guard_after'])

    def test_concurrent_rating_and_fact_settle_to_one_negative_outcome(self):
        result=self.scenario('race')
        self.assertEqual(result['trials'],[[1,0]]*5)

    def test_existing_c5_and_replay_scenarios_with_source_checked_precedence(self):
        target=self.root/'candidate'
        env=os.environ.copy();env['PYTHONPATH']=str(target)
        for mode in ('on','positive'):
            with self.subTest(mode=mode):
                proc=subprocess.run([sys.executable,'-c',MULTIORGAN_PROBE,mode],cwd=target,env=env,
                                    text=True,capture_output=True,timeout=60)
                self.assertEqual(proc.returncode,0,proc.stderr)
                result=json.loads(proc.stdout.strip().splitlines()[-1])
                self.assertEqual(result['used_skill'],'ember_route')
                self.assertEqual((result['after_fact'],result['after_restart']),([1,0],[1,0]))
                self.assertEqual(result['after_explicit'],[1,1] if mode=='positive' else [1,0])
                self.assertTrue(result['replay_pass'])
                self.assertEqual((result['learning_mode'],result['updates']),('RECORD_ONLY',0))
                if mode=='on':
                    self.assertEqual(result['feedback']['events'],1)
                    self.assertEqual([x['memory_id'] for x in result['second_shadow']],[result['correction']])


if __name__=='__main__':unittest.main()
