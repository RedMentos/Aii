import tempfile
import unittest
from pathlib import Path
from v13 import guards
from v13.config import initialize,validate,DEFAULTS
from v13.store import Store

class CollapseGuard(unittest.TestCase):
    def test_query_echo_and_repetition_are_detected(self):
        q='Wie viel Budget bleibt bei Projekt Aurora nach Option Rot übrig?'
        echo=guards.turn_metrics(q,q);good=guards.turn_metrics('Bei Option Rot bleiben 40 Euro vom Budget übrig, weil 120 minus 80 gleich 40 ist.',q)
        self.assertGreater(echo['query_echo'],.9);self.assertLess(good['query_echo'],.3)
        loop=guards.turn_metrics('ja das ist so ja das ist so ja das ist so ja das ist so ja das ist so')
        self.assertGreater(loop['repetition_rate'],.5);self.assertLess(loop['type_token_ratio'],.3)
        self.assertTrue(guards.turn_metrics('kurz')['below_min_new'])
        self.assertTrue(guards.turn_metrics('Dazu gibt es nichts Belegtes, ich vermute: 40.')['abstention'])
    def test_report_needs_min_turns_and_flags_collapse(self):
        self.assertEqual(guards.collapse_report([])['status'],'INSUFFICIENT_TURNS')
        q='Erkläre bitte kurz wie der Speicher von V13 funktioniert'
        bad=guards.collapse_report([(q,q)]*5);self.assertEqual(bad['status'],'COLLAPSE_SUSPECTED');self.assertIn('query_echo',bad['alarms']);self.assertIn('self_citation',bad['alarms'])
        answers=['Korrekturen landen mit Quelle im Speicher und werden beim nächsten Turn gefunden.',
                 'Der Abruf nutzt lexikalische Treffer, das Thema muss passen.','Gelöschte Quellen werden sofort aus dem Kontext entfernt.',
                 'Replay wiederholt alte Korrekturen nach Abstand, damit nichts verloren geht.']
        ok=guards.collapse_report([('Frage '+str(i)+' zum Speicher',a) for i,a in enumerate(answers)])
        self.assertEqual(ok['status'],'OK',ok)
    def test_store_pairs_reads_only_model_generated_final_answers(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);initialize(home);s=Store(home)
            try:
                sid=s.new_session();e=s.event(sid,'Frage eins')
                with s.tx() as c:
                    c.execute("INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) VALUES (?,?,?,?,?,?,?)",(sid,e['event_id'],'assistant','Antwort eins','FINAL','{"model_generated": true}',0))
                e2=s.event(sid,'Frage zwei')
                with s.tx() as c:
                    c.execute("INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) VALUES (?,?,?,?,?,?,?)",(sid,e2['event_id'],'assistant','Quelle kopiert','FINAL','{"model_generated": false}',0))
                self.assertEqual(guards.store_pairs(s,sid),[('Frage eins','Antwort eins')])
            finally:s.close()

class DataMixAndRelease(unittest.TestCase):
    def test_quotas_follow_v4_section_24(self):
        self.assertTrue(guards.data_mix_check({'human':60,'human_replay':31,'self':6,'dream':3})['pass'])
        v=guards.data_mix_check({'human':50,'self':30,'dream':10,'seed':10})['violations']
        for name in ('HUMAN_SHARE_BELOW_MIN','SELF_GENERATED_ABOVE_MAX','DREAM_ABOVE_MAX','SEED_NOT_ALLOWED'):self.assertIn(name,v)
        self.assertFalse(guards.data_mix_check({})['pass'])
        with self.assertRaises(ValueError):guards.data_mix_check({'teacher':3})
    def test_enforce_drops_only_own_items(self):
        items=[('human',i) for i in range(18)]+[('self',i) for i in range(10)]+[('dream',i) for i in range(10)]+[('seed',0)]
        kept=guards.enforce_data_mix(items,lambda x:x[0]);counts={}
        for o,_ in kept:counts[o]=counts.get(o,0)+1
        self.assertEqual(counts['human'],18);self.assertNotIn('seed',counts)
        self.assertTrue(guards.data_mix_check(counts)['pass'],counts)
        self.assertEqual(guards.enforce_data_mix([('self',1)],lambda x:x[0]),[])
    def test_retention_rollback_and_stability_envelope(self):
        self.assertTrue(guards.retention_rollback(.90,.87)['rollback']);self.assertFalse(guards.retention_rollback(.90,.89)['rollback'])
        cfg=dict(DEFAULTS)
        self.assertEqual(guards.stability_envelope({'max_applied_step_norm':.02},cfg),[])
        self.assertEqual(guards.stability_envelope({'max_applied_step_norm':.03,'effective_max_update_norm':.04},cfg),[])
        bad=guards.stability_envelope({'max_applied_step_norm':.5,'route_shift':.9,'calibration_shift':.5,'data_mix':{'self':5,'human':5},'old_set_score':{'before':.9,'after':.8}},cfg)
        for name in ('UPDATE_NORM_ABOVE_CAP','ROUTE_SHIFT_ABOVE_CAP','CALIBRATION_SHIFT_ABOVE_CAP','SELF_GENERATED_ABOVE_MAX','OLD_SET_REGRESSION_ABOVE_2_PERCENT'):self.assertIn(name,bad)

class DecoderProfile(unittest.TestCase):
    def test_v4_decoder_start_values_and_config(self):
        d=guards.C3_DECODER
        self.assertEqual((d['temperature'],d['top_p'],d['top_k'],d['min_p'],d['repeat_penalty']),(.6,.95,20,.05,1.08))
        self.assertEqual(d['dry_allowed_length'],3);self.assertEqual(guards.MIN_NEW_TOKENS,8)
        self.assertEqual(DEFAULTS['c3_sampling'],'anti_echo')
        with self.assertRaises(ValueError):validate(dict(DEFAULTS,c3_sampling='hot'))
    def test_runner_payload_uses_profile_only_for_c3_free_text(self):
        import inspect
        from v13 import runners
        src=inspect.getsource(runners)
        self.assertIn("self.role=='C3_LANGUAGE' and not schema and self.cfg.get('c3_sampling','anti_echo')=='anti_echo'",src)

if __name__=='__main__':unittest.main()
