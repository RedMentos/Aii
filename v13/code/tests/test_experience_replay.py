"""Authority, persistence and failure checks. These are not native model proofs."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from v13.common import digest,Cancelled
from v13.runtime import Runtime
from v13.operator import Operator

class ExperienceReplay(unittest.TestCase):
    def test_dataset_export_is_scoped_and_preserves_explicit_permissions(self):
        from v13.common import file_hash
        e,_,_=self.pair();self.r.memory.select(e['event_id'],self.r.session,'teacher',0,9,permission='learn')
        sid=self.r.session;other=self.r.store.new_session();eid=self.r.store.event(other,'Andere Frage')['event_id'];self.r.store.message(other,eid,'assistant','Andere Antwort','FINAL',{})
        out=self.r.memory.export_dataset(sid);items=[json.loads(line) for line in Path(out['dataset']).read_text().splitlines()]
        self.assertEqual(len(items),1);self.assertEqual(items[0]['event_id'],e['event_id']);self.assertFalse(items[0]['teacher_truth_authority'])
        self.assertEqual(items[0]['decisions'][0]['learning_permission'],'learn');self.assertEqual(file_hash(Path(out['dataset'])),out['sha256'])
        self.assertEqual(self.r.memory.export_dataset()['records'],2)
        self.assertEqual(self.r.store.rows('SELECT * FROM updates'),[])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def pair(self):
        s=self.r.store;e=s.event(self.r.session,'Projekt Aurora Budget?')
        mid=s.message(self.r.session,e['event_id'],'assistant','Unbekannt','FINAL',{})
        text='Korrektur: 120 Euro. Grüße 🍎.';ref=s.source(text,'TEACHER_REFERENCE')
        tid=s.message(self.r.session,e['event_id'],'teacher',text,'FINAL',{'own_answer_hash_before_teacher':digest('Unbekannt'),'reference_source_ref':ref})
        return e,tid,text
    def test_teacher_never_becomes_memory_without_operator_selection(self):
        e,tid,text=self.pair();self.assertEqual(self.r.memory.recall('Projekt Aurora Budget?',self.r.session),[])
        start=text.index('120');end=start+8;before=self.r.store.history(self.r.session)
        mid=self.r.memory.select(e['event_id'],self.r.session,'teacher',start,end)
        found=self.r.memory.recall('Projekt Aurora Budget?',self.r.session);self.assertEqual(found[0]['value'],'120 Euro')
        self.assertEqual(before,self.r.store.history(self.r.session))
        decision=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='HumanDecision'")['payload'])
        self.assertEqual(decision['selection']['message_id'],tid);self.assertEqual(self.r.store.read_source(decision['selection']['source_ref']),'120 Euro')
        self.r.close();self.r=Runtime(self.home);self.assertEqual(self.r.memory.recall('Projekt Aurora Budget?',self.r.session)[0]['id'],mid)
    def test_invalid_cross_session_partial_and_before_self_rejected(self):
        e,tid,text=self.pair()
        for lo,hi in [(-1,3),(0,len(text)+1),(4,2),(1,1)]:
            with self.assertRaises(ValueError):self.r.memory.select(e['event_id'],self.r.session,'teacher',lo,hi)
        with self.assertRaises(ValueError):self.r.memory.select(e['event_id'],self.r.store.new_session(),'teacher')
        with self.r.store.tx() as c:c.execute("UPDATE messages SET status='CANCELLED' WHERE id=?",(tid,))
        with self.assertRaises(ValueError):self.r.memory.select(e['event_id'],self.r.session,'teacher')
        self.assertEqual(self.r.store.rows('SELECT * FROM memories'),[])
    def test_self_selection_and_command_authority(self):
        e,_,_=self.pair();op=Operator(self.r)
        with self.assertRaises(ValueError):op.run(':choose teacher',origin='MODEL_OUTPUT')
        op.run(':choose self 0:9 --kind preference')
        row=self.r.store.one('SELECT * FROM memories');self.assertEqual(row['value'],'Unbekannt');self.assertEqual(row['kind'],'preference')
        with self.assertRaises(ValueError):op.run(':choose teacher --bogus')
        with self.assertRaises(ValueError):op.run(':replay 999')
    def test_replay_missing_model_keeps_queue_and_does_not_add_facts(self):
        e,_,_=self.pair();self.r.memory.feedback(e['event_id'],'fact','120 Euro')
        before=self.r.store.rows('SELECT * FROM memories');history=self.r.store.history(self.r.session);generation=self.r.store.generation()
        with self.assertRaises(RuntimeError):self.r._replay(1)
        self.assertEqual(self.r.store.rows('SELECT * FROM memories'),before)
        self.assertEqual(self.r.store.history(self.r.session),history);self.assertEqual(self.r.store.generation(),generation)
        self.assertEqual(self.r.store.one('SELECT status FROM replay')['status'],'PENDING')
        report=json.loads((self.home/'exports/replay-last.json').read_text());self.assertEqual(report['status'],'REPLAY_INTERRUPTED');self.assertFalse(report['weight_updates'])
    def test_restart_recovers_interrupted_replay_and_cancel_leaves_pending(self):
        e,_,_=self.pair();self.r.memory.feedback(e['event_id'],'fact','120 Euro')
        with self.r.store.tx() as c:c.execute("UPDATE replay SET status='RUNNING'")
        self.r.close();self.r=Runtime(self.home)
        self.assertEqual(self.r.store.one('SELECT status FROM replay')['status'],'PENDING')
        self.r.cancel_event.set()
        with self.assertRaises(Cancelled):self.r._replay(1)
        self.assertEqual(self.r.store.one('SELECT status FROM replay')['status'],'PENDING')
        self.assertFalse(self.r.store.rows("SELECT * FROM packets WHERE kind='ReplayItem'"))


class Step4DatasetView(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def test_step4_lanes_and_fingerprint_are_separate_stable_and_restart_safe(self):
        s=self.r.store;e=s.event(self.r.session,'Projekt Aurora Budget?')
        own='Eigene Antwort';s.message(self.r.session,e['event_id'],'assistant',own,'FINAL',{'model_revision':'self-r1'})
        teacher='Referenz: 120 Euro';ref=s.source(teacher,'TEACHER_REFERENCE')
        s.message(self.r.session,e['event_id'],'teacher',teacher,'FINAL',{'own_answer_hash_before_teacher':digest(own),'reference_source_ref':ref,'reference_only':True,'not_fact':True,'model_revision':'teacher-r1'})
        self.r.memory.select(e['event_id'],self.r.session,'teacher',10,len(teacher))
        a=self.r.memory.experience(e['event_id'],self.r.session)
        self.assertEqual(a['schema'],'V13_STEP4_EXPERIENCE_V1');self.assertFalse(a['teacher_truth_authority'])
        self.assertEqual(a['lanes']['self'][0]['text'],own);self.assertEqual(a['lanes']['reference'][0]['text'],teacher)
        self.assertTrue(a['lanes']['reference'][0]['metadata']['reference_only']);self.assertEqual(len(a['decisions']),1)
        fp=a['fingerprint_sha256'];self.assertEqual(fp,self.r.memory.experience(e['event_id'],self.r.session)['fingerprint_sha256'])
        session=self.r.session;self.r.close();self.r=Runtime(self.home)
        b=self.r.memory.experience(e['event_id'],session);self.assertEqual(fp,b['fingerprint_sha256'])
        self.assertFalse(b['teacher_truth_authority']);self.assertEqual(b['decisions'][0]['selection']['lane'],'teacher')
    def test_step4_fingerprint_with_selection_is_equal_across_homes(self):
        def flow(r):
            s=r.store;e=s.event(r.session,'Projekt Aurora Budget?')
            own='Eigene Antwort';s.message(r.session,e['event_id'],'assistant',own,'FINAL',{'model_revision':'self-r1'})
            teacher='Referenz: 120 Euro';ref=s.source(teacher,'TEACHER_REFERENCE')
            s.message(r.session,e['event_id'],'teacher',teacher,'FINAL',{'own_answer_hash_before_teacher':digest(own),'reference_source_ref':ref,'reference_only':True,'not_fact':True,'model_revision':'teacher-r1'})
            r.memory.select(e['event_id'],r.session,'teacher',None,None,'fact','record')
            r.memory.select(e['event_id'],r.session,'self',None,None,'preference','record')
            return r.memory.experience(e['event_id'],r.session)
        with tempfile.TemporaryDirectory() as other:
            r2=Runtime(Path(other))
            try:
                s2=r2.store;s2.source('verschiebt Zeilen-IDs','USER')  # different row history in the second home
                b=flow(r2)
            finally:r2.close()
        a=flow(self.r)
        self.assertNotEqual(a['decisions'][0]['selection']['source_ref']['source_id'],b['decisions'][0]['selection']['source_ref']['source_id'])
        self.assertEqual(a['fingerprint_sha256'],b['fingerprint_sha256'])


if __name__=='__main__':unittest.main()
