"""WP-BJ1 (§13, IH-H25, §14.5): B-JEPA as a local predictive latent objective on a body's LoRA adapter.

Blueprint §13.1: student/context/predictor learn by gradient, the target path is stop-gradient and follows by EMA.
§13.4: on mobile the EMA copy covers only the selected adapter, not the billion base weights. §14.5: the LoRA adapter
is the body's active plasticity. Two views of the same experience: the question (context view, student) and the
answer text alone (target view). The predictor maps the student's latent of the question onto the EMA target's latent
of the answer; loss 1 - cosine. Target modes:
  ema       EMA copy of the adapter (canon)
  base      frozen base body (LLM-JEPA style, what lora_trainer.py's jepa_weight already does)
  shuffled  EMA target of a different experience (negative control: same budget, wrong pairing)
The ObjectiveAdapter field set is the one from GPT Run38 (codex/body-jepa-micro-run38-20261024, synthetic micro-port);
this module is its first use on real body weights. Torch is imported lazily; nothing here is active in the runtime.
"""
from dataclasses import dataclass
import json,math,time,operator

MODES=('ema','base','shuffled')

@dataclass(frozen=True)
class ObjectiveAdapter:
    objective_id:str
    applicable_components:tuple
    required_inputs:tuple
    target_builder:str
    stop_gradient_policy:str
    ema_policy:tuple
    loss_terms:tuple
    credit_mapper:str
    update_scope:tuple
    eval_metrics:tuple

OBJECTIVE=ObjectiveAdapter(
    'B_JEPA_LORA_TWO_VIEW_V1',('B1_DETAIL','B2_GIST'),('context_view_ids','target_view_ids','eligibility'),
    'EMA_ADAPTER_TARGET','DETACH_TARGET',('SELECTED_ADAPTER_ONLY',),('ANSWER_CE','ANCHOR_KL','JEPA_COSINE'),
    'LOCAL_ELIGIBILITY_WEIGHT',('LORA_ADAPTER','PREDICTOR'),
    ('learned_recall','paraphrase_recall','near_miss_leak','retention','target_effective_rank','ema_delta'))

def credit_map(learner_error,eligibility,path='B1_DETAIL'):
    """Bounded local credit for the registered body paths; never an update authority by itself."""
    if path not in OBJECTIVE.applicable_components:raise ValueError('unregistered learner path')
    if not all(type(v) in (float,int) and math.isfinite(v) for v in (learner_error,eligibility)):raise ValueError('nonfinite credit input')
    if learner_error<0 or not 0<=eligibility<=1:raise ValueError('credit input out of bounds')
    return {'path':path,'credit':min(1.,learner_error)*eligibility,'authority':'SHADOW_NO_AGE_ACTION'}

def effective_rank(x,eps=1e-12):
    """exp(entropy of normalised singular values) of the centred rows (Roy & Vetterli); 0 for <2 rows or no variance."""
    import numpy as np
    x=np.asarray(x,dtype='float64')
    if x.ndim!=2 or len(x)<2 or not np.isfinite(x).all():return 0.
    s=np.linalg.svd(x-x.mean(0),compute_uv=False);t=s.sum()
    if t<=eps:return 0.
    p=s/t;p=p[p>0];return float(np.exp(-(p*np.log(p)).sum()))

def derangement(n,rng):
    """Bounded valid permutation without fixed points; no fabricated negative control."""
    if n<2:raise ValueError('need two experiences for a shuffled target')
    expected=list(range(n))
    # Preserve the existing RNG sequence for successful draws. An adversarial
    # or broken RNG must never hang a shuffled-target training arm indefinitely.
    for _ in range(64):  # BOOT fail-closed attempt cap, not a tuned optimum
        raw=rng.permutation(n)
        try:
            if len(raw)!=n:raise ValueError('invalid RNG permutation')
            p=[]
            for v in raw:
                if isinstance(v,bool):raise ValueError('invalid RNG permutation')
                p.append(operator.index(v))  # NumPy integers OK; floats/strings never truncated
        except (TypeError,ValueError,OverflowError):
            raise ValueError('invalid RNG permutation') from None
        if sorted(p)!=expected:
            raise ValueError('invalid RNG permutation')
        if all(p[i]!=i for i in range(n)):return p
    raise ValueError('derangement attempts exhausted')

