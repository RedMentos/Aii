"""Structural regressions. Fixtures here are not native/hardware proof artifacts."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from v13.common import Cancelled,Unavailable,dumps
from v13.contracts import packet
from v13.runtime import Runtime
from v13.runners import LlamaRunner
from v13.proofs import assess_native_probe,native_probe_evidence,audit_event
from v13.verification import completion_ledger
from v13.memory import relevance

class ProofGate(unittest.TestCase):
    def sample(self):
        revisions={r:'fixture-revision' for r in ['C3_LANGUAGE','C2_CONTROL','B1_DETAIL','B2_GIST']}
        roles={r:{'ok':True,'actual_output':'unit fixture','unload':{'process_reaped':True}} for r in revisions}
        roles['C2_CONTROL']={'ok':True,'embedding_dim':3072,'embedding_squared_norm':1.}
        return {'status':'SMOKE_PASS','phone_measured':True,'device':{'android':True},'roles':roles,'model_revisions':revisions},revisions
    def test_smoke_does_not_complete_step1_or_step2(self):
        p,rev=self.sample();a=assess_native_probe(p,rev);self.assertTrue(a['phone_smoke_valid']);self.assertFalse(a['step1_complete']);self.assertFalse(a['step2_complete']);self.assertFalse(a['configuration_recorded'])
    def test_missing_roles_failed_status_wrong_revision(self):
        p,rev=self.sample()
        for change in [lambda x:x.update(status='SMOKE_PARTIAL'),lambda x:x['roles'].pop('B2_GIST'),lambda x:x['model_revisions'].update(C3_LANGUAGE='wrong'),lambda x:x['roles']['C2_CONTROL'].update(embedding_squared_norm=float('nan')),lambda x:x['device'].update(android=False)]:
            bad=copy.deepcopy(p);change(bad);self.assertFalse(assess_native_probe(bad,rev)['smoke_valid'])
    def test_malformed_nested_evidence_never_passes_or_crashes(self):
        p,rev=self.sample()
        for change in [lambda x:x.update(model_revisions=None),lambda x:x.update(device=[]),lambda x:x.update(phone_measured=False),lambda x:x['roles']['B1_DETAIL'].update(unload=None),lambda x:x['roles']['C2_CONTROL'].update(embedding_squared_norm=True)]:
            bad=copy.deepcopy(p);change(bad);self.assertFalse(assess_native_probe(bad,rev)['smoke_valid'])

class Pipeline(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home);self.r.cfg['observer_mode']='off'
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def turn(self):
        eid=self.r.submit('Kopiere exakt: Budget 120 Euro');end=time.monotonic()+5
        while not self.r.idle() and time.monotonic()<end:time.sleep(.02)
        self.assertTrue(self.r.idle());e=json.loads(self.r.store.one('SELECT packet FROM events WHERE id=?',(eid,))['packet']);return e
    def test_persisted_exec_broadcast_and_corollary_order(self):
        s=self.r.store;rid=s.request('RULES',{'base_rule':s.generation()['rule_version'],'after':['Keine Cloud']});s.approve_rule(rid,self.r.cfg,{})
        e=self.turn();a=audit_event(s,e['event_id'])
        for name in ['c1_state_packet','broadcast_packet','single_assistant_stream','single_action_owner','corollary_before_first_output','self_hash_matches','source_refs_valid']:self.assertTrue(a['checks'][name],name)
        self.assertFalse(a['checks']['actual_model_output'])  # exact-copy unit test is not inference
        b=json.loads(s.one("SELECT payload FROM packets WHERE event_id=? AND kind='JEFBroadcastPacket'",(e['event_id'],))['payload']);self.assertEqual(b['constraints'],['Keine Cloud'])
    def test_stale_broadcast_rejected_before_model(self):
        e=self.turn()
        with self.assertRaisesRegex(ValueError,'veraltet'):self.r.cognition.offer('B1_DETAIL',e,99,time.monotonic()+2)
    def test_query_persists_broadcast_link_even_if_runner_missing(self):
        e=self.turn();s=self.r.store;state,_=s.state('C1_EXEC:'+self.r.session)
        v=json.loads(s.one("SELECT payload FROM packets WHERE event_id=? AND kind='JEFBroadcastPacket'",(e['event_id'],))['payload'])['state_version']
        with self.assertRaises(Unavailable):self.r.cognition.offer('B1_DETAIL',e,v,time.monotonic()+2)
        q=json.loads(s.one("SELECT payload FROM packets WHERE event_id=? AND kind='QueryPacket'",(e['event_id'],))['payload']);b=s.one('SELECT kind FROM packets WHERE id=?',(q['broadcast_packet_id'],))
        self.assertEqual(b['kind'],'JEFBroadcastPacket');self.assertEqual(q['source_view_width_chars'],240);self.assertFalse(q['probe_only'])
        attempt=json.loads(s.one("SELECT metrics FROM telemetry WHERE event_id=? AND kind='body_offer_attempt'",(e['event_id'],))['metrics']);self.assertEqual(attempt['query_packet_id'],q['packet_id']);self.assertEqual(attempt['status'],'ERROR')
    def test_peer_receiver_and_event_binding(self):
        e=self.turn();s=self.r.store
        v=json.loads(s.one("SELECT payload FROM packets WHERE event_id=? AND kind='JEFBroadcastPacket'",(e['event_id'],))['payload'])['state_version']
        offer=packet('OfferPacket','B1_DETAIL',e['event_id'],e['brain_generation_id'],role='B1_DETAIL',based_on_state_version=v,deadline_monotonic_ns=time.monotonic_ns()+10**9,evidence_refs=[e['source_ref']],offer={'summary':'fixture','uncertainty':'fixture','needs_reentry':False},confidence=0.)
        s.add_packet('OfferPacket',offer);peer=self.r.cognition.communicate(offer,'B2_GIST')
        self.assertTrue(s.one('SELECT id FROM packets WHERE id=?',(peer['message_packet_id'],)))
        with self.assertRaisesRegex(ValueError,'Empfänger'):self.r.cognition.offer('B1_DETAIL',e,v,time.monotonic()+2,peer)
        peer['message_packet_id']='missing'
        with self.assertRaisesRegex(ValueError,'Provenance'):self.r.cognition.offer('B2_GIST',e,v,time.monotonic()+2,peer)
    def test_probe_file_presence_cannot_promote_step1(self):
        p=self.home/'exports/native-probe.json';p.write_text('{}');self.r.store.set_meta('latest_native_probe',str(p))
        self.assertFalse(native_probe_evidence(self.r)['smoke_valid']);row=next(x for x in completion_ledger(self.r)['rows'] if x['feature_id']=='STEP1_JEF_VERTICAL');self.assertEqual(row['gate_status'],'PARTIAL')
    def test_probe_rejects_input_without_creating_test_chat_event(self):
        with self.r.lock:self.r.current='probe'
        try:
            with self.assertRaises(RuntimeError):self.r.submit('must not enter probe session')
            self.assertEqual(self.r.store.rows('SELECT * FROM events'),[])
        finally:
            with self.r.lock:self.r.current=None
    def test_load_failure_has_metrics_without_fake_memory(self):
        runner=LlamaRunner(self.home,'C3_LANGUAGE',self.home/'missing.gguf',self.r.cfg)
        with self.assertRaises(Unavailable):list(runner.generate([{'role':'user','content':'fixture'}],threading.Event(),time.monotonic()+1))
        self.assertEqual(runner.last_metrics['status'],'ERROR');self.assertIsNone(runner.last_metrics['sampled_peak_rss_bytes']);self.assertEqual(runner.last_metrics['generated_tokens'],0)
        self.assertEqual(runner.last_metrics['last_phase'],'load');self.assertNotIn('prefill_to_first_token_s',runner.last_metrics['stage_durations_s'])
    def test_entity_topic_retrieval_handles_partial_transfer_without_other_attribute_leak(self):
        key='Welches Budget hat Projekt Aurora? Sag nur den Betrag, falls er bekannt ist.'
        positives=[
            'Für Projekt Aurora: Wie viel bleibt vom Budget nach einer Ausgabe von 30 Euro?',
            'Projekt Aurora hat welches verfügbare Budget?',
            'Wie viel ist die Hälfte des Budgets von Projekt Aurora?',
            'Wie hoch ist das Budget von Projekt Aurora? Beachte weiterhin die lokale Vorgabe.',
        ]
        for query in positives:
            self.assertGreaterEqual(relevance(query,key),self.r.cfg['memory_threshold'],query)
        negatives=[
            'Wer leitet Projekt Aurora? Nenne nur den Namen, falls er bekannt ist.',
            'Wann ist die Deadline von Projekt Aurora? Nenne nur das Datum, falls es bekannt ist.',
            'Welches Budget hat Projekt Borealis?',
        ]
        for query in negatives:self.assertEqual(relevance(query,key),0.,query)
    def test_telemetry_omits_raw_text_but_keeps_metrics_and_exact_source(self):
        s=self.r.store;e=self.turn();secret='PRIVATE_TEXT_must_only_stay_in_provenance'
        s.log('turn_finished',e['event_id'],{'status':'FINAL','route':{'source':'NATIVE_C2_ADVISORY','native_control':{'reasoning':secret}},'detail':secret,secret:999,'runner':{'duration_s':1.25,'resource_samples':[{'rss_bytes':123,'phase':'stream'}]}})
        row=s.one('SELECT metrics FROM telemetry ORDER BY id DESC LIMIT 1');m=json.loads(row['metrics'])
        self.assertNotIn(secret,row['metrics']);self.assertEqual(m['status'],'FINAL');self.assertEqual(m['runner']['duration_s'],1.25);self.assertEqual(m['runner']['resource_samples'][0]['rss_bytes'],123)
        self.assertEqual(s.read_source(e['source_ref']),'Kopiere exakt: Budget 120 Euro')
    def test_legacy_telemetry_is_scrubbed_once_on_restart(self):
        s=self.r.store;e=self.turn();secret='LEGACY_PRIVATE_NATIVE_REASONING'
        with s.tx() as c:
            c.execute("INSERT INTO telemetry(kind,metrics,created) VALUES ('turn_finished',?,?)",(dumps({'detail':secret,'duration_s':2.5}),time.time()))
        s.set_meta('telemetry_policy_revision',1);self.r.close();self.r=Runtime(self.home)
        row=self.r.store.one('SELECT metrics FROM telemetry ORDER BY id DESC LIMIT 1');self.assertNotIn(secret,row['metrics']);self.assertEqual(json.loads(row['metrics'])['duration_s'],2.5);self.assertEqual(self.r.store.meta('telemetry_policy_revision'),2)
        self.assertEqual(self.r.store.read_source(e['source_ref']),'Kopiere exakt: Budget 120 Euro')
    def test_unload_reaps_actual_process_and_records_role(self):
        runner=LlamaRunner(self.home,'B1_DETAIL',self.home/'not-used.gguf',self.r.cfg);proc=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']);runner.proc=proc;self.r.pool.current=runner
        result=self.r.pool.unload();self.assertTrue(result['process_reaped']);self.assertIsNotNone(proc.poll());self.assertEqual(self.r.pool.pids(),[]);self.assertEqual(self.r.pool.release_history[-1]['role'],'B1_DETAIL')
    def test_cancel_check_reaps_resident_process_before_returning(self):
        runner=LlamaRunner(self.home,'B1_DETAIL',self.home/'not-used.gguf',self.r.cfg);proc=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']);runner.proc=proc;cancel=threading.Event();cancel.set()
        try:
            with self.assertRaises(Cancelled):list(runner.generate([{'role':'user','content':'unit fixture'}],cancel,time.monotonic()+3))
            self.assertIsNotNone(proc.poll());self.assertEqual(runner.pids(),[]);self.assertTrue(runner.last_metrics['interruption_unload']['process_reaped'])
        finally:runner.unload()
if __name__=='__main__':unittest.main()
