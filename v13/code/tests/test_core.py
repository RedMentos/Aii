import io
import json
from pathlib import Path
import tarfile
import tempfile
import threading
import time
import unittest
from v13.common import atomic_write,dumps,digest,file_hash,uid,now
from v13.config import initialize,save_config
from v13.store import Store,SCHEMA_VERSION
from v13.contracts import packet,offer_is_fresh
from v13.memory import Memory
from v13.runtime import Runtime
from v13.operator import Operator
from v13.backup import backup,restore,unpack_verified

class Core(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.cfg=initialize(self.home);self.s=Store(self.home);self.sid=self.s.new_session()
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def event(self,text='Projekt Aurora Budget?'):return self.s.event(self.sid,text)
    def test_boot_generation_snapshot_is_atomic_and_idempotent(self):
        placeholder=self.s.generation_id;models={"C2_CONTROL":"needle-rev","C3_LANGUAGE":"language-rev"}
        snap=self.s.ensure_generation_snapshot(self.cfg,models);manifest=self.s.generation()
        self.assertNotEqual(snap,placeholder);self.assertEqual(manifest["parent_generation_id"],placeholder)
        self.assertEqual(manifest["config"],self.cfg);self.assertEqual(manifest["models"],models)
        self.assertEqual(self.s.ensure_generation_snapshot(self.cfg|{"threads":2},{"C2_CONTROL":"changed"}),snap)
        self.assertEqual(self.s.generation()["models"],models)

    def test_unicode_source_and_tamper(self):
        ref=self.s.source('Grüße 🍎!');self.assertEqual(self.s.read_source(ref|{'char_start':6,'char_end':7}),'🍎')
        atomic_write(self.home/'data/blobs'/ref['sha256'],'falsch')
        with self.assertRaises(ValueError):self.s.read_source(ref)
    def test_invalid_span_and_dangling(self):
        ref=self.s.source('abc')
        for bad in [ref|{'char_end':4},ref|{'source_id':'missing'}]:
            with self.assertRaises(ValueError):self.s.read_source(bad)
    def test_exclusive_writer(self):
        with self.assertRaises(RuntimeError):Store(self.home)
    def test_no_provisional_events(self):
        with self.assertRaises(ValueError):self.s.event(self.sid,'hypothesis','PROVISIONAL')
    def test_final_immutable_and_partial_restart(self):
        e=self.event();mid=self.s.message(self.sid,e['event_id'],'assistant');self.s.append_message(mid,'abc');self.s.close();self.s=Store(self.home)
        self.assertEqual(self.s.one('SELECT status FROM messages WHERE id=?',(mid,))['status'],'INTERRUPTED')
        with self.assertRaises(ValueError):self.s.append_message(mid,'changed')
    def test_offer_stale_generation_and_commit(self):
        e=self.event();p=packet('OfferPacket','B1_DETAIL',e['event_id'],e['brain_generation_id'],role='B1_DETAIL',based_on_state_version=2,deadline_monotonic_ns=time.monotonic_ns()+10**9,evidence_refs=[],offer={},confidence=0.)
        self.assertTrue(offer_is_fresh(p,e['event_id'],e['brain_generation_id'],2));self.assertFalse(offer_is_fresh(p,e['event_id'],'other',2));self.assertFalse(offer_is_fresh(p,e['event_id'],e['brain_generation_id'],2,True))
    def test_source_memory_restart_and_scope(self):
        e=self.event();m=Memory(self.s,self.cfg);m.feedback(e['event_id'],'fact','120 Euro');self.s.close();self.s=Store(self.home);m=Memory(self.s,self.cfg)
        self.assertEqual(m.recall('Budget Projekt Aurora',self.sid)[0]['value'],'120 Euro');self.assertEqual(m.recall('Budget Projekt Borealis',self.sid),[]);self.assertEqual(m.recall('Budget Projekt Aurora',self.s.new_session()),[])
    def test_feedback_supersedes_same_key_only(self):
        e=self.event();m=Memory(self.s,self.cfg);m.feedback(e['event_id'],'fact','100');m.feedback(e['event_id'],'fact','120');m.feedback(e['event_id'],'style','kurz')
        active=self.s.rows('SELECT * FROM memories WHERE active=1');self.assertEqual(len(active),2);self.assertNotIn('100',[r['value'] for r in active])
    def test_forget_source_and_packets(self):
        e=self.event();m=Memory(self.s,self.cfg);mid=m.feedback(e['event_id'],'fact','120');r=self.s.one('SELECT source_id FROM memories WHERE id=?',(mid,));m.forget(mid)
        self.assertEqual(m.recall('Projekt Aurora Budget',self.sid),[]);self.assertFalse(self.s.one('SELECT id FROM feedback WHERE source_id=?',(r['source_id'],)));self.assertEqual(self.s.integrity(True),[])
    def test_corollary_precedes_dispatch(self):
        e=self.event();aid=self.s.start_action(e['event_id'],e['brain_generation_id']);a=self.s.one('SELECT * FROM actions WHERE id=?',(aid,));p=self.s.one('SELECT * FROM packets WHERE id=?',(a['corollary_id'],));self.assertLessEqual(p['created'],a['created'])
    def candidate(self):
        id_=uid('upd');path='checkpoints/head-'+id_+'.npz';atomic_write(self.home/path,b'test-artifact');h=file_hash(self.home/path)
        with self.s.tx() as c:c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)',(id_,self.s.generation_id,'PENDING_APPROVAL',path,h,dumps({'commit_eligible':True}),now()))
        return id_,path
    def test_commit_rule_change_rollback_retains_rules(self):
        before=self.s.generation();id_,path=self.candidate();self.s.switch_generation(id_,self.cfg,{})
        rid=self.s.request('RULES',{'base_rule':self.s.generation()['rule_version'],'after':['kurz']});self.s.approve_rule(rid,self.cfg,{})
        self.s.rollback(id_);self.assertEqual(self.s.generation()['hashes'],before['hashes']);self.assertEqual(self.s.rules(),['kurz'])
    def test_corrupt_candidate_never_activated(self):
        id_,path=self.candidate();before=self.s.generation_id;atomic_write(self.home/path,b'bad')
        with self.assertRaises(RuntimeError):self.s.switch_generation(id_,self.cfg,{})
        self.assertEqual(self.s.generation_id,before)
    def test_backup_restore_roundtrip(self):
        self.event('Original');snap=backup(self.s);self.event('Später');self.s.close();restore(self.home,snap);self.s=Store(self.home)
        rows=self.s.history(self.sid);self.assertEqual([r['text'] for r in rows],['Original']);self.assertEqual(self.s.integrity(True),[])
    def test_restore_rejects_traversal(self):
        path=self.home/'evil.tar.gz'
        with tarfile.open(path,'w:gz') as t:
            x=tarfile.TarInfo('../escape');x.size=1;t.addfile(x,io.BytesIO(b'x'))
        stage=self.home/'tmp/stage';stage.mkdir()
        with self.assertRaises(ValueError):unpack_verified(path,stage,10000)