class EmaAdapter:
    """EMA copy of the trainable adapter tensors only (§13.4). swap() temporarily loads the EMA values into the live
    model for a no-grad target pass and restores the student values afterwards."""
    def __init__(self,params,decay):
        if not 0<=decay<1:raise ValueError('decay must be in [0,1)')
        self.params=list(params);self.decay=float(decay);self.shadow=[p.detach().clone() for p in self.params];self.updates=0
    def update(self):
        import torch
        with torch.no_grad():
            for s,p in zip(self.shadow,self.params):s.mul_(self.decay).add_(p.detach(),alpha=1-self.decay)
        self.updates+=1
    def delta(self):
        """L2 distance EMA vs student over all adapter tensors."""
        return float(sum(float((s-p.detach()).pow(2).sum()) for s,p in zip(self.shadow,self.params))**.5)
    def swap(self):
        ema=self
        class _Swap:
            def __enter__(self):
                import torch
                self.keep=[p.detach().clone() for p in ema.params]
                with torch.no_grad():
                    for s,p in zip(ema.shadow,ema.params):p.copy_(s)
            def __exit__(self,*exc):
                import torch
                with torch.no_grad():
                    for k,p in zip(self.keep,ema.params):p.copy_(k)
                return False
        return _Swap()

def make_predictor(torch,dim):
    """Linear predictor initialised to identity, so step 0 is the plain cosine between the two views."""
    lin=torch.nn.Linear(dim,dim)
    with torch.no_grad():lin.weight.copy_(torch.eye(dim));lin.bias.zero_()
    return lin

def last_token_latent(torch,model,batch_ids,layer=-1):
    """Hidden state of the last real token per row (right padding, pad id ignored via lengths)."""
    ids,lens=batch_ids
    if (ids.ndim!=2 or lens.ndim!=1 or len(lens)!=ids.shape[0] or ids.shape[1]<1
            or not bool(torch.all((lens>=1)&(lens<=ids.shape[1])))):
        raise ValueError('nonempty right-padded token sequences required')
    att=(torch.arange(ids.shape[1])[None,:]<lens[:,None]).long()
    out=model(input_ids=ids,attention_mask=att,output_hidden_states=True)
    h=out.hidden_states[layer]
    return h[torch.arange(len(lens)),lens-1]

def ema_target_latent(torch,model,tgt,ema,layer=-1,eval_target=False):
    """Opt-in dropout-stable EMA target, without changing frozen train-mode cohorts.

    The EMA adapter and all module train/eval flags are restored even if the
    target forward raises. The student graph is created only after this pass.
    """
    if type(eval_target) is not bool:raise ValueError('jepa_target_eval must be bool')
    if not eval_target:
        with torch.no_grad(),ema.swap():
            return last_token_latent(torch,model,tgt,layer).detach()
    modules=list(model.modules());flags=[m.training for m in modules]
    try:
        model.eval()
        with torch.no_grad(),ema.swap():
            return last_token_latent(torch,model,tgt,layer).detach()
    finally:
        # Run train() hooks on the root, then restore mixed child flags exactly.
        model.train(flags[0])
        for module,flag in zip(modules,flags):module.training=flag


def pad(torch,seqs,pad_id=0):
    if not seqs or any(len(s)==0 for s in seqs):
        raise ValueError('nonempty token sequences required')
    n=max(len(s) for s in seqs);ids=torch.full((len(seqs),n),pad_id,dtype=torch.long)
    for i,s in enumerate(seqs):ids[i,:len(s)]=torch.tensor(s)
    return ids,torch.tensor([len(s) for s in seqs])

