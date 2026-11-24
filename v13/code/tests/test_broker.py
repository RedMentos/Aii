"""WP-T7: output broker precedence, every C6 egress kind, sandbox tool preview/approval/undo in the live turn. No models."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from v13.runtime import Runtime
from v13.operator import Operator
from v13 import broker as B
from v13 import actionlearn as A
from v13.agi import hub
from v13.agi.tools import ToolRegistry

class DecideTests(unittest.TestCase):
    def test_precedence_before_commit(self):
        d=B.decide(['MODEL_ANSWER','EXPLICIT_EXACT_COPY','APPROVED_FIXED_RULE'])
        self.assertEqual(d['selected'],'APPROVED_FIXED_RULE');self.assertEqual(d['overridden'],['EXPLICIT_EXACT_COPY','MODEL_ANSWER'])
        self.assertEqual(B.decide(['SOURCE_SYSTEM_REPORT','MODEL_ANSWER'])['selected'],'MODEL_ANSWER')  # partial model text beats the diagnostic
        self.assertIsNone(B.decide([])['selected'])
    def test_after_commit_nothing_is_replaced(self):
        d=B.decide(['APPROVED_FIXED_RULE','SOURCE_SYSTEM_REPORT'],committed='MODEL_ANSWER')
        self.assertEqual(d['selected'],'MODEL_ANSWER');self.assertEqual(d['late'],[('APPROVED_FIXED_RULE','CORRECTION'),('SOURCE_SYSTEM_REPORT','DROP')])
        with self.assertRaises(ValueError):B.decide(['TEACHER'])
    def test_egress_type(self):
        self.assertEqual(B.egress_type('APPROVED_FIXED_RULE'),'EXACT_RENDER');self.assertEqual(B.egress_type('MODEL_ANSWER',clarify=True),'CLARIFY')
        self.assertEqual(B.egress_type('SOURCE_SYSTEM_REPORT',status='ERROR'),'SYSTEM_REPORT');self.assertEqual(B.egress_type('MODEL_ANSWER',status='CANCELLED'),'TEXT_REPORT')
    def test_conflicts(self):
        tr={'tool':'calc','args':{'expression':'48*37'},'result':1776}
        self.assertEqual(B.conflicts('It is 1,776.','FINAL',tr),[]);self.assertEqual(B.conflicts('About 1700.','FINAL',tr),['ANSWER_OMITS_TOOL_RESULT'])
        self.assertEqual(B.conflicts('About 1700.','CANCELLED',tr),[])
        self.assertEqual(B.conflicts("I've saved the note.",'FINAL',pending={'call_id':'x'}),['ANSWER_CLAIMS_PENDING_ACTION_DONE'])
        self.assertEqual(B.conflicts('x','FINAL',egress={'ok':False,'violations':['empty']}),['EGRESS:empty'])

class EgressKindTests(unittest.TestCase):
    """One positive and one negative case for every egress kind the broker emits."""
    def test_every_kind(self):
        ok=lambda k,p,**kw:A.egress(k,p,**kw)['ok']
        bad=lambda k,p,**kw:A.egress(k,p,**kw)['violations']
        self.assertTrue(ok('TEXT_REPORT','Answer.'));self.assertIn('empty',bad('TEXT_REPORT',' '))
        self.assertTrue(ok('EXACT_RENDER','abc',source_text='abc'));self.assertIn('exact_render_differs_from_source',bad('EXACT_RENDER','abc',source_text='abd'))
        self.assertTrue(ok('CLARIFY','Which one?'));self.assertIn('clarify_without_question',bad('CLARIFY','Tell me.'))
        self.assertTrue(ok('SYSTEM_REPORT','[Systembericht] Frist abgelaufen'));self.assertIn('control_characters',bad('SYSTEM_REPORT','a\x01'))
        self.assertTrue(ok('SNAPSHOT','[CURRENT_OUTPUT_SNAPSHOT; STREAMING]\nhal'));self.assertIn('snapshot_without_marker',bad('SNAPSHOT','hal'))
        self.assertTrue(ok('CORRECTION',{'text':'fix','correction_of':3,'reason':'TOOL_RESULT_OMITTED'}))
        self.assertEqual(set(bad('CORRECTION',{'text':'fix'})),{'correction_without_target','correction_without_reason'})
        pv={'call_id':'tool_1','tool':'sandbox_note','status':'PROPOSED','preview':{},'text':'… :tx approve tool_1'}
        self.assertTrue(ok('ACTION_PREVIEW',pv,tools={'sandbox_note'}))
        self.assertEqual(set(bad('ACTION_PREVIEW',dict(pv,status='EXECUTED',text='done'),tools={'calc'})),{'unknown_tool','preview_not_pending','preview_without_approval_command'})
        self.assertTrue(ok('TOOL_CALL',{'tool':'calc','args':{'expression':'1+1'}},tools={'calc'}));self.assertIn('tool_schema',bad('TOOL_CALL','rm -rf /'))
        self.assertIn('unknown_action_type',bad('SHELL','x'))

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off');self.seen=[]
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def turn(self,text,answer):
        def gen(messages,*a,**k):self.seen.append(messages);yield answer
        self.r._route=Mock(return_value=('simple',{'source':'TEST_ROUTE_SEAM'}))
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},generate=gen));self.r.learner.output_delta=Mock(return_value=None)
        self.r.submit(text);until=time.monotonic()+15
        while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
        row=self.r.last_answer();self.assertEqual(row['status'],'FINAL')
        dec=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='OutputBrokerDecision' AND event_id=?",(row['event_id'],))['payload'])
        late=self.r.store.rows("SELECT * FROM messages WHERE event_id=? AND role='broker' ORDER BY id",(row['event_id'],))
        return row,dec,late

class PreviewTests(Base):
    def test_registry_preview_is_a_dry_run(self):
        reg=ToolRegistry(self.r.store);reg.enable('sandbox_note');f=Path(self.tmp.name)/'data/tool_sandbox/todo.txt'
        tx=reg.call('sandbox_note',{'name':'todo','text':'milk'},origin='SYSTEM')
        self.assertEqual(tx['status'],'PROPOSED');self.assertEqual(tx['preview']['effect'],'CREATE');self.assertFalse(f.exists())
        reg.approve(tx['id']);self.assertEqual(f.read_text(),'milk')
        pv=reg.preview('sandbox_note',{'name':'todo','text':'bread'});self.assertEqual((pv['effect'],pv['old_head'],pv['new_head']),('REPLACE','milk','bread'))
        self.assertTrue(pv['undo_available']);self.assertEqual(f.read_text(),'milk')
        self.assertIsNone(reg.preview('sandbox_note',{'name':'todo'}))  # schema violation: no preview
        self.assertEqual(reg.preview('sandbox_note',{'name':'../x','text':'y'})['effect'],'PREVIEW_FAILED')
        self.assertEqual(reg.preview('calc',{'expression':'1+1'})['effect'],'UNKNOWN_NO_DRY_RUN')

class LiveTests(Base):
    def test_note_request_becomes_preview_then_approve_and_undo(self):
        hub(self.r).tools.enable('sandbox_note');f=Path(self.tmp.name)/'data/tool_sandbox/shopping.txt'
        row,dec,late=self.turn('Save a note called shopping: buy milk and bread',"I've saved the note.")
        self.assertFalse(f.exists())
        ans=[m for m in self.seen if 'Proposed action' in json.dumps(m)];self.assertTrue(ans);self.assertIn('Not executed',json.dumps(ans[0]))  # the answering body knows
        self.assertEqual(dec['authority'],'MODEL_ANSWER');self.assertIn('ANSWER_CLAIMS_PENDING_ACTION_DONE',dec['conflicts'])
        self.assertEqual(len(late),1);self.assertIn('[Aktion wartet auf Freigabe] sandbox_note',late[0]['text'])
        call=json.loads(late[0]['metadata'])['tool_call'];self.assertIn(':tx approve '+call,late[0]['text'])
        self.assertEqual(self.r.last_answer()['text'],"I've saved the note.")  # broker rows are not answers
        out=json.loads(Operator(self.r).run(':tx approve '+call));self.assertEqual(out['status'],'EXECUTED');self.assertEqual(f.read_text(),'buy milk and bread')
        Operator(self.r).run(':tx undo '+call);self.assertFalse(f.exists())
        rep=json.loads(Operator(self.r).run(':tx broker'));self.assertEqual(rep['late'],{'ACTION_PREVIEW':1})
    def test_note_without_user_permission_is_not_proposed(self):
        row,dec,late=self.turn('Save a note called shopping: buy milk','I cannot save notes yet.')
        self.assertEqual(late,[]);self.assertEqual(dec['late'],[])
    def test_executed_tool_result_missing_from_answer_gets_a_correction(self):
        g=hub(self.r).tools;g.enable('calc');g._policy=lambda spec,origin,args,confirmed=False:('APPROVED','POLICY',[])
        row,dec,late=self.turn('What is 48 times 37?','It is about 1700.')
        self.assertIn('ANSWER_OMITS_TOOL_RESULT',dec['conflicts']);self.assertEqual(len(late),1);self.assertIn('= 1776',late[0]['text'])
        self.assertEqual(json.loads(late[0]['metadata'])['correction_of'],row['id']);self.assertEqual(row['text'],'It is about 1700.')  # transcript untouched
        self.r.cfg['tool_conflict_policy']='log'
        row,dec,late=self.turn('What is 48 times 38?','About 1800.')
        self.assertIn('ANSWER_OMITS_TOOL_RESULT',dec['conflicts']);self.assertEqual(late,[]);self.assertFalse(dec['late'][0]['applied'])
    def test_exact_copy_is_exact_render(self):
        self.r.submit('Copy exactly: a  b');until=time.monotonic()+10
        while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
        row=self.r.last_answer();dec=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='OutputBrokerDecision' AND event_id=?",(row['event_id'],))['payload'])
        self.assertEqual((dec['authority'],dec['egress_type'],dec['conflicts'],dec['rewrites']),('EXPLICIT_EXACT_COPY','EXACT_RENDER',[],0))
        n=self.r.store.one("SELECT COUNT(*) n FROM packets WHERE kind='EgressCheck' AND event_id=?",(row['event_id'],))['n'];self.assertEqual(n,1)  # one C6 check per output

if __name__=='__main__':unittest.main()
