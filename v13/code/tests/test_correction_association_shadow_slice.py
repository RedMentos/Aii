"""Real Runtime/Store/Sleep integration on a source-bound candidate copy."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.correction_association_integration_candidate import build_sources


CODE = Path(__file__).resolve().parents[1]
PROBE = r'''
import json, sys, tempfile, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from v13.runtime import Runtime
from v13.correction_association_shadow_candidate import KEY, set_mode, rollback, record_correction
from v13.operator import Operator

mode, replay, action = sys.argv[1], sys.argv[2] == 'yes', sys.argv[3]

def wire(r):
    r.sleep.cycle.set_policy('enabled','off')
    def gen(messages,*a,**k):yield 'I do not know.'
    r._route=Mock(return_value=('simple',{'source':'TEST_ROUTE_SEAM'}))
    r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},generate=gen))
    r.learner.output_delta=Mock(return_value=None)

def turn(r,text):
    eid=r.submit(text)
    end=time.monotonic()+10
    while not r.idle() and time.monotonic()<end:time.sleep(.005)
    if not r.idle():raise RuntimeError('turn timeout')
    row=r.last_answer()
    if not row or row['event_id']!=eid or row['status']!='FINAL':raise RuntimeError('turn failed: '+repr(row))
    return eid, row, json.loads(row['metadata'])

with tempfile.TemporaryDirectory() as home:
    r=Runtime(Path(home));wire(r)
    try:
        session=r.session
        if mode=='shadow':
            enabled=Operator(r).run(':episodes correction-association shadow')
            if 'shadow' not in enabled:raise RuntimeError('operator did not enable shadow')
        try:set_mode(r.store,'on');raise RuntimeError('active mode must not be available')
        except ValueError:pass
        base_event=r.store.event(session,'Project Ember budget')
        first=r.memory.feedback(base_event['event_id'],'fact','120 credits',key='Project Ember budget')
        eid,answer,meta=turn(r,'What are Project Ember budget and launch date?')
        before_ids=[x['memory_id'] for x in meta['memory_retrieval']]
        target=r.memory.feedback(eid,'fact','8 April',key='Project Ember launch date')
        state=r.store.state(KEY,None)[0]
        recorded=0 if state is None else len(state['links'])
        duplicate=record_correction(r.store,r.cfg,eid,target,session)['recorded']
        # Before rehearsal, even an existing association is never a candidate.
        _,pre,pre_meta=turn(r,'What is Project Ember budget?')
        pre_candidates=pre_meta.get('correction_association_shadow',[])
        passes=[]
        if replay:
            cy=r.sleep.cycle;st,version=cy.queue.load();policy=cy.policy()
            cy.queue.sync(st,policy)
            report=cy.sleep_a(st,policy,8,stage_candidates=False)
            cy.queue.save(st,version)
            passes=report['items']
        _,second,second_meta=turn(r,'What is Project Ember budget?')
        second_ids=[x['memory_id'] for x in second_meta['memory_retrieval']]
        shadow=second_meta.get('correction_association_shadow',[])
        text=second['text']
        r.close();r=Runtime(Path(home));wire(r)
        if r.session!=session:raise RuntimeError('session not restored')
        _,restart,restart_meta=turn(r,'What is Project Ember budget?')
        restored=restart_meta.get('correction_association_shadow',[])
        if action=='revoke':
            r.memory.forget(target)
            removed={'removed':0}
        elif action=='revoke_authority':
            sid=r.store.one('SELECT source_id FROM memories WHERE id=?',(target,))['source_id']
            with r.store.tx() as conn:
                conn.execute("DELETE FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(sid,))
            removed={'removed':0}
        else:
            removed=rollback(r.store,target) if mode=='shadow' else {'removed':0}
        _,after,after_meta=turn(r,'What is Project Ember budget?')
        recalled=r.memory.recall('Project Ember launch date',session)
        print(json.dumps({'first':first,'target':target,'prior_ids':before_ids,'recorded':recorded,
          'duplicate':duplicate,'pre_candidates':pre_candidates,'replay_items':passes,'second_ids':second_ids,
          'shadow':shadow,'answer':text,'restart_shadow':restored,'removed':removed['removed'],
          'after_shadow':after_meta.get('correction_association_shadow',[]),
          'target_still_recallable':target in [x['id'] for x in recalled],
          'learning_mode':r.cfg['learning_mode'],'updates':len(r.store.rows('SELECT * FROM updates'))}))
    finally:r.close()
'''


class CorrectionAssociationRuntimeSlice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.copy = Path(cls.tmp.name)
        shutil.copytree(CODE / 'v13', cls.copy / 'v13', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(CODE / 'specs', cls.copy / 'specs')
        for name, data in build_sources(CODE / 'v13').items():
            (cls.copy / 'v13' / name).write_bytes(data)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def scenario(self, mode, replay, action='rollback'):
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.copy)
        proc = subprocess.run([sys.executable, '-c', PROBE, mode, replay, action], cwd=self.copy,
                              env=env, text=True, capture_output=True, timeout=45)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout.strip().splitlines()[-1])

    def test_real_runtime_correction_replay_second_turn_restart_and_rollback(self):
        off = self.scenario('off', 'yes')
        unreplayed = self.scenario('shadow', 'no')
        shadow = self.scenario('shadow', 'yes')
        for result in (off, unreplayed, shadow):
            self.assertIn(result['first'], result['prior_ids'])
            self.assertIn(result['first'], result['second_ids'])
            self.assertNotIn(result['target'], result['second_ids'])
            self.assertEqual(result['answer'], 'I do not know.')
            self.assertEqual(result['learning_mode'], 'RECORD_ONLY')
            self.assertEqual(result['updates'], 0)
            self.assertTrue(result['target_still_recallable'])
        self.assertEqual(off['recorded'], 0)
        self.assertEqual(off['shadow'], [])
        self.assertEqual(unreplayed['recorded'], 1)
        self.assertEqual(unreplayed['duplicate'], 0)
        self.assertEqual(unreplayed['shadow'], [])
        self.assertEqual(shadow['pre_candidates'], [])
        self.assertTrue(any(item.get('outcome') == 'PASS' for item in shadow['replay_items']))
        self.assertEqual([x['memory_id'] for x in shadow['shadow']], [shadow['target']])
        self.assertEqual([x['memory_id'] for x in shadow['restart_shadow']], [shadow['target']])
        self.assertEqual(shadow['removed'], 1)
        self.assertEqual(shadow['after_shadow'], [])

    def test_revoking_a_correction_removes_its_shadow_candidate(self):
        result = self.scenario('shadow', 'yes', 'revoke')
        self.assertEqual([x['memory_id'] for x in result['restart_shadow']], [result['target']])
        self.assertEqual(result['after_shadow'], [])
        self.assertFalse(result['target_still_recallable'])

    def test_lost_human_authority_invalidates_existing_replay(self):
        result = self.scenario('shadow', 'yes', 'revoke_authority')
        self.assertEqual([x['memory_id'] for x in result['restart_shadow']], [result['target']])
        self.assertEqual(result['after_shadow'], [])
        self.assertFalse(result['target_still_recallable'])

    def test_source_binding_rejects_changed_runtime_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            from scripts.correction_association_integration_candidate import BASE_SHA256
            for name in BASE_SHA256:
                shutil.copy2(CODE / 'v13' / name, source / name)
            with (source / 'sleep.py').open('ab') as stream:
                stream.write(b'\n')
            with self.assertRaisesRegex(ValueError, 'unsupported source: sleep.py'):
                build_sources(source)


if __name__ == '__main__':
    unittest.main()
