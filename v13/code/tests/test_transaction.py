"""WP-K: action transaction (IH-H14), tool security contract (IH-H29), output commit point (IH-H12), provisional buffer (IH-H13)."""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from v13.runtime import Runtime
from v13.operator import Operator
from v13 import transaction as K
from v13.agi.tools import ToolRegistry,ToolSpec

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        self.t=[1000.];self.T=K.Transactions(self.r.store,clock=lambda:self.t[0])
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def kinds(self,kind,aid):return [json.loads(x['payload']) for x in self.r.store.rows("SELECT payload FROM packets WHERE kind=?",(kind,)) if json.loads(x['payload'])['action_id']==aid]

class TransactionTests(Base):
    def test_copy_committed_before_side_effect_and_order(self):
        a=self.T.prepare(None,'demo',{'x':'1'},'USER','READ_LOCAL',True);seen={}
        with self.assertRaises(ValueError):self.T.execute(a['id'],lambda x:x)  # no effect before the copy
        self.T.commit_copy(a['id'],{'k':1})
        def effect(x):
            seen['copy']=len(self.kinds('CorollaryCopy',a['id']));seen['state']=self.T.get(a['id'])['state'];return x+'!'
        done=self.T.execute(a['id'],effect)
        self.assertEqual(seen,{'copy':1,'state':'EXECUTING'});self.assertEqual((done['state'],done['result']),('SUCCEEDED','1!'))
        self.assertEqual([s for s,_ in done['trail']],['PREPARED','COPY_COMMITTED','EXECUTING','SUCCEEDED'])
        self.assertEqual(self.kinds('ActionOutcome',a['id'])[0]['status'],'SUCCEEDED');self.assertEqual(len(self.kinds('ActionIntent',a['id'])),1)
        with self.assertRaises(ValueError):self.T.cancel(a['id'])
    def test_crash_during_execution_becomes_unknown_never_rerun(self):
        a=self.T.prepare(None,'demo',{},'USER','WRITE_LOCAL',False);self.T.commit_copy(a['id'])
        self.T._write(lambda st:self.T._move(st,a['id'],'EXECUTING'))  # process dies here
        old=self.T.prepare(None,'demo',{},'USER','READ_LOCAL',True);self.t[0]+=K.STALE_PREPARED_S+1
        self.assertEqual(self.T.recover(),{'UNKNOWN':1,'CANCELLED':1})
        self.assertEqual(self.T.get(a['id'])['state'],'UNKNOWN');self.assertEqual(self.T.get(old['id'])['state'],'CANCELLED')
        with self.assertRaises(ValueError):self.T.execute(a['id'],lambda:None)
    def test_idempotency_key_deduplicates(self):
        calls=[];reg=ToolRegistry(self.r.store);reg.register(ToolSpec('count',lambda:calls.append(1) or len(calls),schema={}));reg.enable('count')
        self.assertEqual(reg.call('count',{},idempotency_key='k1')['status'],'EXECUTED')
        again=reg.call('count',{},idempotency_key='k1');self.assertEqual((again['status'],again['result']),('DEDUPLICATED',1));self.assertEqual(len(calls),1)