def jepa_loss(torch,model,predictor,ctx,tgt,mode,ema=None,base_targets=None,perm=None,weights=None,layer=-1):
    """1 - cos(predictor(student latent of context view), stop-grad target latent of target view), eligibility-weighted mean.
    Returns (loss, detached target latents)."""
    if mode not in MODES:raise ValueError('unknown target mode')
    if base_targets is not None:t=base_targets  # frozen-base targets, or EMA targets computed BEFORE the student forward
    elif mode=='base':raise ValueError('base mode needs precomputed frozen-base targets')
    else:
        # swap() edits adapter tensors in place: only safe when no autograd graph of this step exists yet
        if ema is None:raise ValueError('ema/shuffled mode needs the EMA adapter')
        with torch.no_grad(),ema.swap():t=last_token_latent(torch,model,tgt,layer)
    t=t.detach()
    if mode=='shuffled':
        if (not isinstance(perm,(list,tuple)) or len(perm)!=len(t)
                or any(type(v) is not int for v in perm)
                or sorted(perm)!=list(range(len(t)))
                or any(i==v for i,v in enumerate(perm))):
            raise ValueError('shuffled mode requires a true derangement')
        t=t[torch.tensor(perm,device=t.device)]
    p=predictor(last_token_latent(torch,model,ctx,layer))
    if t.shape!=p.shape or not bool(torch.isfinite(t).all()) or not bool(torch.isfinite(p).all()):
        raise ValueError('invalid target/student latent shape or nonfinite values')
    l=1-torch.nn.functional.cosine_similarity(p,t,dim=-1)
    w=torch.ones_like(l) if weights is None else torch.as_tensor(weights,dtype=l.dtype,device=l.device)
    if (w.ndim!=1 or w.shape!=l.shape or not bool(torch.isfinite(w).all())
            or bool((w<0).any()) or not bool(w.sum()>0)):
        raise ValueError('eligibility weights must be finite, aligned, >=0 and not all zero')
    return (l*w).sum()/w.sum(),t

def minor_subspace_init(torch,model,r):
    """Subspace Tuning (arXiv 2610.22293, Chavan et al.) in its cheapest LoRA form (MiLoRA-style): the update B@A may only
    live in the span of the r LOWEST singular directions of each wrapped weight, so the dominant directions (where SFT drift
    and forgetting concentrate) stay untouched. Linear W (out x in): in <= out -> A (r x in) = lowest right singular vectors,
    frozen, train B (starts 0); in > out -> B (out x r) = lowest left singular vectors, frozen, train A (starts 0).
    Singular directions come from eigh of the smaller Gram matrix, so the largest matrix is 2048 x 2048. Returns a summary."""
    if type(r) is not int or r<1:raise ValueError('subspace rank must be a positive integer')
    n=0;frozen=0;share=[]
    for name,mod in model.named_modules():
        if not (hasattr(mod,'lora_A') and 'default' in getattr(mod,'lora_A',{})):continue
        W=mod.base_layer.weight.detach().double();out_d,in_d=W.shape
        if r>min(out_d,in_d) or not bool(torch.isfinite(W).all()):
            raise ValueError('invalid subspace rank or nonfinite base weight')
        with torch.no_grad():
            if in_d<=out_d:
                evals,evecs=torch.linalg.eigh(W.T@W)
            else:
                evals,evecs=torch.linalg.eigh(W@W.T)
            singular=evals.clamp(min=0).sqrt()
            mass=singular.sum()
            if not bool(torch.isfinite(mass)) or not bool(mass>0):
                raise ValueError('subspace singular mass must be finite and positive')
            if in_d<=out_d:
                low=evecs[:,:r].T.float().contiguous()  # r x in
                mod.lora_A['default'].weight.copy_(low);mod.lora_A['default'].weight.requires_grad_(False);mod.lora_B['default'].weight.zero_()
            else:
                low=evecs[:,:r].float().contiguous()  # out x r
                mod.lora_B['default'].weight.copy_(low);mod.lora_B['default'].weight.requires_grad_(False);mod.lora_A['default'].weight.zero_()
            share.append(float(singular[:r].sum()/mass))
        n+=1;frozen+=int(low.numel())
    return {'modules':n,'frozen_side_params':frozen,'mean_low_singular_mass_share':round(sum(share)/max(1,len(share)),6)}

def anchor_retention_kl(torch,model,anchor_seqs,anchor_logp):
    """Read-only forward KL(master || adapted) on fixed, aligned anchor tokens."""
    if len(anchor_seqs)!=len(anchor_logp):
        raise ValueError('unaligned retention anchors')
    result=[]
    with torch.no_grad():
        for seq,base_logp in zip(anchor_seqs,anchor_logp):
            adapted_logp=torch.log_softmax(model(torch.tensor([seq])).logits[0].float(),dim=-1)
            if (adapted_logp.shape!=base_logp.shape
                    or not bool(torch.isfinite(base_logp).all())
                    or not bool(torch.isfinite(adapted_logp).all())):
                raise ValueError('invalid anchor distribution')
            divergence=(base_logp.exp()*(base_logp-adapted_logp)).sum(-1).mean()
            if not bool(torch.isfinite(divergence)):
                raise ValueError('nonfinite post-training anchor KL')
            result.append(float(divergence))
    return result


