import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from v13.common import atomic_write,Cancelled,Limits,dumps
from v13.config import initialize
from v13.consolidation import Consolidation
from v13.memory import Memory
from v13.store import Store
from v13.backup import backup,restore

class ConsolidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.cfg=initialize(self.home);self.cfg['learning_mode']='SHADOW_UPDATE'
        self.s=Store(self.home);self.session=self.s.new_session();self.m=Memory(self.s,self.cfg);self.c=Consolidation(self.s,self.cfg,self.m)
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def confirmations(self,kind='fact',value='400 Euro',permission='learn',keys=None,scope='session'):
        ids=[]
        for i,key in enumerate(keys or ['Projekt Liora Budget','Projekt Liora Finanzrahmen','Projekt Liora verfügbare Mittel']):
            e=self.s.event(self.session,key+' bitte '+str(i));ids.append(self.m.feedback(e['event_id'],kind,value,permission,key=key,scope=scope))
        return ids
    def activate(self,component='semantic'):
        rid=self.c.stage(self.session,component)['requests'][0];self.cfg['learning_mode']='APPROVED_COMMIT';cid=self.c.approve(rid);return rid,cid
    def test_stage_is_reviewable_no_activation_and_record_mode_refused(self):
        self.confirmations();rid=self.c.stage(self.session)['requests'][0];request=json.loads(self.s.one('SELECT payload FROM requests WHERE id=?',(rid,))['payload'])
        self.assertEqual(request['members'],3);self.assertEqual(request['value'],'400 Euro');self.assertEqual(len(request['source_ids']),9);self.assertEqual(self.c.active(self.session),[])
        self.assertEqual(self.c.stage(self.session)['requests'],[])
        self.cfg['learning_mode']='RECORD_ONLY'
        with self.assertRaises(ValueError):self.c.stage(self.session)
        with self.assertRaises(ValueError):self.c.approve(rid)
    def test_only_independent_explicit_human_confirmations(self):
        self.confirmations(permission='record');self.assertEqual(self.c.stage(self.session)['requests'],[])
        for _ in range(3):
            e=self.s.event(self.session,'Identical query');self.m.feedback(e['event_id'],'fact','20 Euro','learn',key='Projekt Same Budget')
        self.assertEqual(self.c.stage(self.session)['requests'],[])
        # Real dream/reference source records, absent a HumanDecision, confer no authority.
        self.s.source('400 Euro','REPLAY_HYPOTHESIS');self.s.source('400 Euro','TEACHER_REFERENCE');self.assertEqual(self.c.stage(self.session)['requests'],[])
    def test_compaction_preserves_source_value_and_other_memory(self):
        members=self.confirmations();rid,cid=self.activate();query='Projekt Liora Budget Finanzrahmen verfügbare Mittel'
        ordinary=self.m.recall(query,self.session);merged=self.c.merge(query,self.session,ordinary)
        self.assertEqual(len(ordinary),3);self.assertEqual(len(merged),1);self.assertEqual(merged[0]['id'],cid);self.assertEqual(merged[0]['value'],'400 Euro')
        self.assertEqual(set(merged[0]['consolidation']['members']),set(members));self.assertEqual(len(merged[0]['consolidation']['source_refs']),9)
        self.assertEqual(self.c.merge('Projekt Andere Budget',self.session,[]),[])
        self.assertEqual(self.c.merge(query,self.s.new_session(),[]),[])
        self.assertEqual(self.m.report_context(query,merged)[0]['correction'],'400 Euro')
    def test_changed_correction_and_permission_fail_closed(self):
        self.confirmations();self.activate();e=self.s.event(self.session,'Budget prüfen')
        self.m.feedback(e['event_id'],'fact','500 Euro','learn',key='Projekt Liora Budget');self.assertEqual(self.c.active(self.session),[])
        # Equal value with record-only authority cannot silently retain old permission.
        self.m.feedback(e['event_id'],'fact','400 Euro','record',key='Projekt Liora Budget');self.assertEqual(self.c.active(self.session),[])
    def test_tamper_and_pending_conflict_never_activate(self):
        self.confirmations();rid=self.c.stage(self.session)['requests'][0];p=json.loads(self.s.one('SELECT payload FROM requests WHERE id=?',(rid,))['payload'])
        atomic_write(self.home/p['path'],'{}');self.cfg['learning_mode']='APPROVED_COMMIT'
        with self.assertRaises(ValueError):self.c.approve(rid)
        self.assertEqual(self.c.active(self.session),[])
    def test_deleted_member_invalidates_index_without_false_unlearning(self):
        ids=self.confirmations();self.activate();self.m.forget(ids[0]);self.assertEqual(self.c.active(self.session),[]);self.assertEqual(self.s.integrity(True),[])
    def test_restart_rollback_preserves_original_memories(self):
        ids=self.confirmations();rid,cid=self.activate();self.s.close();self.s=Store(self.home);self.m=Memory(self.s,self.cfg);self.c=Consolidation(self.s,self.cfg,self.m)
        self.assertEqual(self.c.active(self.session)[0]['index_id'],cid);self.c.rollback(rid);self.assertEqual(self.c.active(self.session),[])
        self.assertEqual(len(self.s.rows('SELECT * FROM memories WHERE active=1')),3)
        with self.assertRaises(ValueError):self.c.rollback(cid)
        self.assertEqual(self.s.integrity(True),[])
    def test_backup_restore_exact_index_and_lineage(self):
        self.confirmations();rid,cid=self.activate();snap=backup(self.s);self.c.rollback(cid);self.s.close();restore(self.home,snap)
        self.s=Store(self.home);self.m=Memory(self.s,self.cfg);self.c=Consolidation(self.s,self.cfg,self.m);self.assertEqual(self.c.active(self.session)[0]['index_id'],cid)
    def test_procedure_only_exact_human_cues(self):
        keys=['Projekt Liora Rechnung prüfen','Projekt Liora Kosten berechnen','Projekt Liora Betrag kontrollieren'];self.confirmations('route','detail',keys=keys);rid,cid=self.activate('procedural')
        actual=keys[1]+' bitte 1';decision=self.c.route(actual,self.session);self.assertEqual(decision['route'],'detail');self.assertEqual(decision['index_id'],cid)
        self.assertEqual(self.c.route('Projekt Liora Kosten schätzen',self.session),None);self.assertEqual(self.c.route(actual,self.s.new_session()),None)
        self.assertEqual(self.c.merge(actual,self.session,[]),[])
    def test_different_entities_never_pool_confirmations(self):
        self.confirmations(keys=['Projekt A Budget','Projekt B Budget','Projekt C Budget']);self.assertEqual(self.c.stage(self.session)['requests'],[])
    def test_active_artifact_tamper_and_approval_deletion_fail_closed(self):
        self.confirmations();rid,cid=self.activate();state,_=self.s.state('CONSOLIDATION:'+cid)
        with self.s.tx() as db:db.execute('DELETE FROM packets WHERE id=?',(state['approval_packet_id'],))
        self.assertEqual(self.c.active(self.session),[])
    def test_ordinary_semantic_policy_is_not_swallowed(self):
        self.confirmations();self.activate();ordinary=self.m.recall('Projekt Liora Budget',self.session);ordinary[0]['retrieval_policy']={'decision':'admit','in_support':True}
        merged=self.c.merge('Projekt Liora Budget',self.session,ordinary);self.assertEqual(merged,ordinary)
    def test_explicit_selection_retains_original_reference_lineage(self):
        ids=[];reference=self.s.source('Reference: 400 Euro','SELF_CANDIDATE');selection_ref=reference|{'char_start':11,'char_end':19}
        for i,key in enumerate(['Projekt Liora Budget','Projekt Liora Finanzrahmen','Projekt Liora verfügbare Mittel']):
            event=self.s.event(self.session,key+' '+str(i));ids.append(self.m.feedback(event['event_id'],'fact','400 Euro','learn',key=key,selection={'source_ref':selection_ref,'lane':'self'}))
        rid,cid=self.activate();index=self.c.active(self.session)[0];self.assertIn(reference['source_id'],index['source_ids'])
        selected=self.c.merge('Projekt Liora Budget',self.session,self.m.recall('Projekt Liora Budget',self.session));self.assertIn(selection_ref,self.c.source_refs(selected))
        with self.s.tx() as db:db.execute('UPDATE sources SET deleted=1 WHERE id=?',(reference['source_id'],))
        self.assertEqual(self.c.active(self.session),[])
    def test_memory_recall_learned_rejections_cannot_be_resurrected(self):
        self.confirmations();self.activate();self.m.consolidation=self.c
        query='Projekt Liora Budget Finanzrahmen verfügbare Mittel';calls=[]
        def rejected(memory):calls.append(memory['id']);return {'decision':'reject','probability':.01,'in_support':True}
        self.assertEqual(self.m.recall(query,self.session,rejected),[]);self.assertEqual(len(calls),3)
        admitted=lambda memory:{'decision':'admit','probability':.99,'in_support':True}
        rows=self.m.recall(query,self.session,admitted);self.assertEqual(len(rows),3);self.assertTrue(all(r['retrieval_policy']['decision']=='admit' for r in rows))
    def test_global_conflict_across_sessions_revokes_index_and_memory(self):
        ids=self.confirmations(scope='global');rid,cid=self.activate();other=self.s.new_session();event=self.s.event(other,'Budget neu')
        new=self.m.feedback(event['event_id'],'fact','500 Euro','learn',key='Projekt Liora Budget',scope='global')
        self.assertEqual(self.c.active(self.session),[]);self.assertEqual(self.c.active(other),[])
        rows=self.m.recall('Projekt Liora Budget',self.session);self.assertEqual([m['value'] for m in rows],['500 Euro']);self.assertEqual(rows[0]['id'],new)
        self.assertEqual(self.s.one('SELECT active FROM memories WHERE id=?',(ids[0],))['active'],0)
    def test_global_samevalue_record_only_revokes_across_sessions(self):
        self.confirmations(scope='global');self.activate();other=self.s.new_session();event=self.s.event(other,'Budget nochmal')
        self.m.feedback(event['event_id'],'fact','400 Euro','record',key='Projekt Liora Budget',scope='global')
        self.assertEqual(self.c.active(self.session),[]);self.assertEqual(self.c.active(other),[])
    def test_local_override_only_suppresses_global_index_in_its_session(self):
        self.confirmations(scope='global');self.activate();self.m.consolidation=self.c;original=self.session;other=self.s.new_session();event=self.s.event(other,'Lokales Budget')
        local=self.m.feedback(event['event_id'],'fact','500 Euro','learn',key='Projekt Liora Budget',scope='session')
        self.assertEqual(len(self.c.active(original)),1);self.assertEqual(self.c.active(other),[])
        self.assertEqual([m['value'] for m in self.m.recall('Projekt Liora Budget',other)],['500 Euro'])
        self.assertEqual(self.m.recall('Projekt Liora Budget',other)[0]['id'],local)
        self.assertEqual(self.m.recall('Projekt Liora Budget',original)[0]['value'],'400 Euro')
    def test_local_record_only_samevalue_does_not_revoke_other_session(self):
        self.confirmations(scope='global');self.activate();other=self.s.new_session();event=self.s.event(other,'Budget lokal notieren')
        self.m.feedback(event['event_id'],'fact','400 Euro','record',key='Projekt Liora Budget',scope='session')
        self.assertEqual(len(self.c.active(self.session)),1);self.assertEqual(self.c.active(other),[])
    def test_staging_record_overflow_refuses_without_sampling_or_writes(self):
        for i in range(513):
            event=self.s.event(self.session,'Record '+str(i));self.m.feedback(event['event_id'],'fact','Value '+str(i),'learn',key='Key '+str(i))
        with self.assertRaises(Limits):self.c.stage(self.session)
        self.assertEqual(self.s.rows("SELECT id FROM requests WHERE kind='CONSOLIDATION'"),[]);self.assertEqual(list((self.home/'checkpoints').glob('consolidation-*')),[])
    def test_request_and_active_index_overflow_fail_closed(self):
        ordinary=[{'id':'ordinary'}]
        for i in range(65):
            self.s.request('CONSOLIDATION',{'evidence_signature':str(i)})
            self.s.set_state('CONSOLIDATION:fixture'+str(i),{'status':'APPROVED','members':3})
        with self.assertRaises(Limits):self.c.stage(self.session)
        self.assertEqual(self.c.active(self.session),[]);self.assertEqual(self.c.merge('query',self.session,ordinary),ordinary)
        self.assertEqual(self.c.route('query',self.session),None)
        self.assertTrue(self.s.one("SELECT id FROM telemetry WHERE kind='consolidation_work_limit'"))
    def test_active_source_record_overflow_fail_closed(self):
        for i in range(3):self.s.set_state('CONSOLIDATION:fixture'+str(i),{'status':'APPROVED','members':200})
        self.assertEqual(self.c.active(self.session),[])
    def test_approval_cannot_disable_existing_indexes_by_exceeding_record_cap(self):
        self.confirmations();rid=self.c.stage(self.session)['requests'][0]
        for i in range(2):self.s.set_state('CONSOLIDATION:fixture'+str(i),{'status':'APPROVED','members':256})
        self.cfg['learning_mode']='APPROVED_COMMIT'
        with self.assertRaises(Limits):self.c.approve(rid)
        self.assertEqual(self.s.one('SELECT status FROM requests WHERE id=?',(rid,))['status'],'PENDING')
    def test_cancellation_and_deadline_checked_before_and_during_work(self):
        stopped=threading.Event();stopped.set()
        for fn in (lambda:self.c.stage(self.session,cancel=stopped),lambda:self.c.active(self.session,cancel=stopped),lambda:self.c.route('query',self.session,cancel=stopped),lambda:self.c.merge('query',self.session,[],cancel=stopped)):
            with self.assertRaises(Cancelled):fn()
        with self.assertRaises(Limits):self.c.active(self.session,deadline=time.monotonic()-1)
        self.confirmations();calls=[0];original=self.c._member
        def stop_during(member,cancel=None,deadline=None):
            calls[0]+=1;stopped.set();return original(member,stopped,deadline)
        stopped.clear();self.c._member=stop_during
        with self.assertRaises(Cancelled):self.c.stage(self.session,cancel=stopped)
        self.assertEqual(self.s.rows("SELECT id FROM requests WHERE kind='CONSOLIDATION'"),[])

if __name__=='__main__':unittest.main()
