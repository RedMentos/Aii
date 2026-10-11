"""WP-S6/AG6: LoRA trainer glue without torch — gate with deployed numbers, specificity check, approval binds the adapter,
rollback unbinds it, runners only add --lora for an exact hash match."""
from pathlib import Path
import json
import tempfile
import unittest
from v13.runtime import Runtime
from v13.agi.weights import WeightConsolidation
from v13.lora_trainer import AdapterRegistry,runner_lora_args,answer_hit,LoraTrainer
from v13.common import file_hash

class FakeLora:
    method='fake-lora';role='C3_LANGUAGE'
    def __init__(self,home,model,cand,leak=0.,drift=None):
        self.home=home;self.model=model;self.cand=cand;self.leak=leak;self.drift=drift
    def fit(self,items,base,cancel=None,deadline=None):
        self.seen=items;p=self.home/'adapter.gguf';p.write_bytes(b'lora-bytes')
        ms=file_hash(self.model)
        ev={'base_eval':{'overall':.8,'unseen':.75,'near_miss_leak':0.},'candidate_eval':dict(self.cand,near_miss_leak=self.leak),'learned_recall':1.}
        if self.drift is not None:ev['wp_s5_drift']=self.drift
        return {'artifact':str(p),'hash':file_hash(p),'method':self.method,'eval':ev,
                'metrics':{'kl_to_base':.02,'deployed':{'model_sha256':ms,'learned_recall':1.}}}