class RuntimeChecks(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home);self.r.cfg['observer_mode']='off';self.op=Operator(self.r)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def wait(self):
        until=time.monotonic()+5
        while not self.r.idle() and time.monotonic()<until:time.sleep(.02)
        self.assertTrue(self.r.idle())
    def test_model_text_cannot_execute(self):
        self.op.run('Kopiere exakt: :shutdown');self.wait();self.assertEqual(self.r.last_answer()['text'],':shutdown');self.assertFalse(self.r.stop.is_set())
        with self.assertRaises(ValueError):self.op.run(':shutdown',origin='MODEL_OUTPUT')
    def test_missing_models_show_diagnostic(self):
        self.r.submit('Hallo');self.wait();m=self.r.last_answer();self.assertEqual(m['status'],'ERROR');self.assertIn('Systemdiagnose',m['text']);self.assertFalse(json.loads(m['metadata'])['model_generated'])
    def test_record_mode_has_no_weight_changes(self):
        before=self.r.store.generation_id
        with self.assertRaises(ValueError):self.r.learner.shadow()
        self.assertEqual(list((self.home/'checkpoints').iterdir()),[]);self.assertEqual(before,self.r.store.generation_id)
    def test_pause_resume_queue_and_age(self):
        self.r.pause();self.r.submit('Kopiere exakt: ok');time.sleep(.15);self.assertEqual(self.r.jobs.qsize(),1);self.r.resume();self.wait();self.assertEqual(self.r.last_answer()['text'],'ok');self.op.run(':stage cap 5');self.assertEqual(self.r.cfg['system_stage'],0)
    def test_rule_diff_requires_exact_approval(self):
        result=self.op.run(':rules add kurz');self.assertEqual(self.r.store.rules(),[]);self.op.run(':approve '+result.split(';')[0]);self.assertEqual(self.r.store.rules(),['kurz'])
    def test_queue_input_bounds_and_config_validation(self):
        self.r.pause();self.r.cfg['input_bytes']=5
        with self.assertRaises(RuntimeError):self.r.submit('too long')
        self.assertEqual(self.r.store.history(self.r.session),[])
        with self.assertRaises(ValueError):self.op.run(':budget threads 0')
        self.assertEqual(self.r.cfg['threads'],4)
    def test_no_unknown_rejection_success(self):
        with self.assertRaises(ValueError):self.op.run(':reject missing')
    def test_schema_registry_exposed(self):
        schemas=json.loads(self.op.run(':schemas'));self.assertIn('OfferPacket',schemas);self.assertEqual(schemas['OfferPacket']['schema_version'],'1.0')
        ledger=json.loads(self.op.run(':ledger'));ids={x['feature_id'] for x in ledger['rows']};self.assertIn('STEP0_SCHEMA_REGISTRY',ids);self.assertIn('B3_LATENT',ids)
        self.assertTrue((self.home/'exports/schema-registry.json').is_file());self.assertTrue((self.home/'exports/completion-ledger.json').is_file())
    def test_database_version_and_telemetry_bound(self):
        self.assertEqual(self.r.store.db.execute('PRAGMA user_version').fetchone()[0],SCHEMA_VERSION)
        for i in range(10250): self.r.store.log('bound_test',None,{'i':i})
        n=self.r.store.db.execute('SELECT COUNT(*) FROM telemetry').fetchone()[0]
        self.assertLessEqual(n,10200)
        from v13.verification import write_build_artifacts
        a=write_build_artifacts(self.r);self.assertTrue(Path(a['logging_policy']).is_file());self.assertTrue(Path(a['open_questions']).is_file())
        self.assertIn('Redmi',Path(a['open_questions']).read_text().split('## RESEARCH_NEEDED')[0])  # WP-V8: real operator tasks listed
    def test_runner_log_rotation_policy(self):
        from v13.runners import rotate_log
        p=self.home/'logs/test.log';p.write_bytes(b'x'*1025);rotate_log(p,cap=1024)
        self.assertFalse(p.exists());self.assertTrue((self.home/'logs/test.previous.log').is_file())

class Gradient(unittest.TestCase):
    def test_analytic_gradient_and_repeatability(self):
        try:import numpy as np
        except ImportError:self.skipTest('NumPy not installed')
        from v13.learning_worker import features,gradient_check,optimize,objective
        rng=np.random.default_rng(13);x=features(rng.normal(size=(12,16)));y=np.arange(12)%4;w=np.zeros((17,4));trace=np.zeros(17)
        self.assertLess(gradient_check(x,y,w),1e-6)
        with tempfile.TemporaryDirectory() as d:cfg=initialize(Path(d))
        a,_=optimize(x,y,w,trace,cfg);b,_=optimize(x,y,w,trace,cfg);self.assertTrue(np.array_equal(a,b));self.assertLess(objective(x,y,a)[0],objective(x,y,w)[0])
if __name__=='__main__':unittest.main()