def select_heldout_prompts(probes,items,anchors,cap):
    """Return prompt-disjoint heldout candidates and excluded exact overlaps.

    No semantic independence or provenance completeness is asserted. Duplicates
    and empty prompts are never counted as independent retention evidence.
    """
    if type(cap) is not int or not 0<=cap<=16:
        raise ValueError('heldout_probe_cap must be an integer from 0 to 16')
    def norm(value):
        if not isinstance(value,str):raise ValueError('probe/anchor must contain text')
        return ' '.join(value.casefold().split())
    seen={norm(i['prompt']) for i in items}
    seen.update(norm(a) for a in anchors)
    picked=[];excluded=0
    for probe in probes:
        if not isinstance(probe,dict) or 'prompt' not in probe:
            raise ValueError('heldout probe requires prompt text')
        prompt=probe['prompt'];key=norm(prompt)
        if not key or key in seen:
            excluded+=1
            continue
        seen.add(key)
        if len(picked)<cap:picked.append(prompt)
    return picked,excluded


def heldout_retention_kl(torch,model,sequences):
    """Deterministic forward KL(base || adapter) on prompt-disjoint probes.

    Both baseline and adapted distributions must use eval mode: leaving
    training dropout enabled makes retention depend on RNG and can even
    report zero KL for a nonzero adapter. Preserve the caller's mode on
    success and failure, without modifying weights or optimizer state.
    """
    disabled=getattr(model,'disable_adapter',None)
    if not callable(disabled):
        raise ValueError('PEFT disable_adapter context is required for heldout baseline')
    # Preserve mixed module modes (e.g. frozen base in eval while adapter trains).
    # Restoring only model.training would incorrectly switch all children on.
    modules=list(model.modules())
    flags=[module.training for module in modules]
    result=[]
    model.eval()
    try:
        with torch.no_grad():
            for seq in sequences:
                if (not isinstance(seq,(list,tuple)) or not seq or
                        any(type(tok) is not int or tok<0 for tok in seq)):
                    raise ValueError('heldout probe must contain nonempty token IDs')
                ids=torch.tensor([seq],dtype=torch.long)
                with disabled():
                    baseline=torch.log_softmax(model(input_ids=ids).logits[0].float(),dim=-1)
                adapted=torch.log_softmax(model(input_ids=ids).logits[0].float(),dim=-1)
                if (baseline.shape!=adapted.shape or not bool(torch.isfinite(baseline).all())
                        or not bool(torch.isfinite(adapted).all())):
                    raise ValueError('invalid heldout distribution')
                kl=(baseline.exp()*(baseline-adapted)).sum(dim=-1).mean()
                if not bool(torch.isfinite(kl)):
                    raise ValueError('nonfinite heldout KL')
                result.append(max(0.,float(kl)))
    finally:
        model.train(flags[0])
        for module,flag in zip(modules,flags):
            module.training=flag
    return result


def streamed_anchor_kl(torch,model,seq):
    """Exact differentiable KL(base || adapter) with ONE live reference tensor.

    Unlike full-logit caching across dozens of anchors, the frozen base is
    evaluated on demand using the same PEFT model with its adapter disabled.
    Only the adapter forward path receives a gradient. No off-device call.
    """
    if (not isinstance(seq,(list,tuple)) or not seq
            or any(type(i) is not int or i<0 for i in seq)):
        raise ValueError('invalid streamed anchor token IDs')
    disable=getattr(model,'disable_adapter',None)
    if not callable(disable):
        raise ValueError('streamed anchors require a PEFT disable_adapter context')
    ids=torch.tensor([seq],dtype=torch.long)
    # The frozen and adapted distributions must use the same dropout mode.
    # Keep the adapted forward differentiable while both paths run in eval;
    # restore the exact per-module training flags even if a forward raises.
    modules=list(model.modules())
    flags=[module.training for module in modules]
    model.eval()
    try:
        with torch.no_grad(),disable():
            base_logp=torch.log_softmax(model(input_ids=ids).logits[0].float(),dim=-1)
        adapted_logp=torch.log_softmax(model(input_ids=ids).logits[0].float(),dim=-1)
        if (base_logp.shape!=adapted_logp.shape
                or not bool(torch.isfinite(base_logp).all())
                or not bool(torch.isfinite(adapted_logp).all())):
            raise ValueError('invalid streamed anchor distribution')
        result=(base_logp.exp()*(base_logp-adapted_logp)).sum(dim=-1).mean()
        if not bool(torch.isfinite(result)):
            raise ValueError('nonfinite streamed anchor KL')
        return result
    finally:
        model.train(flags[0])
        for module,flag in zip(modules,flags):
            module.training=flag


