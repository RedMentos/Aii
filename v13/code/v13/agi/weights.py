"""WP-AG6 consolidation into weights: knowledge moves from recall into a trained candidate.

Pipeline (FORSCHUNG §9 #6, ROADMAP WP-S3/S7, blueprint L8.3/§21):
  STAGED       nightly batch of human-authored, replay-tested memories (provenance kept, AG12 holdout excluded)
  TRAINED      a pluggable trainer (LoRA / sparse memory finetuning / memory slots) produced a candidate
  GATE_PASS    retention gate: AG12 eval of candidate vs base, forgetting, drift (KL to base), batch recall
  PENDING_USER a store request waits for the human; Age 0 base_merge_authority = 0, nothing activates itself
  ACTIVATING   durable manual-approval intent; interrupted mirror publication reopens PENDING_USER on recovery
  APPROVED     user approved; the generation switch itself stays with the existing update/generation path
  REJECTED / GATE_FAIL / NO_TRAINER / ROLLED_BACK
NullTrainer records a batch honestly as NO_TRAINER. Real trainer: v13/lora_trainer.LoraTrainer (WP-S6, torch LoRA on the
master + deployed llama.cpp gate numbers); an approved adapter is bound via lora_trainer.AdapterRegistry, rollback unbinds it.
"""
import json
import time
from pathlib import Path
from ..common import digest,dumps,atomic_write,uid
from .base import StateBox,age_allows

KEY='G6_WEIGHT_CONSOLIDATION';REVISION='g6-weights-v1'
KINDS=('fact','style','preference')
DENY_SOURCE=('DREAM','TEACHER','MODEL','REPLAY','REFERENCE','HYPOTHESIS')
MAX_ITEMS=256;MAX_BATCHES=64
# BOOT gate values (not measured). retention delta reuses the existing retention_max_delta knob.
DRIFT_MAX=.05;LEARNED_MIN=.8;LEAK_MAX=.2;RATED_MIN=8

class NullTrainer:
    method='none'
    def fit(self,items,base_generation,cancel=None,deadline=None):return {'artifact':None,'hash':None,'method':self.method,'metrics':{}}

class _ApprovalStore:
    """AdapterRegistry's state writes join the caller's SQLite transaction.

    No mirror is published by the registry: AG6 journals that filesystem step and
    publishes it while the same transaction holds the store's write lock.
    """
    home=None
    def __init__(self,c):self.c=c
    def state(self,key,default=None):
        row=self.c.execute('SELECT payload,version FROM states WHERE key=?',(key,)).fetchone()
        return (json.loads(row['payload']),row['version']) if row else (default,0)
    def set_state(self,key,payload,expected=None):
        _,v=self.state(key)
        if expected is not None and expected!=v:raise ValueError('Stale state write')
        self.c.execute('INSERT OR REPLACE INTO states VALUES (?,?,?)',(key,v+1,dumps(payload)))
        return v+1

