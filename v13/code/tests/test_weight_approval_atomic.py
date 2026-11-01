"""Manual AG6 approval atomicity with real SQLite, authored adapter bytes only.

No model training or deployed learning quality is claimed by these tests.
"""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

from v13.common import file_hash
from v13.runtime import Runtime
from v13.agi.weights import WeightConsolidation,KEY,_ApprovalStore
from v13.lora_trainer import AdapterRegistry,REGISTRY_KEY,MIRROR,runner_lora_args
from tests.test_lora_trainer import FakeLora


class Interrupted(BaseException):pass


class ApprovalAtomicity(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name)
        self.r=Runtime(self.home);self.r.sleep.cycle.set_policy('enabled','off');self.s=self.r.store
        self.model=self.home/'model.gguf';self.model.write_bytes(b'authored model fixture')
        e=self.s.event(self.r.session,'What is the project name?')
        self.r.memory.feedback(e['event_id'],'fact','Mira')
        self.cfg=self.r.cfg|{'learning_mode':'SHADOW_UPDATE'}
        self.w=WeightConsolidation(self.s,self.cfg,trainer=FakeLora(self.home,self.model,cand={'overall':.8,'unseen':.75,'forgetting':{'rate':0.}}))
        self.bid=self.w.stage(require_replay_pass=False)['batch_id']
        b=self.w.train_and_gate(self.bid);self.rid=b['request_id'];self.adapter=Path(b['trainer']['artifact'])
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def restart(self):
        self.r.close();self.r=Runtime(self.home);self.r.sleep.cycle.set_policy('enabled','off');self.s=self.r.store
        self.w=WeightConsolidation(self.s,self.cfg)
    def assert_pending(self):
        self.assertEqual(self.w.batch(self.bid)['status'],'PENDING_USER')
        self.assertEqual(self.s.one('SELECT status FROM requests WHERE id=?',(self.rid,))['status'],'PENDING')
        self.assertEqual(self.s.state(KEY)[0]['consolidated'],[])
        self.assertEqual(len(self.w.candidates(require_replay_pass=False)),1)
        self.assertNotIn('C3_LANGUAGE',AdapterRegistry(self.s).report()['active'])
        self.assertEqual(runner_lora_args(self.home,'C3_LANGUAGE',self.model),[])
    def test_missing_adapter_remains_pending_after_sqlite_restart_and_is_retryable(self):
        original=self.adapter.read_bytes();self.adapter.unlink()
        with mock.patch.object(self.w,'_neuromod') as signal:
            with self.assertRaisesRegex(ValueError,'Adapter-Datei'):self.w.approve(self.bid)
            signal.assert_not_called()
        self.assert_pending();self.restart();self.assert_pending()
        self.assertEqual(self.w.stage(require_replay_pass=False)['status'],'PENDING_USER')
        self.adapter.write_bytes(original);self.assertEqual(self.w.approve(self.bid)['status'],'APPROVED')
    def test_tampered_adapter_remains_pending_after_restart(self):
        self.adapter.write_bytes(b'tampered')
        with self.assertRaises(ValueError):self.w.approve(self.bid)
        self.assert_pending();self.restart();self.assert_pending()
    def test_activation_exception_after_registry_write_rolls_back_every_sqlite_effect(self):
        activate=AdapterRegistry.activate
        def fail(reg,*args,**kwargs):activate(reg,*args,**kwargs);raise OSError('fixture failure after registry save')
        with mock.patch.object(AdapterRegistry,'activate',fail),mock.patch.object(self.w,'_neuromod') as signal:
            with self.assertRaises(OSError):self.w.approve(self.bid)
            signal.assert_not_called()
        self.assert_pending();self.restart();self.assert_pending()
    def test_success_is_persistent_and_only_then_signals_positive_neuromod(self):
        with mock.patch.object(self.w,'_neuromod') as signal:
            self.assertEqual(self.w.approve(self.bid)['status'],'APPROVED')
            signal.assert_called_once_with('signal',self.bid,source_class='human_correction',human_correction=1.,evidence_gain=1.)
        self.restart()
        self.assertEqual(self.w.batch(self.bid)['status'],'APPROVED')
        self.assertEqual(self.s.one('SELECT status FROM requests WHERE id=?',(self.rid,))['status'],'APPROVED')
        self.assertEqual(len(self.s.state(KEY)[0]['consolidated']),1)
        self.assertEqual(AdapterRegistry(self.s).report()['active']['C3_LANGUAGE']['batch_id'],self.bid)
        self.assertEqual(runner_lora_args(self.home,'C3_LANGUAGE',self.model)[1],str(self.adapter))
        self.assertEqual(self.w.stage(require_replay_pass=False)['status'],'NOTHING_TO_STAGE')
    def test_legacy_authored_trainer_without_deployed_binding_keeps_approval_behavior(self):
        self.w.box.mutate(lambda st:st['batches'][self.bid]['trainer']['metrics'].pop('deployed'))
        self.adapter.unlink()
        self.assertEqual(self.w.approve(self.bid)['status'],'APPROVED')
        self.assertNotIn('C3_LANGUAGE',AdapterRegistry(self.s).report()['active'])
    def test_sqlite_trigger_failure_after_mirror_publish_restores_previous_binding(self):
        previous=self.home/'previous.gguf';previous.write_bytes(b'previous')
        AdapterRegistry(self.s).activate('C3_LANGUAGE',previous,file_hash(previous),file_hash(self.model),'previous-batch')
        old=AdapterRegistry(self.s).report();old_mirror=(self.home/MIRROR).read_bytes()
        with self.s.tx() as c:
            c.execute("CREATE TRIGGER approval_fixture_fail BEFORE UPDATE OF status ON requests WHEN NEW.status='APPROVED' BEGIN SELECT RAISE(ABORT,'fixture persistence failure'); END")
        with self.assertRaisesRegex(Exception,'fixture persistence failure'):self.w.approve(self.bid)
        self.assertEqual(self.w.batch(self.bid)['status'],'PENDING_USER')
        self.assertEqual(AdapterRegistry(self.s).report(),old)
        self.assertEqual((self.home/MIRROR).read_bytes(),old_mirror)
        self.restart();self.assertEqual(AdapterRegistry(self.s).report(),old)
        with self.s.tx() as c:c.execute('DROP TRIGGER approval_fixture_fail')
        self.assertEqual(self.w.approve(self.bid)['status'],'APPROVED')
        self.w.rollback(self.bid)
        self.assertEqual(runner_lora_args(self.home,'C3_LANGUAGE',self.model)[1],str(previous))
    def test_cas_failure_does_not_retry_activation_or_leak_side_effects(self):
        save=_ApprovalStore.set_state;calls=[]
        def stale(proxy,key,payload,expected=None):
            if key==KEY and payload['batches'][self.bid]['status']=='APPROVED':
                calls.append(1);raise ValueError('Stale state write fixture')
            return save(proxy,key,payload,expected)
        with mock.patch.object(_ApprovalStore,'set_state',stale),mock.patch.object(AdapterRegistry,'activate',autospec=True,wraps=AdapterRegistry.activate) as activate:
            # A real registry call is covered above; this isolates no optimistic callback retry.
            with self.assertRaisesRegex(ValueError,'Stale state'):self.w.approve(self.bid)
            self.assertEqual(activate.call_count,1)
        self.assertEqual(calls,[1]);self.assert_pending();self.restart();self.assert_pending()
    def test_request_missing_fails_without_consolidating(self):
        with self.s.tx() as c:c.execute('DELETE FROM requests WHERE id=?',(self.rid,))
        with self.assertRaisesRegex(ValueError,'Keine offene'):self.w.approve(self.bid)
        self.assertEqual(self.w.batch(self.bid)['status'],'PENDING_USER')
        self.assertEqual(self.s.state(KEY)[0]['consolidated'],[])
        self.assertEqual(runner_lora_args(self.home,'C3_LANGUAGE',self.model),[])
    def test_mirror_publish_failure_keeps_pending_and_retryable(self):
        publish=self.w._publish_adapter_mirror;calls=[]
        def fail_once(registry):
            calls.append(1)
            if len(calls)==1:raise OSError('fixture mirror failure')
            return publish(registry)
        with mock.patch.object(self.w,'_publish_adapter_mirror',fail_once):
            with self.assertRaises(OSError):self.w.approve(self.bid)
        self.assert_pending();self.restart();self.assert_pending()
    def test_interruption_after_mirror_before_commit_is_recovered_on_restart(self):
        publish=self.w._publish_adapter_mirror
        def interrupt(registry):publish(registry);raise Interrupted()
        with mock.patch.object(self.w,'_publish_adapter_mirror',interrupt),mock.patch.object(self.w,'_neuromod') as signal:
            with self.assertRaises(Interrupted):self.w.approve(self.bid)
            signal.assert_not_called()
        self.assertEqual(self.w.batch(self.bid)['status'],'ACTIVATING')
        self.assertEqual(self.s.one('SELECT status FROM requests WHERE id=?',(self.rid,))['status'],'PENDING')
        self.assertEqual(self.s.state(KEY)[0]['consolidated'],[])
        self.assertNotIn('C3_LANGUAGE',AdapterRegistry(self.s).report()['active'])
        # SQLite rolled back, but the interrupted filesystem mirror still needs reconciliation.
        self.assertIn('C3_LANGUAGE',json.loads((self.home/MIRROR).read_text()))
        self.restart();self.assert_pending()
        self.assertEqual(self.w.batch(self.bid)['approval_attempt']['status'],'RECOVERED_NOT_ACTIVATED')
        self.assertEqual(self.w.approve(self.bid)['status'],'APPROVED')
    def test_failed_recovery_preserves_durable_journal_until_retry(self):
        publish=self.w._publish_adapter_mirror;calls=[]
        def fail(registry):
            calls.append(1)
            if len(calls)==1:publish(registry)
            raise OSError('fixture filesystem unavailable')
        with mock.patch.object(self.w,'_publish_adapter_mirror',fail):
            with self.assertRaises(OSError):self.w.approve(self.bid)
        self.assertEqual(self.w.batch(self.bid)['status'],'ACTIVATING')
        self.assertEqual(self.s.state(KEY)[0]['consolidated'],[])
        self.assertIn('C3_LANGUAGE',json.loads((self.home/MIRROR).read_text()))
        self.restart();self.assert_pending()
    def test_approval_reservation_persistence_failure_has_no_activation(self):
        with self.s.tx() as c:
            c.execute("CREATE TRIGGER intent_fixture_fail BEFORE INSERT ON states WHEN NEW.key='G6_WEIGHT_CONSOLIDATION' AND NEW.payload LIKE '%ACTIVATING%' BEGIN SELECT RAISE(ABORT,'fixture intent failure'); END")
        with mock.patch.object(AdapterRegistry,'activate') as activate:
            with self.assertRaisesRegex(Exception,'fixture intent failure'):self.w.approve(self.bid)
            activate.assert_not_called()
        self.assert_pending()
    def test_real_sqlite_commit_failure_rolls_back_request_registry_and_consolidation(self):
        # Deferred FK violation happens at COMMIT, after mirror publication and
        # all SQL writes. This exercises Store.tx's actual rollback path.
        with self.s.tx() as c:
            c.execute('CREATE TABLE approval_fixture_parent(id INTEGER PRIMARY KEY)')
            c.execute('CREATE TABLE approval_fixture_child(parent INTEGER REFERENCES approval_fixture_parent(id) DEFERRABLE INITIALLY DEFERRED)')
            c.execute("CREATE TRIGGER approval_fixture_commit_fail AFTER UPDATE OF status ON requests WHEN NEW.status='APPROVED' BEGIN INSERT INTO approval_fixture_child VALUES (123); END")
        with mock.patch.object(self.w,'_neuromod') as signal:
            with self.assertRaisesRegex(Exception,'FOREIGN KEY constraint failed'):self.w.approve(self.bid)
            signal.assert_not_called()
        self.assert_pending();self.restart();self.assert_pending()
        self.assertEqual(self.s.rows('SELECT * FROM approval_fixture_child'),[])
        with self.s.tx() as c:c.execute('DROP TRIGGER approval_fixture_commit_fail')
        self.assertEqual(self.w.approve(self.bid)['status'],'APPROVED')
    def test_changed_candidate_after_approval_intent_is_not_activated(self):
        save=_ApprovalStore.set_state
        def changed(proxy,key,payload,expected=None):
            result=save(proxy,key,payload,expected)
            if key==KEY and payload['batches'][self.bid]['status']=='ACTIVATING':
                # Represents a competing candidate edit between the two commits.
                payload['batches'][self.bid]['trainer']['hash']='0'*64
                save(proxy,key,payload,result)
            return result
        with mock.patch.object(_ApprovalStore,'set_state',changed),mock.patch.object(AdapterRegistry,'activate') as activate:
            with self.assertRaisesRegex(ValueError,'Freigabedaten'):self.w.approve(self.bid)
            activate.assert_not_called()
        self.assert_pending();self.restart();self.assert_pending()
    def test_filesystem_reader_can_observe_attempt_before_later_commit_failure(self):
        """Record the real remaining cross-domain reader race; do not hide it."""
        with self.s.tx() as c:
            c.execute('CREATE TABLE reader_fixture_parent(id INTEGER PRIMARY KEY)')
            c.execute('CREATE TABLE reader_fixture_child(parent INTEGER REFERENCES reader_fixture_parent(id) DEFERRABLE INITIALLY DEFERRED)')
            c.execute("CREATE TRIGGER reader_fixture_fail AFTER UPDATE OF status ON requests WHEN NEW.status='APPROVED' BEGIN INSERT INTO reader_fixture_child VALUES (123); END")
        publish=self.w._publish_adapter_mirror;observed=[];read_errors=[]
        def read():
            try:observed.append(runner_lora_args(self.home,'C3_LANGUAGE',self.model))
            except Exception as exc:read_errors.append(type(exc).__name__)
        def publish_then_read(registry):
            publish(registry)
            if registry.get('active',{}).get('C3_LANGUAGE',{}).get('batch_id')==self.bid:
                reader=threading.Thread(target=read);reader.start();reader.join(timeout=2)
                self.assertFalse(reader.is_alive(),'filesystem reader unexpectedly serialized')
        with mock.patch.object(self.w,'_publish_adapter_mirror',publish_then_read):
            with self.assertRaisesRegex(Exception,'FOREIGN KEY'):self.w.approve(self.bid)
        self.assertEqual(read_errors,[]);self.assertEqual(len(observed),1)
        self.assertEqual(observed[0][1],str(self.adapter))
        self.assert_pending()
        self.reader_observation={'filesystem_reader_during_uncommitted_attempt_saw_candidate':bool(observed[0]),
                                 'after_commit_failure_runner_args':runner_lora_args(self.home,'C3_LANGUAGE',self.model),
                                 'after_commit_failure_batch_status':self.w.batch(self.bid)['status'],
                                 'after_commit_failure_consolidated_count':len(self.s.state(KEY)[0]['consolidated']),
                                 'native_model_launched':False}
    def test_constructor_waits_for_live_approval_instead_of_recovering_its_intent(self):
        """One Store is shared; its coordinator flock excludes another owner."""
        intent=threading.Event();proceed=threading.Event();ctor_started=threading.Event();ctor_done=threading.Event()
        errors=[];results=[];save=_ApprovalStore.set_state
        def pause(proxy,key,payload,expected=None):
            result=save(proxy,key,payload,expected)
            if key==KEY and payload['batches'][self.bid]['status']=='ACTIVATING':
                intent.set()
                if not proceed.wait(timeout=3):raise RuntimeError('fixture coordination timeout')
            return result
        def approve():
            try:results.append(self.w.approve(self.bid)['status'])
            except BaseException as exc:errors.append(type(exc).__name__)
        def construct():
            ctor_started.set()
            try:results.append(WeightConsolidation(self.s,self.cfg).batch(self.bid)['status'])
            except BaseException as exc:errors.append(type(exc).__name__)
            finally:ctor_done.set()
        with mock.patch.object(_ApprovalStore,'set_state',pause):
            worker=threading.Thread(target=approve);worker.start()
            try:
                self.assertTrue(intent.wait(timeout=2))
                other=threading.Thread(target=construct);other.start()
                self.assertTrue(ctor_started.wait(timeout=2))
                self.assertFalse(ctor_done.wait(timeout=.05))
            finally:proceed.set();worker.join(timeout=3)
            other.join(timeout=3)
        self.assertFalse(worker.is_alive());self.assertFalse(other.is_alive())
        self.assertEqual(errors,[]);self.assertEqual(results,['APPROVED','APPROVED'])
        self.assertNotIn('RECOVERED_NOT_ACTIVATED',[self.w.batch(self.bid)['approval_attempt']['status']])

if __name__=='__main__':unittest.main()