class ContractTests(Base):
    def test_schema_namespace_and_shell_strings(self):
        for bad in (':status','Rm','a b','x'):
            with self.assertRaises(ValueError):ToolSpec(bad,lambda:0)
        self.assertEqual(K.check_args({'n':'int','s':'str?'},{'n':3}),[])
        self.assertIn('type:n',K.check_args({'n':'int'},{'n':True}));self.assertIn('missing_arg:n',K.check_args({'n':'int'},{}))
        self.assertIn('unexpected_arg:z',K.check_args({},{'z':'1'}));self.assertIn('unsafe_arg:s',K.check_args({'s':'str'},{'s':'a; rm -rf /'}))
        reg=ToolRegistry(self.r.store);reg.enable('calc')
        tx=reg.call('calc',{'expression':'1+1','extra':'x'});self.assertTrue(tx['reason'].startswith('SCHEMA:'));self.assertEqual(tx['status'],'DENIED')
        self.assertEqual(reg.call('calc',{'expression':'2*3'})['result'],6)
        self.assertEqual(reg.call('calc',{'expression':'1+1'},origin='SELF')['reason'],'AGE_RIGHT:simple_tool_choice')  # Age 0
    def test_secrets_are_handles_resolved_only_in_executor(self):
        reg=ToolRegistry(self.r.store);reg.register(ToolSpec('echo_key',lambda key:'got '+key,schema={'key':'secret'}));reg.enable('echo_key')
        with patch.dict(os.environ,{'V13_SECRET_API':'s3cr3t-value'}):tx=reg.call('echo_key',{'key':{'$secret':'api'}})
        self.assertEqual((tx['status'],tx['result']),('EXECUTED','got [REDACTED]'))
        dump=json.dumps([self.r.store.state(k)[0] for k in (K.KEY,'G10_TOOLS')])+json.dumps(self.r.store.rows("SELECT payload FROM packets"))+json.dumps(self.r.store.rows("SELECT metrics FROM telemetry"))
        self.assertNotIn('s3cr3t-value',dump)
        with patch.dict(os.environ,{},clear=False):
            os.environ.pop('V13_SECRET_API',None);tx=reg.call('echo_key',{'key':{'$secret':'api'}})
        self.assertEqual(tx['status'],'FAILED');self.assertIn('PermissionError',tx['error'])
        self.assertEqual(reg.call('echo_key',{'key':'plain'})['status'],'DENIED')
    def test_write_tool_needs_approval_runs_sandboxed_and_undoes(self):
        reg=ToolRegistry(self.r.store);reg.enable('sandbox_note');f=Path(self.tmp.name)/'data/tool_sandbox/todo.txt'
        tx=reg.call('sandbox_note',{'name':'todo','text':'milk'});self.assertEqual((tx['status'],tx['reason']),('PROPOSED','NEEDS_PER_CALL_APPROVAL'));self.assertFalse(f.exists())
        done=reg.approve(tx['id']);self.assertEqual(done['status'],'EXECUTED');self.assertEqual(f.read_text(),'milk')
        tx2=reg.approve(reg.call('sandbox_note',{'name':'todo','text':'bread'})['id']);self.assertEqual(f.read_text(),'bread')
        self.assertEqual(reg.undo(tx2['id'])['state'],'SUCCEEDED');self.assertEqual(f.read_text(),'milk')
        with self.assertRaises(ValueError):reg.undo(tx2['id'])
        reg.undo(done['id']);self.assertFalse(f.exists())
        bad=reg.approve(reg.call('sandbox_note',{'name':'../x','text':'y'})['id']);self.assertEqual(bad['status'],'FAILED')
        with self.assertRaises(ValueError):reg.approve(tx['id'])  # already decided