class WeightConsolidation:
    def __init__(self,store,cfg,generality=None,age=None,trainer=None,home=None,clock=time.time):
        self.s=store;self.cfg=cfg;self.g=generality;self.age=age;self.trainer=trainer or NullTrainer();self.home=home;self.clock=clock
        self.box=StateBox(store,KEY,REVISION,lambda:{'batches':{},'consolidated':[],'order':[]})
        self._recover_approvals()
    # -- staging ---------------------------------------------------------------------------------------
    def _replay_passed(self):
        from ..sleep import SCHEDULE_KEY
        st=self.s.state(SCHEDULE_KEY,None)[0] or {}
        return {it['event_id'] for it in st.get('items',{}).values() if it.get('reps',0)>=1 and not it.get('retired')}
    def candidates(self,require_replay_pass=True,cap=True):
        done=set(self.box.load()[0]['consolidated'])
        rows=self.s.rows("SELECT m.id,m.event_id,m.kind,m.key_text,m.value,m.source_id,s.hash,s.chars,s.kind AS skind FROM memories m "
                         "JOIN sources s ON s.id=m.source_id WHERE m.active=1 AND s.deleted=0 ORDER BY m.created")
        passed=self._replay_passed() if require_replay_pass else None
        out=[]
        for m in rows:
            if m['kind'] not in KINDS or m['id'] in done or any(d in m['skind'].upper() for d in DENY_SOURCE):continue
            if passed is not None and m['event_id'] not in passed:continue
            out.append({'memory_id':m['id'],'event_id':m['event_id'],'kind':m['kind'],'prompt':m['key_text'],'target':m['value'],
                        'source_ref':{'source_id':m['source_id'],'sha256':m['hash'],'char_start':0,'char_end':m['chars'],'modality':'text'}})
        return out[:MAX_ITEMS] if cap else out
    def rated_candidates(self,min_score=RATED_MIN):
        """Explicitly user-rated answers (`:note` >= min_score) as style examples; weight grows with the score. Implicit praise and
        low ratings are not trained (no self-reinforcement from model text without an explicit human label)."""
        try:
            from ..inputs import ratings
            rows=ratings(self.s)
        except Exception:return []
        done=set(self.box.load()[0]['consolidated']);out=[]
        for r in rows:
            if r.get('origin')!='EXPLICIT_NOTE' or r['score']<min_score or 'rating:'+r['event_id'] in done:continue
            q=self.s.one("SELECT text FROM messages WHERE event_id=? AND role='user' ORDER BY id LIMIT 1",(r['event_id'],))
            a=self.s.one("SELECT text FROM messages WHERE event_id=? AND role='assistant' AND status='FINAL' ORDER BY id DESC LIMIT 1",(r['event_id'],))
            ev=self.s.one("SELECT source_id FROM events WHERE id=?",(r['event_id'],))
            if not q or not a or not ev:continue
            out.append({'memory_id':'rating:'+r['event_id'],'event_id':r['event_id'],'kind':'rated_answer','prompt':q['text'],'target':a['text'],
                        'weight':round((r['score']-5)/5,3),'rating':r['score'],'source_ref':{'source_id':ev['source_id'],'modality':'text','label':'HUMAN_QUALITY_LABEL_NOT_FACT'}})
        return out
    def sdft_candidates(self):
        """WP-S5 SDFT: human corrections marked `learn`. The target stays empty here; a self-teaching trainer
        (lora_trainer) answers the teacher prompt (question + correction) itself and trains the student prompt on it."""
        try:
            from ..drift import Drift
            rows=Drift(self.s,self.cfg).sdft_dataset()
        except Exception as exc:self.s.log('g6_sdft_error',None,{'error':type(exc).__name__});return []
        from ..memory_trainer import answer_keys
        done=set(self.box.load()[0]['consolidated'])
        return [{'memory_id':r['item_id'],'event_id':r['event_id'],'kind':'sdft','prompt':r['student_prompt'],'target':None,
                 'teacher_prompt':r['teacher_prompt'],'target_policy':r['target_policy'],'origin':r['origin'],
                 'answer_keys':answer_keys({'prompt':r['student_prompt'],'target':r.get('correction') or ''}) if r.get('correction') else None,
                 'source_ref':r['source_ref']} for r in rows if r['item_id'] not in done]
    def stage(self,origin='SYSTEM',require_replay_pass=True,include_rated=False,include_sdft=False):
        if self.cfg.get('learning_mode')=='RECORD_ONLY':return {'status':'SKIPPED_RECORD_ONLY'}
        if not age_allows(self.age,'small_shadow_update',origin):return {'status':'SKIPPED_AGE_RIGHT'}
        items=self.candidates(require_replay_pass,cap=False);admission=None
        try:  # WP-T9 §9.5 learned admission: SHADOW logs scores, ACTIVE (user) orders and drops low scores before the cap
            from ..admission import Admission
            items,admission=Admission(self.s,self.cfg).order(items)
        except Exception as exc:self.s.log('g6_admission_error',None,{'error':type(exc).__name__})
        items=items[:MAX_ITEMS]
        if include_rated:items=(items+self.rated_candidates())[:MAX_ITEMS]
        if include_sdft:items=(items+self.sdft_candidates())[:MAX_ITEMS]
        if not items:return {'status':'NOTHING_TO_STAGE','admission':admission}
        from ..guards import mix_for_training
        items,mix=mix_for_training(items)  # v4 §24 data mix before every training job (human >= 60 %, self <= 10 %, dream <= 5 %)
        if not mix['check']['pass']:self.s.log('g6_data_mix',None,{'status':'DATA_MIX_FAIL','violations':mix['check']['violations'],'before':mix['before']});return {'status':'DATA_MIX_FAIL','data_mix':mix}
        nm=self._neuromod_gate()
        if nm and nm['veto']:return {'status':'SKIPPED_MODULATOR_VETO','neuromodulation':nm}
        if self.g is not None:self.g.guard_training([i['prompt'] for i in items]+[x for i in items for x in (i['target'],i.get('teacher_prompt')) if x])
        h=digest(dumps([[i['memory_id'],i['target']] for i in items]))
        def put(st):
            for b in st['batches'].values():
                if b['dataset_hash']==h and b['status'] not in {'REJECTED','GATE_FAIL','NO_TRAINER','ROLLED_BACK','DATA_MIX_FAIL'}:return dict(b,deduplicated=True)
            bid='g6b_'+h[:16]+'_'+str(int(self.clock()))
            b={'id':bid,'status':'STAGED','origin':origin,'created':self.clock(),'base_generation':self.s.generation_id,'dataset_hash':h,
               'items':items,'trainer':None,'gate':None,'request_id':None,'history':[['STAGED',self.clock()]],'neuromodulation':nm,'data_mix':mix,'admission':admission}
            st['batches'][bid]=b;st['order']=(st['order']+[bid])
            while len(st['order'])>MAX_BATCHES:st['batches'].pop(st['order'].pop(0),None)
            return dict(b)
        b=self.box.mutate(put);self.s.log('g6_stage',None,{'items':len(items),'status':b['status']})
        if not b.get('deduplicated'):self._neuromod('touch',b['id'],refs=[i['source_ref'] for i in items[:8]])
        return {'status':b['status'],'batch_id':b['id'],'items':len(items),'deduplicated':b.get('deduplicated',False)}
    def _set(self,bid,fn):
        def go(st):
            b=st['batches'].get(bid)
            if not b:raise ValueError('Unbekannter Konsolidierungs-Batch')
            fn(st,b);return dict(b)
        return self.box.mutate(go)
    def _move(self,b,status):b['status']=status;b['history'].append([status,self.clock()])
    # -- training + gate -------------------------------------------------------------------------------
    def train(self,bid,cancel=None,deadline=None):
        b=self.batch(bid)
        if b['status']!='STAGED':raise ValueError('Nur STAGED-Batches werden trainiert')
        from ..guards import mix_for_training
        kept,mix=mix_for_training(b['items'])
        if len(kept)!=len(b['items']) or not mix['check']['pass']:  # defence in depth: a batch staged before the mix rule or edited later
            def bad(st,b):b['data_mix']=mix;self._move(b,'DATA_MIX_FAIL')
            return self._set(bid,bad)
        try:
            from ..anchor import for_batch
            anchor,override=for_batch(self.s,b['items'],self.trainer)  # WP-U5 §69: anchor strength from novelty/stability
        except Exception as exc:anchor,override={'error':type(exc).__name__},None
        saved=dict(self.trainer.cfg) if override else None
        try:
            if override:self.trainer.cfg.update(override)
            todo=b['items'] if getattr(self.trainer,'self_teaches',False) else [i for i in b['items'] if i.get('target') is not None]  # SDFT needs a self-teaching trainer
            out=self.trainer.fit(todo,b['base_generation'],cancel,deadline) or {}
        finally:
            if saved is not None:self.trainer.cfg.clear();self.trainer.cfg.update(saved)
        def f(st,b):
            b['data_mix']=mix;b['anchor']=anchor
            b['trainer']={'method':out.get('method'),'artifact':out.get('artifact'),'hash':out.get('hash'),'metrics':out.get('metrics',{}),
                          'eval':out.get('eval'),'role':getattr(self.trainer,'role','C3_LANGUAGE')}
            self._move(b,'TRAINED' if out.get('artifact') else 'NO_TRAINER')
        return self._set(bid,f)
    def train_and_gate(self,bid,cancel=None,deadline=None):
        """Trainer with its own deployed-path evaluator (lora_trainer.LoraTrainer + LlamaCppEvaluator): train, then gate.
        Without an evaluator the batch stays TRAINED and needs gate() with external AG12 numbers."""
        b=self.train(bid,cancel,deadline);ev=(b.get('trainer') or {}).get('eval')
        if b['status']!='TRAINED' or not ev:return b
        return self.gate(bid,ev['base_eval'],ev['candidate_eval'],ev.get('learned_recall'),drift=ev.get('wp_s5_drift'))
    def gate(self,bid,base_eval,candidate_eval,learned_recall=None,drift=None):
        """base_eval/candidate_eval: AG12 run summaries. learned_recall: candidate accuracy on the batch's own prompts.
        drift: WP-S5 report on the frozen drift probes (drift.Drift.measure_lm), when the evaluator measured one."""
        b=self.batch(bid)
        if b['status']!='TRAINED':raise ValueError('Gate nur nach TRAINED')
        delta=float(self.cfg.get('retention_max_delta',.02));checks={}
        bo,co=base_eval.get('overall'),candidate_eval.get('overall')
        checks['general_retention']=bo is not None and co is not None and co>=bo-delta
        bu,cu=base_eval.get('unseen'),candidate_eval.get('unseen')
        checks['unseen_retention']=bu is None or (cu is not None and cu>=bu-delta)
        fr=(candidate_eval.get('forgetting') or {}).get('rate')
        checks['forgetting']=fr is None or fr<=delta
        kl=b['trainer']['metrics'].get('kl_to_base')
        checks['drift']=kl is not None and kl<=DRIFT_MAX
        checks['learned']=learned_recall is not None and learned_recall>=LEARNED_MIN
        # Specificity (knowledge-editing locality): near-miss questions must not receive the learned answers.
        leak=candidate_eval.get('near_miss_leak')
        if leak is not None:checks['specificity']=leak<=float(base_eval.get('near_miss_leak') or 0.)+LEAK_MAX
        if drift is not None:checks['frozen_drift']=bool(drift.get('passed'))  # WP-S5: hash-pinned generic probes, never trained on
        ok=all(checks.values())
        def f(st,b):
            b['gate']={'checks':checks,'base':{'overall':bo,'unseen':bu},'candidate':{'overall':co,'unseen':cu,'forgetting':fr},
                       'kl_to_base':kl,'learned_recall':learned_recall,'retention_max_delta':delta,'drift_max':DRIFT_MAX}
            if drift is not None:b['drift']={k:drift.get(k) for k in ('component','measure','value','cap','n','probes_sha256','passed','error') if k in drift}
            if ok:
                b['request_id']=self.s.request('WEIGHT_CONSOLIDATION',{'batch_id':bid,'base_generation':b['base_generation'],
                    'artifact_hash':b['trainer']['hash'],'items':len(b['items']),'gate':b['gate']})
                self._move(b,'PENDING_USER')
            else:self._move(b,'GATE_FAIL')
        out=self._set(bid,f)
        # §16.3: a failed retention gate reopens/blocks the knowledge path; a pass is measured evidence, not a tag by itself.
        self._neuromod('signal',bid,source_class='real_deterministic_outcome',retention=1. if ok else -1.)
        return out
    # -- human decisions --------------------------------------------------------------------------------
    def _approval_state(self,c):
        proxy=_ApprovalStore(c);st,v=proxy.state(KEY)
        if st is None:st=self.box.empty()|{'revision':REVISION}
        if st.get('revision')!=REVISION:raise ValueError(KEY+': state revision mismatch')
        return proxy,st,v
    def _approval_input_hash(self,b):
        return digest(dumps({k:b.get(k) for k in ('trainer','items','request_id','drift','gate','base_generation')}))
    def _publish_adapter_mirror(self,registry):
        home=getattr(self.s,'home',None)
        if home is None:return
        from ..lora_trainer import MIRROR
        active={r:{k:b[k] for k in ('path','sha256','base_model_sha256','batch_id','scale','sidecar_sha256') if k in b}
                for r,b in registry.get('active',{}).items() if b}
        atomic_write(Path(home)/MIRROR,json.dumps(active,indent=1))
    def _recover_approvals(self):
        """A crash before SQLite commit leaves ACTIVATING, never consolidated.

        Restore the runner mirror from the committed registry before reopening
        the request. Recovery does not activate the attempted candidate; a new
        explicit approve call is required. A mirror error leaves the journal in
        place and propagates, so recovery is never falsely reported complete.
        """
        if not any(b.get('status')=='ACTIVATING' for b in self.box.load()[0]['batches'].values()):return
        from ..lora_trainer import REGISTRY_KEY
        with self.s.tx() as c:
            proxy,st,v=self._approval_state(c)
            pending=[b for b in st['batches'].values() if b.get('status')=='ACTIVATING']
            if not pending:return
            if any(b.get('approval_attempt',{}).get('registry_required') for b in pending):
                self._publish_adapter_mirror(proxy.state(REGISTRY_KEY,{'active':{},'history':[]})[0])
            for b in pending:
                self._move(b,'PENDING_USER');b['approval_attempt']['status']='RECOVERED_NOT_ACTIVATED'
            proxy.set_state(KEY,st,expected=v)
    def approve(self,bid):
        """Manual approval commits registry, request and consolidation together.

        The durable ACTIVATING intent bridges SQLite and the runner's atomic
        mirror replacement. Exceptions restore the old committed mirror and
        reopen PENDING_USER; process interruption is recovered on construction.
        StateBox callbacks are deliberately avoided because they can be retried
        after side effects. Trainers without deployed metadata retain the
        existing approval behavior without claiming an adapter activation.

        The store mutex spans both transactions so another instance cannot
        mistake this live intent for a crash. Filesystem-only runner readers do
        not take that mutex: mirror visibility is recoverable, not atomic with
        SQLite, and requires separate runner/coordinator serialization.
        """
        with self.s.mutex:return self._approve_locked(bid)
    def _approve_locked(self,bid):
        self._recover_approvals()
        attempt=uid('g6approve')
        with self.s.tx() as c:
            proxy,st,v=self._approval_state(c);b=st['batches'].get(bid)
            if not b or b['status']!='PENDING_USER':raise ValueError('Freigabe nur für PENDING_USER')
            from ..drift import gate as drift_gate
            bad=drift_gate({'drift':b['drift']} if b.get('drift') else {},self.cfg)
            if bad:raise ValueError('Freigabe gesperrt: '+', '.join(bad))
            t=b.get('trainer') or {};dep=(t.get('metrics') or {}).get('deployed') or {}
            required=bool(t.get('artifact') and dep.get('model_sha256'))
            b['approval_attempt']={'id':attempt,'registry_required':required,'status':'ACTIVATING','input_hash':self._approval_input_hash(b)}
            self._move(b,'ACTIVATING');proxy.set_state(KEY,st,expected=v)
        try:
            with self.s.tx() as c:
                proxy,st,v=self._approval_state(c);b=st['batches'].get(bid)
                if not b or b['status']!='ACTIVATING' or b.get('approval_attempt',{}).get('id')!=attempt:
                    raise ValueError('Freigabeversuch veraltet')
                if self._approval_input_hash(b)!=b['approval_attempt']['input_hash']:
                    raise ValueError('Freigabedaten verändert')
                t=b.get('trainer') or {};dep=(t.get('metrics') or {}).get('deployed') or {}
                if required:
                    from ..lora_trainer import AdapterRegistry
                    reg=AdapterRegistry(proxy,self.clock)
                    reg.activate(t.get('role') or 'C3_LANGUAGE',t['artifact'],t['hash'],dep['model_sha256'],bid)
                    self._publish_adapter_mirror(reg.report())
                skip=set(((t.get('metrics') or {}).get('sdft') or {}).get('dropped') or [])
                self._move(b,'APPROVED');b['approval_attempt']['status']='COMMITTED'
                st['consolidated']=sorted(set(st['consolidated'])|{i['memory_id'] for i in b['items'] if i['memory_id'] not in skip})
                if b['request_id']:
                    cur=c.execute("UPDATE requests SET status='APPROVED' WHERE id=? AND kind='WEIGHT_CONSOLIDATION' AND status='PENDING'",(b['request_id'],))
                    if cur.rowcount!=1:raise ValueError('Keine offene Konsolidierungsanfrage')
                proxy.set_state(KEY,st,expected=v);out=dict(b)
        except Exception as exc:
            self._recover_approvals()
            self.s.log('g6_adapter_error',None,{'what':'activate','error':type(exc).__name__,'detail':str(exc)[:160]})
            raise
        if required:
            role=t.get('role') or 'C3_LANGUAGE'
            try:
                from .slots import ModelSlots
                slot,_,kind=role.partition('#')
                ModelSlots(self.s,self.age,self.clock).register_asset(slot,(kind or 'lora')+':'+bid,'adapter' if kind else 'lora',dataset_ref='G6:'+bid)
            except Exception as exc:self.s.log('g6_slot_asset_error',None,{'error':type(exc).__name__})
            self.s.log('g6_adapter_activate',None,{'batch_id':bid,'role':role})
        self._neuromod('signal',bid,source_class='human_correction',human_correction=1.,evidence_gain=1.)
        return out
    def _adapter(self,what,b):
        """Legacy registry helper for rollback; approval uses the journaled path above."""
        t=b.get('trainer') or {};dep=(t.get('metrics') or {}).get('deployed') or {}
        if not t.get('artifact') or not dep.get('model_sha256'):return
        try:
            from ..lora_trainer import AdapterRegistry
            reg=AdapterRegistry(self.s,self.clock);role=t.get('role') or 'C3_LANGUAGE'
            if what=='activate':
                reg.activate(role,t['artifact'],t['hash'],dep['model_sha256'],b['id'])
                try:
                    from .slots import ModelSlots
                    slot,_,kind=role.partition('#')  # 'C3_LANGUAGE#sparse_memory' -> slot C3_LANGUAGE, asset kind adapter
                    ModelSlots(self.s,self.age,self.clock).register_asset(slot,(kind or 'lora')+':'+b['id'],'adapter' if kind else 'lora',dataset_ref='G6:'+b['id'])
                except Exception as exc:self.s.log('g6_slot_asset_error',None,{'error':type(exc).__name__})
            else:reg.deactivate(role,b['id'])
            self.s.log('g6_adapter_'+what,None,{'batch_id':b['id'],'role':role})
        except Exception as exc:self.s.log('g6_adapter_error',None,{'what':what,'error':type(exc).__name__,'detail':str(exc)[:160]})
    def _neuromod(self,what,bid,**kw):
        """WP-N10 feed (path 'weights'); best effort, never changes the AG6 outcome."""
        try:
            from ..neuromod import Neuromod
            n=Neuromod(self.s,self.age)
            if what=='touch':n.touch('weights',bid,authority='AG6_STAGE',refs=kw.get('refs'))
            else:n.signal(bid,path='weights',**kw)
        except Exception as exc:self.s.log('neuromod_feed_error',None,{'what':what,'error':type(exc).__name__})
    def _neuromod_gate(self):
        try:
            from ..neuromod import Neuromod
            return Neuromod(self.s,self.age).gate('weights')
        except Exception as exc:
            self.s.log('neuromod_gate_unavailable',None,{'component':'weights','error':type(exc).__name__});return None
    def reject(self,bid,reason='user'):
        def f(st,b):
            if b['status'] in {'APPROVED','ROLLED_BACK'}:raise ValueError('Schon freigegeben; rollback verwenden')
            self._move(b,'REJECTED');b['reason']=str(reason)[:200]
            if b['request_id']:
                with self.s.tx() as c:c.execute("UPDATE requests SET status='REJECTED' WHERE id=?",(b['request_id'],))
        return self._set(bid,f)
    def rollback(self,bid):
        def f(st,b):
            if b['status']!='APPROVED':raise ValueError('Rollback nur für APPROVED')
            self._move(b,'ROLLED_BACK');ids={i['memory_id'] for i in b['items']}
            st['consolidated']=[m for m in st['consolidated'] if m not in ids]
        out=self._set(bid,f);self._adapter('deactivate',out)
        return out
    def batch(self,bid):
        b=self.box.load()[0]['batches'].get(bid)
        if not b:raise ValueError('Unbekannter Konsolidierungs-Batch')
        return b
    def report(self):
        st=self.box.load()[0]
        return {'revision':REVISION,'trainer':getattr(self.trainer,'method','custom'),'consolidated_memories':len(st['consolidated']),
                'batches':[{k:st['batches'][i][k] for k in ('id','status','origin','created','base_generation')}|{'items':len(st['batches'][i]['items'])} for i in st['order'][-16:]],
                'claim_limit':'LoRA trainer is torch-CPU (cloud/Termux), on-device native trainer open (WP-S6); nothing activates without the user'}