class LoraGlue(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled','off');self.s=self.r.store
        self.model=self.home/'c3.gguf';self.model.write_bytes(b'quantized-model')
        e=self.s.event(self.r.session,'What is the name of my cat?');self.r.memory.feedback(e['event_id'],'fact','Mitzi')
        self.cfg=self.r.cfg|{'learning_mode':'SHADOW_UPDATE'}
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def wc(self,**kw):
        w=WeightConsolidation(self.s,self.cfg,trainer=FakeLora(self.home,self.model,**kw));w.box.mutate(lambda st:st['batches'].clear());return w
    def test_gate_pass_needs_user_then_binds_and_rollback_unbinds(self):
        w=self.wc(cand={'overall':.8,'unseen':.75,'forgetting':{'rate':0.}})
        bid=w.stage(require_replay_pass=False)['batch_id'];b=w.train_and_gate(bid)
        self.assertEqual(b['status'],'PENDING_USER');self.assertTrue(b['gate']['checks']['specificity'])
        self.assertEqual(runner_lora_args(self.home,'C3_LANGUAGE',self.model),[])  # nothing live before the user
        w.approve(bid);args=runner_lora_args(self.home,'C3_LANGUAGE',self.model)
        self.assertEqual(args[0],'--lora-scaled');self.assertTrue(args[1].endswith('adapter.gguf'))
        self.assertEqual(runner_lora_args(self.home,'B1_DETAIL',self.model),[])
        other=self.home/'other.gguf';other.write_bytes(b'different-model')
        self.assertEqual(runner_lora_args(self.home,'C3_LANGUAGE',other),[])  # wrong base revision -> ignored
        (self.home/'adapter.gguf').write_bytes(b'tampered')
        self.assertEqual(runner_lora_args(self.home,'C3_LANGUAGE',self.model),[])
        w.rollback(bid);self.assertNotIn('C3_LANGUAGE',json.loads((self.home/'config/lora-active.json').read_text()))
    def test_forgetting_or_leak_fails_gate_and_nothing_binds(self):
        w=self.wc(cand={'overall':.58,'unseen':.25,'forgetting':{'rate':.3}})
        b=w.train_and_gate(w.stage(require_replay_pass=False)['batch_id'])
        self.assertEqual(b['status'],'GATE_FAIL');self.assertFalse(b['gate']['checks']['general_retention'])
        w=self.wc(cand={'overall':.8,'unseen':.75,'forgetting':{'rate':0.}},leak=1.)
        b=w.train_and_gate(w.stage(require_replay_pass=False)['batch_id'])
        self.assertEqual(b['status'],'GATE_FAIL');self.assertFalse(b['gate']['checks']['specificity'])
        self.assertEqual(runner_lora_args(self.home,'C3_LANGUAGE',self.model),[])
    def test_frozen_probe_drift_gates_and_blocks_approval(self):
        """WP-S5 in AG6: frozen-probe KL above cap fails the gate; drift_required=1 refuses approval without a measurement."""
        ok={'component':'C3_LANGUAGE','measure':'LM_KL','value':.01,'cap':.05,'n':30,'probes_sha256':'s','passed':True}
        good={'overall':.8,'unseen':.75,'forgetting':{'rate':0.}}
        w=self.wc(cand=good,drift=dict(ok,value=.3,passed=False))
        b=w.train_and_gate(w.stage(require_replay_pass=False)['batch_id'])
        self.assertEqual(b['status'],'GATE_FAIL');self.assertFalse(b['gate']['checks']['frozen_drift']);self.assertEqual(b['drift']['value'],.3)
        self.cfg['drift_required']=1
        w=self.wc(cand=good);bid=w.stage(require_replay_pass=False)['batch_id'];b=w.train_and_gate(bid)
        self.assertEqual(b['status'],'PENDING_USER');self.assertNotIn('frozen_drift',b['gate']['checks'])
        with self.assertRaisesRegex(ValueError,'DRIFT_NOT_MEASURED'):w.approve(bid)
        self.assertEqual(runner_lora_args(self.home,'C3_LANGUAGE',self.model),[])
        w=self.wc(cand=good,drift=ok);bid=w.stage(require_replay_pass=False)['batch_id'];b=w.train_and_gate(bid)
        self.assertTrue(b['gate']['checks']['frozen_drift']);self.cfg['drift_kl_max']=.005  # cap from the current config, not the report
        with self.assertRaisesRegex(ValueError,'DRIFT_ABOVE_CAP'):w.approve(bid)
        self.cfg['drift_kl_max']=.05;self.assertEqual(w.approve(bid)['status'],'APPROVED')
    def test_sdft_corrections_staged_and_self_taught(self):
        """WP-S5 SDFT in AG6: corrections join the batch with an empty target; only a self-teaching trainer receives them."""
        from unittest import mock
        from v13.drift import Drift
        row={'item_id':'sdft:fb1','event_id':'evt_x','kind':'fact','student_prompt':'What is the capital of Australia?','teacher_prompt':'Q + It is Canberra.',
             'target':None,'correction':'It is Canberra.','target_policy':'SELF_TEACHER_IN_CONTEXT','origin':'human_replay',
             'source_ref':{'source_id':1,'sha256':'h','modality':'text','label':'HUMAN_CORRECTION'}}
        w=self.wc(cand={'overall':.8,'unseen':.75,'forgetting':{'rate':0.}})
        with mock.patch.object(Drift,'sdft_dataset',return_value=[row]):
            self.assertEqual(w.stage(require_replay_pass=False)['items'],1)  # off unless asked
            w.box.mutate(lambda st:st['batches'].clear())
            out=w.stage(require_replay_pass=False,include_sdft=True)
        self.assertEqual(out['items'],2);it=[i for i in w.batch(out['batch_id'])['items'] if i['kind']=='sdft'][0]
        self.assertEqual((it['target'],it['answer_keys'],it['origin']),(None,['canberra'],'human_replay'))
        w.train(out['batch_id']);self.assertEqual([i['kind'] for i in w.trainer.seen],['fact'])  # FakeLora cannot self-teach
        w.trainer.self_teaches=True;w.box.mutate(lambda st:[b.update(status='STAGED') for b in st['batches'].values()])
        w.train(out['batch_id']);self.assertEqual(sorted(i['kind'] for i in w.trainer.seen),['fact','sdft'])
    def test_self_teach_uses_teacher_answer_and_drops_misses(self):
        lt=LoraTrainer.__new__(LoraTrainer);lt._encode=lambda tok,p,t=None:([len(p)],None);lt._greedy=lambda torch,model,ids,n:ids
        class Tok:
            def decode(s,ids,skip_special_tokens=True):return 'The capital of Australia is Canberra.' if ids[0]>20 else 'Sydney.'
        items=[{'memory_id':'m','prompt':'q','target':'t'},
               {'memory_id':'sdft:a','prompt':'What is the capital?','target':None,'teacher_prompt':'x'*30,'answer_keys':['canberra']},
               {'memory_id':'sdft:b','prompt':'Other?','target':None,'teacher_prompt':'short','answer_keys':['canberra']}]
        out,st=lt.self_teach(None,Tok(),None,items)
        self.assertEqual([i['memory_id'] for i in out],['m','sdft:a']);self.assertEqual(out[1]['target'],'The capital of Australia is Canberra.')
        self.assertEqual(out[1]['prompt'],'What is the capital?');self.assertEqual((st['items'],st['kept'],st['dropped']),(2,1,['sdft:b']))
        self.assertEqual(LoraTrainer.teacher_prefix('Sure! It is Canberra. Canberra was planned in 1913.',['canberra']),'Sure! It is Canberra.')
    def test_registry_restores_previous_binding(self):
        reg=AdapterRegistry(self.s);a=self.home/'a.gguf';b=self.home/'b.gguf';a.write_bytes(b'a');b.write_bytes(b'b')
        ms=file_hash(self.model);reg.activate('C3_LANGUAGE',a,file_hash(a),ms,'g1');reg.activate('C3_LANGUAGE',b,file_hash(b),ms,'g2')
        self.assertIsNone(reg.deactivate('C3_LANGUAGE','g1'))  # only the current binding can be rolled back
        reg.deactivate('C3_LANGUAGE','g2');self.assertTrue(runner_lora_args(self.home,'C3_LANGUAGE',self.model)[1].endswith('a.gguf'))
        with self.assertRaises(ValueError):reg.activate('C3_LANGUAGE',a,'0'*64,ms,'g3')
    def test_explicit_high_rating_becomes_weighted_style_item(self):
        from v13.inputs import record_rating
        e=self.s.event(self.r.session,'Explain photosynthesis briefly.')
        with self.s.tx() as c:
            c.execute("INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) VALUES(?,?,?,?,?,?,?)",(self.r.session,e['event_id'],'user','Explain photosynthesis briefly.','FINAL','{}',1.))
            c.execute("INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) VALUES(?,?,?,?,?,?,?)",(self.r.session,e['event_id'],'assistant','Plants turn light into sugar.','FINAL','{}',2.))
        record_rating(self.s,e['event_id'],9,'EXPLICIT_NOTE')
        w=self.wc(cand={'overall':.8,'unseen':.75,'forgetting':{'rate':0.}})
        rc=w.rated_candidates();self.assertEqual(len(rc),1);self.assertEqual(rc[0]['weight'],.8);self.assertEqual(rc[0]['target'],'Plants turn light into sugar.')
        out=w.stage(require_replay_pass=False,include_rated=True);self.assertEqual(out['items'],1)  # data mix: 1 human item leaves no room for a self-written target (self <= 10 %)
        self.assertEqual(w.batch(out['batch_id'])['data_mix']['dropped'],1)
        record_rating(self.s,e['event_id'],3,'EXPLICIT_NOTE');self.assertEqual(w.rated_candidates(),[])  # later low note replaces it
    def test_helpers_without_torch(self):
        self.assertTrue(answer_hit('Your cat is  called MITZI.',['mitzi']));self.assertFalse(answer_hit('no idea',['mitzi']))
        t=LoraTrainer(self.home,self.home/'work');self.assertEqual(t.fit([],'g')['metrics']['reason'],'EMPTY_BATCH')


class KlShortAnswer(unittest.TestCase):
    def test_kl_stops_where_base_continuation_ended(self):
        """A one-word answer + EOS: llama-server returns no completion_probabilities after EOS (real bug, 33 probes)."""
        from v13.lora_trainer import LlamaCppEvaluator
        ev=LlamaCppEvaluator.__new__(LlamaCppEvaluator);ev.adapter=None
        def j(method,path,payload=None):
            if path=='/apply-template':return {'prompt':'p'}
            if path=='/tokenize':return {'tokens':[1,2]}
            if payload.get('return_tokens'):return {'tokens':[5,6]}
            if len(payload['prompt'])>=4:return {'content':''}  # after EOS
            return {'completion_probabilities':[{'top_logprobs':[{'id':5,'logprob':-.1},{'id':7,'logprob':-2.5}]}]}
        ev._j=j
        v=ev.kl(['Q?']);self.assertIsNotNone(v);self.assertLess(v,.05)  # same dists: only the top-k renormalisation remains

if __name__=='__main__':unittest.main()