class ProvisionalTests(Base):
    def test_turn_outcome_waits_for_final_and_revision_tombstones(self):
        got=[];reg=ToolRegistry(self.r.store,on_outcome=got.append);reg.enable('calc');P=K.Provisional(self.r.store)
        e1=self.r.store.event(self.r.session,'a')['event_id'];e2=self.r.store.event(self.r.session,'b')['event_id']
        reg.call('calc',{'expression':'1+2'},event_id=e1);reg.call('calc',{'expression':'2+2'},event_id=e2)
        self.assertEqual(got,[]);self.assertEqual(P.report()['live'],2)
        self.assertEqual(P.settle(e1,'FINAL')['promoted'],1);self.assertEqual(got[0]['result'],3)
        self.assertEqual(P.settle(e2,'ERROR')['tombstoned'],1);self.assertEqual(len(got),1)
        st=self.r.store.state(K.PROVISIONAL_KEY)[0];self.assertTrue(all('payload' not in x for x in st['items'].values()))
        self.assertEqual(K.learning_factor('PROVISIONAL'),0.);self.assertEqual(K.learning_factor('FINAL'),.8)
    def test_approval_after_turn_end_reaches_grounding(self):
        # Thread M finding: a call proposed in a turn and approved after that turn ended was parked in the provisional
        # buffer of a turn that never settles again, so AG2 grounding never saw it (TTL tombstone).
        got=[];reg=ToolRegistry(self.r.store,on_outcome=got.append);reg.enable('sandbox_note');P=K.Provisional(self.r.store)
        e=self.r.store.event(self.r.session,'note this')['event_id']
        tx=reg.call('sandbox_note',{'name':'n1','text':'hi'},event_id=e);self.assertEqual(tx['status'],'PROPOSED')
        open_tx=reg.call('sandbox_note',{'name':'n2','text':'yo'},event_id=e)
        reg.approve(open_tx['id']);self.assertEqual(got,[]);self.assertEqual(P.report()['live'],1)  # turn still running: stays provisional
        self.r.store.message(self.r.session,e,'assistant','[Aktion wartet auf Freigabe]','FINAL',{});P.settle(e,'FINAL')
        self.assertEqual([g['args']['name'] for g in got],['n2'])
        done=reg.approve(tx['id']);self.assertEqual(done['status'],'EXECUTED')
        self.assertEqual([g['args']['name'] for g in got],['n2','n1']);self.assertEqual(P.report()['live'],0)
    def test_ttl_expiry(self):
        t=[0.];P=K.Provisional(self.r.store,clock=lambda:t[0]);P.put('e','x',{'v':1},ttl_s=10);t[0]=11
        self.assertEqual(P.settle('e','FINAL'),{'promoted':0,'tombstoned':0,'no_sink':0});self.assertEqual(P.report()['counts']['tombstoned'],1)

class OutputCommitTests(Base):
    def test_turn_commits_before_first_byte_and_corrections_append(self):
        def gen(messages,*a,**k):
            row=self.r.store.one("SELECT status FROM messages WHERE role='assistant' ORDER BY id DESC LIMIT 1");seen.append(row['status']);yield 'fine'
        seen=[];self.r._route=Mock(return_value=('simple',{'source':'TEST_ROUTE_SEAM'}))
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},generate=gen));self.r.learner.output_delta=Mock(return_value=None)
        self.r.submit('hello there');until=time.monotonic()+10
        while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
        ans=self.r.last_answer();meta=json.loads(ans['metadata'])
        self.assertEqual(seen[0],'DRAFT');self.assertEqual(ans['status'],'FINAL');self.assertTrue(meta['output_committed'])
        self.assertLessEqual(meta['output_committed_monotonic_ns'],meta['first_output_monotonic_ns'])
        with self.assertRaises(ValueError):self.r.store.append_message(ans['id'],'rewrite')
        cid=K.correction(self.r.store,self.r.session,ans['event_id'],ans['id'],'Correction: x','LATE_OFFER')
        self.assertEqual(self.r.store.one("SELECT text FROM messages WHERE id=?",(ans['id'],))['text'],'fine')
        self.assertEqual(json.loads(self.r.store.one("SELECT metadata FROM messages WHERE id=?",(cid,))['metadata'])['correction_of'],ans['id'])
        self.assertFalse(K.commit_output(self.r.store,ans['id'],ans['event_id']))
    def test_operator(self):
        op=Operator(self.r);self.assertIn('counts',op.run(':tx'));self.assertIn('factors',op.run(':tx provisional'))
        reg=ToolRegistry(self.r.store);self.r.growth=SimpleNamespace(tools=reg);reg.enable('sandbox_note')
        tx=reg.call('sandbox_note',{'name':'n1','text':'hi'});out=json.loads(op.run(':tx approve '+tx['id']));self.assertEqual(out['status'],'EXECUTED')
        self.assertEqual(json.loads(op.run(':tx undo '+tx['id']))['state'],'SUCCEEDED')

if __name__=='__main__':unittest.main()