# -- trainer ---------------------------------------------------------------------------------------------
from .lora_trainer import LoraTrainer,DEFAULTS as _LORA_DEFAULTS,_check,_rss_mb,answer_hit
from .common import digest,dumps,atomic_write,Unavailable

REVISION='v13-body-jepa-trainer-v1'
DEFAULTS=dict(_LORA_DEFAULTS,jepa_weight=.5,jepa_target='ema',jepa_ema_decay=.9,jepa_layer=-1,max_steps=30,min_steps=30,lr=5e-4,heldout_probe_cap=8,anchor_reference_mode='cached')

class BodyJepaTrainer(LoraTrainer):
    """LoRA body trainer with the §13 B-JEPA term (EMA adapter target + predictor) next to answer CE and KL anchors.
    Same fit()/export contract as LoraTrainer, so AG6 can use it as a trainer; one step = one batched pass over all
    items (right padding, causal body). jepa_weight 0 gives the CE+anchor baseline on exactly the same loop."""
    method='lora-torch-cpu-bjepa'
    _anchor_cache={}
    def __init__(self,*a,cfg=None,**k):
        super().__init__(*a,cfg=dict(DEFAULTS,**(cfg or {})),**k)
    @staticmethod
    def _locality_for(items,cfg):
        """Select locality KL anchors; legacy is frozen default, BP2b explicitly opt-in."""
        policy=cfg.get('locality_policy','legacy')
        swaps=int(cfg['locality_swaps'])
        if policy=='legacy':
            return LoraTrainer.locality_prompts(items,swaps)
        if policy=='bp2b':
            from .locality_anchors import generate_anchors
            return generate_anchors(items,swaps)
        raise ValueError('unknown locality_policy')
    def _views(self,tok,items):
        ctx=[self._encode(tok,i['prompt'])[0] for i in items]
        tgt=[tok(str(i['target']),add_special_tokens=False)['input_ids'] for i in items]
        return ctx,tgt
    def _deployed_eval(self,result,items,cancel=None,deadline=None):
        """Reuse the SAME deployed llama.cpp AG6 gate contract as C3 LoraTrainer.

        The FP32/CPU holdout KL above is diagnostic only. Without a pinned
        evaluator, never fabricate a deployed path result or a gate pass.
        """
        if self.evaluator is None:return result
        _check(cancel,deadline)
        ev=self.evaluator(result['artifact'])
        try:
            rep=ev.evaluate(items,self.probes,cancel=cancel,deadline=deadline)
        finally:
            ev.close()
        if not isinstance(rep,dict) or any(k not in rep for k in
              ('base_eval','candidate_eval','learned_recall','kl_to_base')):
            raise Unavailable('Body-JEPA deployed evaluator did not provide AG6 gate evidence')
        _check(cancel,deadline)
        result['metrics'].update({'deployed':rep,'kl_to_base':rep['kl_to_base'],
                                  'kl_source':'deployed_llama_cpp_topk'})
        result['eval']={'base_eval':rep['base_eval'],
                        'candidate_eval':rep['candidate_eval'],
                        'learned_recall':rep['learned_recall']}
        if 'wp_s5_drift' in rep:result['eval']['wp_s5_drift']=rep['wp_s5_drift']
        return result
    def fit(self,items,base_generation,cancel=None,deadline=None):
        if not items:return {'artifact':None,'hash':None,'method':self.method,'metrics':{'reason':'EMPTY_BATCH'}}
        try:import torch,peft  # noqa: F401
        except ImportError:return {'artifact':None,'hash':None,'method':self.method,'metrics':{'reason':'NO_TORCH_PEFT'}}
        import numpy as np
        t0=time.monotonic();cfg=self.cfg;mode=str(cfg['jepa_target']);w_j=float(cfg['jepa_weight']);layer=int(cfg['jepa_layer'])
        anchor_mode=cfg.get('anchor_reference_mode','cached')
        if anchor_mode not in ('cached','stream'):
            raise ValueError('anchor_reference_mode must be cached|stream')
        target_eval=cfg.get('jepa_target_eval',False)
        if type(target_eval) is not bool:raise ValueError('jepa_target_eval must be bool')
        if mode not in MODES:raise ValueError('unknown jepa_target')
        if cfg.get('locality_policy','legacy') not in ('legacy','bp2b'):raise ValueError('unknown locality_policy')
        torch,tok,model=self._load()
        from peft import LoraConfig,get_peft_model
        pad_id=tok.pad_token_id if tok.pad_token_id is not None else 0
        dh=digest(dumps([[i.get('memory_id'),i['prompt'],i['target']] for i in items]+[self.anchors,{k:v for k,v in cfg.items() if k!='threads'}]))[:24]
        out=self.work/dh;out.mkdir(parents=True,exist_ok=True)
        anchors=list(self.anchors)+self._locality_for(items,cfg)
        ck=(str(self.master),self.master_sha,tuple(anchors))
        if anchor_mode=='cached' and ck in BodyJepaTrainer._anchor_cache:
            anchor_seqs,anchor_logp=BodyJepaTrainer._anchor_cache[ck]
        else:
            anchor_seqs=[]
            for a in anchors:
                pid,_=self._encode(tok,a);anchor_seqs.append(pid+self._greedy(torch,model,pid,24))
            anchor_logp=None
            if anchor_mode=='cached':
                with torch.no_grad():
                    anchor_logp=[
                        torch.log_softmax(model(torch.tensor([seq])).logits[0].float(),-1)
                        for seq in anchor_seqs
                    ]
                BodyJepaTrainer._anchor_cache[ck]=(anchor_seqs,anchor_logp)
        # STREAM avoids long-lived [tokens,vocab] matrices per anchor. The
        # frozen base distribution is recomputed sequentially only when needed.
        anchor_cached_bytes=(
            sum(x.numel()*x.element_size() for x in anchor_logp)
            if anchor_logp is not None else 0
        )
        data=[self._encode(tok,i['prompt'],i['target']) for i in items]
        ctx,tgt=self._views(tok,items);ctx_b=pad(torch,ctx,pad_id);tgt_b=pad(torch,tgt,pad_id)
        with torch.no_grad():
            base_t=last_token_latent(torch,model,tgt_b,layer).detach()
            base_ctx=last_token_latent(torch,model,ctx_b,layer).detach()
        lc=LoraConfig(r=int(cfg['rank']),lora_alpha=float(cfg['alpha']),lora_dropout=0.,target_modules=list(cfg['targets']),bias='none')
        model=get_peft_model(model,lc)
        sub=minor_subspace_init(torch,model,int(cfg['rank'])) if str(cfg.get('lora_subspace','none'))=='minor' else None
        params=[p for p in model.parameters() if p.requires_grad];n_train=sum(p.numel() for p in params)
        dim=int(base_t.shape[-1]);pred=make_predictor(torch,dim)
        ema=EmaAdapter(params,float(cfg['jepa_ema_decay']))
        opt=torch.optim.AdamW(params+list(pred.parameters()),lr=float(cfg['lr']),weight_decay=float(cfg['weight_decay']))
        rng=np.random.default_rng(int(cfg['seed']));perm=derangement(len(items),rng) if len(items)>1 else None
        if mode=='shuffled' and perm is None:raise ValueError('shuffled control needs two items')
        ids_b,lens=pad(torch,[d[0] for d in data],pad_id)
        lab_b=torch.full(ids_b.shape,-100,dtype=torch.long)
        for r,(ids,lab) in enumerate(data):lab_b[r,:len(lab)]=torch.tensor(lab)
        att=(torch.arange(ids_b.shape[1])[None,:]<lens[:,None]).long()
        wts=[float(i.get('weight',1.)) for i in items]
        hist=[];step=0;g=torch.Generator().manual_seed(int(cfg['seed']))
        # Explicit opt-in only: the existing frozen cohorts and default trainer are unchanged.
        # Source binding includes the full master SHA, configuration, anchors and dataset.
        checkpoint_dir=None;checkpoint_source=None;restored_step=0
        if cfg.get('checkpoint_resume',False):
            from .body_jepa_checkpoint import restore as restore_bj_step
            if type(self.master_sha) is not str or len(self.master_sha)!=64:
                raise ValueError('Step resume requires a pinned full master SHA256')
            checkpoint_source=digest(dumps({'master_sha256':self.master_sha,
                'dataset_hash':dh,'base_generation':base_generation,'cfg':cfg,'anchors':anchors,'items':items,'probes':self.probes}))
            checkpoint_dir=out/'step-checkpoints'
            restored=restore_bj_step(checkpoint_dir,checkpoint_source,model,pred,opt,ema,g)
            if restored is not None:
                step=restored['step'];hist=restored['history'];restored_step=step
        model.train()
        while step<int(cfg['max_steps']):
            _check(cancel,deadline);opt.zero_grad()
            ema_t_step=None
            if w_j>0 and mode!='base':  # EMA target first: the in-place swap would break a graph built earlier in the step
                ema_t_step=ema_target_latent(torch,model,tgt_b,ema,layer,eval_target=target_eval)
            o=model(input_ids=ids_b,attention_mask=att)
            lg=o.logits[:,:-1].float();lb=lab_b[:,1:]
            tok_ce=torch.nn.functional.cross_entropy(lg.reshape(-1,lg.shape[-1]),lb.reshape(-1),ignore_index=-100,reduction='none').view(lb.shape)
            per=(tok_ce*(lb!=-100)).sum(1)/(lb!=-100).sum(1).clamp(min=1)
            w=torch.tensor(wts);ce=(per*w).sum()/w.sum();loss=ce;jl_v=None
            if w_j>0:
                jl,_=jepa_loss(torch,model,pred,ctx_b,tgt_b,mode,ema=ema,base_targets=base_t if mode=='base' else ema_t_step,perm=perm,weights=wts,layer=layer)
                loss=loss+w_j*jl;jl_v=float(jl.detach())
            loss.backward();kl_sum=0.;pick=[]
            if anchor_seqs and float(cfg['anchor_weight'])>0:
                pick=torch.randperm(len(anchor_seqs),generator=g).tolist()[:int(cfg['anchors_per_step'])]
                for j in pick:
                    if anchor_logp is None:
                        kl=streamed_anchor_kl(torch,model,anchor_seqs[j])
                    else:
                        cl=torch.log_softmax(model(torch.tensor([anchor_seqs[j]])).logits[0].float(),-1)
                        bl=anchor_logp[j]
                        kl=(bl.exp()*(bl-cl)).sum(-1).mean()
                    (float(cfg['anchor_weight'])*kl/len(pick)).backward();kl_sum+=float(kl.detach())
            opt.step();ema.update();step+=1
            hist.append({'step':step,'ce':round(float(ce.detach()),5),'anchor_kl':round(kl_sum/max(1,len(pick)),6),'jepa':None if jl_v is None else round(jl_v,5),'ema_delta':round(ema.delta(),6)})
            if checkpoint_dir is not None:
                from .body_jepa_checkpoint import save as save_bj_step
                save_bj_step(checkpoint_dir,checkpoint_source,step,model,pred,opt,ema,g,hist)
            if step>=int(cfg['min_steps']) and hist[-1]['ce']<=float(cfg['target_loss']):break
        model.eval()
        # Separate KL on truly unseen prompt strings from training/locality anchors.
        # This is an additional prompt-disjoint diagnostic, NOT semantic data independence.
        cap=cfg.get('heldout_probe_cap',8)
        prompts,excluded=select_heldout_prompts(self.probes,items,anchors,cap)
        heldout=[]
        for prompt in prompts:
            pid,_=self._encode(tok,prompt)
            with model.disable_adapter():
                seq=pid+self._greedy(torch,model,pid,16)
            if not seq:raise ValueError('empty heldout sequence')
            heldout.append(seq)
        heldout_kls=heldout_retention_kl(torch,model,heldout) if heldout else []
        # Measure retention against the frozen master on the SAME anchor sequences
        # used for training. This is a diagnostic, not deployment authority.
        # Recompute sequentially to bound peak memory on the mobile body path.
        retention_kl=(anchor_retention_kl(torch,model,anchor_seqs,anchor_logp)
                      if anchor_logp is not None else
                      heldout_retention_kl(torch,model,anchor_seqs))
        with torch.no_grad():
            st_ctx=last_token_latent(torch,model,ctx_b,layer)
            pc=pred(st_ctx);cos_pred_base=float(torch.nn.functional.cosine_similarity(pc,base_t,dim=-1).mean())
            with ema.swap():ema_t=last_token_latent(torch,model,tgt_b,layer)
            cos_pred_ema=float(torch.nn.functional.cosine_similarity(pc,ema_t,dim=-1).mean())
        rank={'base_target':effective_rank(base_t.numpy()),'ema_target':effective_rank(ema_t.numpy()),
              'base_context':effective_rank(base_ctx.numpy()),'student_context':effective_rank(st_ctx.numpy())}
        recall=[]
        for i in items:
            pid,_=self._encode(tok,i['prompt']);txt=tok.decode(self._greedy(torch,model,pid,48),skip_special_tokens=True)
            recall.append(answer_hit(txt,i.get('answer_keys') or [i['target']]))
        adapter=self._export(torch,model,out,lc)
        tmp=out/'predictor.pt';torch.save({'weight':pred.weight.detach(),'bias':pred.bias.detach(),'layer':layer,'mode':mode},tmp)
        metrics={'revision':REVISION,'objective':OBJECTIVE.objective_id,'dataset_hash':dh,'base_generation':base_generation,'steps':step,
                 'loss_history':hist,'final_ce':hist[-1]['ce'] if hist else None,'trainable_parameter_count':n_train,
                 'predictor_parameter_count':sum(p.numel() for p in pred.parameters()),'rank':int(cfg['rank']),'targets':list(cfg['targets']),
                 'anchor_weight':float(cfg['anchor_weight']),'jepa_weight':w_j,'jepa_target':mode,'jepa_ema_decay':float(cfg['jepa_ema_decay']),'jepa_target_eval':target_eval,
                 'lora_subspace':str(cfg.get('lora_subspace','none')),'subspace_info':sub,'jepa_layer':layer,'shuffle_perm':perm if mode=='shuffled' else None,'master_learned_recall':sum(recall)/len(recall),
                 'cos_pred_vs_base_target':round(cos_pred_base,5),'cos_pred_vs_ema_target':round(cos_pred_ema,5),
                 'anchor_reference_mode':anchor_mode,'anchor_cached_logit_bytes':anchor_cached_bytes,
                 'retention_anchor_count':len(retention_kl),'retention_anchor_kl_mean':round(sum(retention_kl)/len(retention_kl),7) if retention_kl else None,
                 'retention_anchor_kl_max':round(max(retention_kl),7) if retention_kl else None,
                 'retention_anchor_scope':'TRAINING_ANCHORS_NOT_HELDOUT',
                 'heldout_probe_scope':'EXACT_PROMPT_DISJOINT_ONLY',
                 'heldout_probe_cap':cap,'heldout_probe_count':len(heldout_kls),
                 'heldout_excluded_overlap':excluded,
                 'heldout_kl_mean':round(sum(heldout_kls)/len(heldout_kls),7) if heldout_kls else None,
                 'heldout_kl_max':round(max(heldout_kls),7) if heldout_kls else None,
                 'effective_rank':{k:round(v,3) for k,v in rank.items()},'ema_updates':ema.updates,'ema_delta':round(ema.delta(),6),'checkpoint_resume_enabled':checkpoint_dir is not None,'checkpoint_restored_step':restored_step,
                 'seconds':round(time.monotonic()-t0,2),'peak_rss_mb':_rss_mb(),'trained_on':self.deployed_base or 'master',
                 'device':{'backend':'torch-cpu','threads':int(cfg['threads']),'torch':torch.__version__}}
        result={'artifact':str(adapter['gguf']),'hash':adapter['gguf_sha256'],'method':self.method,'metrics':metrics,'files':adapter}
        self._deployed_eval(result,items,cancel,deadline)
        atomic_write(out/'manifest.json',json.dumps(result,indent=1,ensure_ascii=False))
        self.last=result;self.model=model;self.tok=tok;self.torch=torch
        return result
