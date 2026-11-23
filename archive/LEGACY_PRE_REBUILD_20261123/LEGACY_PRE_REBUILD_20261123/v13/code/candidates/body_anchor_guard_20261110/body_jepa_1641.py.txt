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
        if not isinstance(decay,(float,int)) or not math.isfinite(decay) or not 0<=decay<1:
            raise ValueError('decay must be finite and in [0,1)')
        self.params=list(params);self.decay=float(decay);self.shadow=[p.detach().clone() for p in self.params];self.updates=0
    def _validate(self):
        if len(self.shadow)!=len(self.params):
            raise ValueError('EMA parameter count changed')
        for s,p in zip(self.shadow,self.params):
            if s.shape!=p.shape or s.device!=p.device or s.dtype!=p.dtype:
                raise ValueError('EMA parameter metadata changed')
    def update(self):
        """Atomically advance the EMA only when every proposed tensor is finite.

        A failed update must leave the previous target and counter unchanged:
        otherwise subsequent target passes can silently poison body learning.
        """
        import torch
        self._validate()
        with torch.no_grad():
            proposed = []
            for s, p in zip(self.shadow, self.params):
                if not bool(torch.isfinite(s).all()) or not bool(torch.isfinite(p).all()):
                    raise ValueError('nonfinite EMA source or target')
                candidate = s * self.decay + p.detach() * (1 - self.decay)
                if not bool(torch.isfinite(candidate).all()):
                    raise ValueError('nonfinite proposed EMA update')
                proposed.append(candidate)
            # No live shadow is modified before all candidates are validated.
            for s, candidate in zip(self.shadow, proposed):
                s.copy_(candidate)
        self.updates += 1
    def delta(self):
        """L2 distance EMA vs student over all adapter tensors."""
        return float(sum(float((s-p.detach()).pow(2).sum()) for s,p in zip(self.shadow,self.params))**.5)
    def swap(self):
        ema=self
        class _Swap:
            def __enter__(self):
                import torch
                ema._validate()
                self.keep=[p.detach().clone() for p in ema.params]
                try:
                    with torch.no_grad():
                        for s,p in zip(ema.shadow,ema.params):p.copy_(s)
                except BaseException:
                    # Context manager __exit__ is NOT invoked if __enter__ fails.
                    # A failed later copy must not leave earlier student weights replaced.
                    with torch.no_grad():
                        for k,p in zip(self.keep,ema.params):p.copy_(k)
                    raise
                return self
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
    if (ids.ndim!=2 or lens.ndim!=1 or ids.dtype!=torch.long or lens.dtype!=torch.long
            or len(lens)!=ids.shape[0] or ids.shape[1]<1
            or not bool(torch.all((lens>=1)&(lens<=ids.shape[1])))):
        raise ValueError('nonempty right-padded token sequences required')
    # Token IDs, attention mask and advanced-index tensors must share the
    # actual model/input device. CPU-only tests previously hid this CUDA failure.
    # Lengths are metadata and may arrive on CPU from the collator.
    if lens.device != ids.device:
        lens = lens.to(device=ids.device)
    att=(torch.arange(ids.shape[1],device=ids.device)[None,:]<lens[:,None]).long()
    out=model(input_ids=ids,attention_mask=att,output_hidden_states=True)
    h=out.hidden_states[layer]
    if h.device != ids.device:
        raise ValueError('body latent device differs from token input device')
    return h[torch.arange(len(lens),device=h.device),lens-1]

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


def validated_weights(items):
    """Fail before loading the large body when eligibility is invalid."""
    try:
        weights=[float(item.get('weight',1.)) for item in items]
    except (TypeError,ValueError,OverflowError):
        raise ValueError('invalid eligibility weights') from None
    if not weights or not all(math.isfinite(v) and v>=0 for v in weights):
        raise ValueError('eligibility weights must be finite, nonnegative and positive in total')
    # Each weight may be finite while their aggregate overflows.  Such a batch
    # otherwise yields inf denominators and silently zeroes the learning signal.
    try:
        total = math.fsum(weights)
    except OverflowError:
        raise ValueError('eligibility weight sum overflow') from None
    if not math.isfinite(total) or total <= 0:
        raise ValueError('eligibility weights must have a finite positive total')
    return weights

def pad(torch,seqs,pad_id=0,device=None):
    if (not seqs or any(not isinstance(s,(list,tuple)) or not s for s in seqs)
            or any(type(token) is not int or token < 0 for s in seqs for token in s)
            or type(pad_id) is not int or pad_id < 0):
        raise ValueError('nonempty nonnegative integer token sequences required')
    n=max(len(s) for s in seqs);ids=torch.full((len(seqs),n),pad_id,dtype=torch.long,device=device)
    for i,s in enumerate(seqs):ids[i,:len(s)]=torch.tensor(s,dtype=torch.long,device=device)
    return ids,torch.tensor([len(s) for s in seqs],dtype=torch.long,device=device)

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

def checked_gradient_step(torch,params,opt,max_norm=None):
    """Reject nonfinite/missing body gradients before AdamW can corrupt a candidate.

    Optional clipping is an explicit experiment setting; the registered default
    optimizer path is unchanged for finite gradients.
    """
    grads=[p.grad for p in params if p.requires_grad and p.grad is not None]
    if not grads:
        raise ValueError('body JEPA step has no trainable gradients')
    if not all(bool(torch.isfinite(g).all()) for g in grads):
        raise ValueError('body JEPA step has nonfinite gradients')
    if max_norm is not None:
        if type(max_norm) not in (int,float) or not math.isfinite(max_norm) or max_norm<=0:
            raise ValueError('grad_clip_norm must be finite and positive')
        norm=torch.nn.utils.clip_grad_norm_(params,float(max_norm),error_if_nonfinite=True)
        if not bool(torch.isfinite(norm)):
            raise ValueError('nonfinite body gradient norm')
    opt.step()


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
                mod.lora_A['default'].weight.copy_(low.to(device=mod.lora_A['default'].weight.device,dtype=mod.lora_A['default'].weight.dtype));mod.lora_A['default'].weight.requires_grad_(False);mod.lora_B['default'].weight.zero_()
            else:
                low=evecs[:,:r].float().contiguous()  # out x r
                mod.lora_B['default'].weight.copy_(low.to(device=mod.lora_B['default'].weight.device,dtype=mod.lora_B['default'].weight.dtype));mod.lora_B['default'].weight.requires_grad_(False);mod.lora_A['default'].weight.zero_()
            share.append(float(singular[:r].sum()/mass))
        n+=1;frozen+=int(low.numel())
    return {'modules':n,'frozen_side_params':frozen,'mean_low_singular_mass_share':round(sum(share)/max(1,len(share)),6)}

def anchor_retention_kl(torch, model, anchor_seqs, anchor_logp):
    """Deterministic mean KL(frozen base || candidate) on identical anchor tokens.

    The frozen reference must be a normalized log-probability distribution.
    Evaluation restores all mixed train/eval flags, including on failure.
    """
    if len(anchor_seqs) != len(anchor_logp):
        raise ValueError('retention anchor/logprob mismatch')
    if not anchor_seqs:
        return None
    modules = list(model.modules()) if hasattr(model, 'modules') else []
    flags = [module.training for module in modules]
    values = []
    try:
        if modules:
            model.eval()
        with torch.no_grad():
            for seq, base in zip(anchor_seqs, anchor_logp):
                if not seq or base.ndim != 2:
                    raise ValueError('invalid retention anchor')
                if not bool(torch.isfinite(base).all()):
                    raise ValueError('nonfinite retention reference')
                # A finite tensor is not necessarily a valid probability law.
                # Do not silently renormalize corrupted frozen references.
                if not bool(torch.all(torch.abs(torch.logsumexp(base.float(), -1)) <= 1e-4)):
                    raise ValueError('unnormalized retention reference')
                # The frozen reference may be cached on CPU while the LoRA
                # candidate resides on an accelerator. Keep the input on the
                # candidate's device and compare distributions on one device.
                param = next(model.parameters(), None) if hasattr(model, 'parameters') else None
                device = param.device if param is not None else base.device
                logits = model(torch.tensor([seq], dtype=torch.long, device=device)).logits[0].float()
                if logits.shape != base.shape or not bool(torch.isfinite(logits).all()):
                    raise ValueError('invalid retention logits')
                reference = base.to(device=logits.device, dtype=logits.dtype)
                logp = torch.log_softmax(logits, -1)
                value = (reference.exp() * (reference - logp)).sum(-1).mean()
                if not bool(torch.isfinite(value)):
                    raise ValueError('nonfinite retention KL')
                values.append(float(value))
    finally:
        if modules:
            model.train(flags[0])
        for module, flag in zip(modules, flags):
            module.training = flag
    return round(sum(values) / len(values), 8)


# -- trainer ---------------------------------------------------------------------------------------------
from .lora_trainer import LoraTrainer,DEFAULTS as _LORA_DEFAULTS,_check,_rss_mb,answer_hit
from .common import digest,dumps,atomic_write

REVISION='v13-body-jepa-trainer-v1'
DEFAULTS=dict(_LORA_DEFAULTS,jepa_weight=.5,jepa_target='ema',jepa_ema_decay=.9,jepa_layer=-1,max_steps=30,min_steps=30,lr=5e-4)

class BodyJepaTrainer(LoraTrainer):
    """LoRA body trainer with the §13 B-JEPA term (EMA adapter target + predictor) next to answer CE and KL anchors.
    Same fit()/export contract as LoraTrainer, so AG6 can use it as a trainer; one step = one batched pass over all
    items (right padding, causal body). jepa_weight 0 gives the CE+anchor baseline on exactly the same loop."""
    method='lora-torch-cpu-bjepa'
    # Bounded cache of frozen-reference CPU tensors only. Never retain an entire
    # accelerator graph/model output across trainer instances or experiment arms.
    _anchor_cache={}
    _anchor_cache_limit=2
    _anchor_cache_bytes_limit=32*1024*1024
    @classmethod
    def _cache_anchors(cls,key,seqs,logps):
        """Keep a bounded, detached CPU snapshot; never share mutable references."""
        cache=cls._anchor_cache
        cache.pop(key,None)  # refresh insertion order on replacement
        snapshot=(tuple(tuple(s) for s in seqs),
                  tuple(p.detach().cpu().clone() for p in logps))
        size=sum(p.numel()*p.element_size() for p in snapshot[1])
        # A large vocabulary x long-anchor matrix can exceed phone RAM even
        # with only two entries. Keep the current batch usable but uncached.
        if size>cls._anchor_cache_bytes_limit:
            return [list(s) for s in snapshot[0]],[p.clone() for p in snapshot[1]]
        cache[key]=snapshot
        while (len(cache)>cls._anchor_cache_limit or
               sum(p.numel()*p.element_size() for _,logs in cache.values() for p in logs)>cls._anchor_cache_bytes_limit):
            cache.pop(next(iter(cache)))
        return cls._cached_anchors(key)

    @classmethod
    def _cached_anchors(cls,key):
        seqs,logps=cls._anchor_cache[key]
        return [list(s) for s in seqs],[p.clone() for p in logps]

    def __init__(self,*a,cfg=None,**k):
        super().__init__(*a,cfg=dict(DEFAULTS,**(cfg or {})),**k)
    @staticmethod
    def _greedy(torch,model,ids,n):
        """Body-local generation: parent LoraTrainer assumes CPU inputs."""
        device=next(model.parameters()).device
        tokens=torch.tensor([ids],dtype=torch.long,device=device)
        mask=torch.ones_like(tokens)
        with torch.no_grad():
            out=model.generate(tokens,attention_mask=mask,max_new_tokens=n,do_sample=False,pad_token_id=0)
        return out[0][len(ids):].detach().cpu().tolist()

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
    def fit(self,items,base_generation,cancel=None,deadline=None):
        if not items:return {'artifact':None,'hash':None,'method':self.method,'metrics':{'reason':'EMPTY_BATCH'}}
        try:import torch,peft  # noqa: F401
        except ImportError:return {'artifact':None,'hash':None,'method':self.method,'metrics':{'reason':'NO_TORCH_PEFT'}}
        import numpy as np
        t0=time.monotonic();cfg=self.cfg;mode=str(cfg['jepa_target']);w_j=float(cfg['jepa_weight']);layer=int(cfg['jepa_layer'])
        target_eval=cfg.get('jepa_target_eval',False)
        if type(target_eval) is not bool:raise ValueError('jepa_target_eval must be bool')
        if mode not in MODES:raise ValueError('unknown jepa_target')
        if cfg.get('locality_policy','legacy') not in ('legacy','bp2b'):raise ValueError('unknown locality_policy')
        wts=validated_weights(items)
        clip=cfg.get('grad_clip_norm')
        if clip is not None and (type(clip) not in (float,int) or not math.isfinite(clip) or clip<=0):
            raise ValueError('grad_clip_norm must be finite and positive')
        torch,tok,model=self._load()
        from peft import LoraConfig,get_peft_model
        pad_id=tok.pad_token_id if tok.pad_token_id is not None else 0
        model_device=next(model.parameters()).device
        dh=digest(dumps([[i.get('memory_id'),i['prompt'],i['target']] for i in items]+[self.anchors,{k:v for k,v in cfg.items() if k!='threads'}]))[:24]
        out=self.work/dh;out.mkdir(parents=True,exist_ok=True)
        anchors=list(self.anchors)+self._locality_for(items,cfg)
        ck=(str(self.master),self.master_sha,tuple(anchors))
        if ck not in BodyJepaTrainer._anchor_cache:  # base continuations + log-probs are identical for every arm of one body
            anchor_seqs=[]
            for a in anchors:
                pid,_=self._encode(tok,a);anchor_seqs.append(pid+self._greedy(torch,model,pid,24))
            with torch.no_grad():anchor_logp=[torch.log_softmax(model(torch.tensor([s],dtype=torch.long,device=model_device)).logits[0].float(),-1) for s in anchor_seqs]
            anchor_seqs,anchor_logp=BodyJepaTrainer._cache_anchors(ck,anchor_seqs,anchor_logp)
        else:
            anchor_seqs,anchor_logp=BodyJepaTrainer._cached_anchors(ck)
        data=[self._encode(tok,i['prompt'],i['target']) for i in items]
        ctx,tgt=self._views(tok,items);ctx_b=pad(torch,ctx,pad_id,device=model_device);tgt_b=pad(torch,tgt,pad_id,device=model_device)
        with torch.no_grad():
            base_t=last_token_latent(torch,model,tgt_b,layer).detach()
            base_ctx=last_token_latent(torch,model,ctx_b,layer).detach()
        lc=LoraConfig(r=int(cfg['rank']),lora_alpha=float(cfg['alpha']),lora_dropout=0.,target_modules=list(cfg['targets']),bias='none')
        model=get_peft_model(model,lc)
        sub=minor_subspace_init(torch,model,int(cfg['rank'])) if str(cfg.get('lora_subspace','none'))=='minor' else None
        params=[p for p in model.parameters() if p.requires_grad];n_train=sum(p.numel() for p in params)
        dim=int(base_t.shape[-1]);pred=make_predictor(torch,dim).to(device=model_device)
        ema=EmaAdapter(params,float(cfg['jepa_ema_decay']))
        opt=torch.optim.AdamW(params+list(pred.parameters()),lr=float(cfg['lr']),weight_decay=float(cfg['weight_decay']))
        rng=np.random.default_rng(int(cfg['seed']));perm=derangement(len(items),rng) if len(items)>1 else None
        if mode=='shuffled' and perm is None:raise ValueError('shuffled control needs two items')
        ids_b,lens=pad(torch,[d[0] for d in data],pad_id,device=model_device)
        lab_b=torch.full(ids_b.shape,-100,dtype=torch.long,device=model_device)
        for r,(ids,lab) in enumerate(data):lab_b[r,:len(lab)]=torch.tensor(lab,dtype=torch.long,device=model_device)
        att=(torch.arange(ids_b.shape[1],device=model_device)[None,:]<lens[:,None]).long()
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
            w=torch.tensor(wts,dtype=per.dtype,device=per.device);ce=(per*w).sum()/w.sum();loss=ce;jl_v=None
            if w_j>0:
                jl,_=jepa_loss(torch,model,pred,ctx_b,tgt_b,mode,ema=ema,base_targets=base_t if mode=='base' else ema_t_step,perm=perm,weights=wts,layer=layer)
                loss=loss+w_j*jl;jl_v=float(jl.detach())
            loss.backward();kl_sum=0.;pick=[]
            if anchor_seqs and float(cfg['anchor_weight'])>0:
                pick=torch.randperm(len(anchor_seqs),generator=g).tolist()[:int(cfg['anchors_per_step'])]
                for j in pick:
                    cl=torch.log_softmax(model(torch.tensor([anchor_seqs[j]],dtype=torch.long,device=model_device)).logits[0].float(),-1);bl=anchor_logp[j].to(device=cl.device,dtype=cl.dtype)
                    kl=(bl.exp()*(bl-cl)).sum(-1).mean();(float(cfg['anchor_weight'])*kl/len(pick)).backward();kl_sum+=float(kl.detach())
            checked_gradient_step(torch,params+list(pred.parameters()),opt,cfg.get('grad_clip_norm'))
            ema.update();step+=1
            hist.append({'step':step,'ce':round(float(ce.detach()),5),'anchor_kl':round(kl_sum/max(1,len(pick)),6),'jepa':None if jl_v is None else round(jl_v,5),'ema_delta':round(ema.delta(),6)})
            if checkpoint_dir is not None:
                from .body_jepa_checkpoint import save as save_bj_step
                save_bj_step(checkpoint_dir,checkpoint_source,step,model,pred,opt,ema,g,hist)
            if step>=int(cfg['min_steps']) and hist[-1]['ce']<=float(cfg['target_loss']):break
        model.eval()
        with torch.no_grad():
            st_ctx=last_token_latent(torch,model,ctx_b,layer)
            pc=pred(st_ctx);cos_pred_base=float(torch.nn.functional.cosine_similarity(pc,base_t,dim=-1).mean())
            with ema.swap():ema_t=last_token_latent(torch,model,tgt_b,layer)
            cos_pred_ema=float(torch.nn.functional.cosine_similarity(pc,ema_t,dim=-1).mean())
        # Read-only final retention on the original frozen-base anchor distributions.
        # This is a measured candidate metric, never an Age or deployment gate.
        final_anchor_kl = anchor_retention_kl(torch, model, anchor_seqs, anchor_logp)
        rank={'base_target':effective_rank(base_t.detach().cpu().numpy()),'ema_target':effective_rank(ema_t.detach().cpu().numpy()),
              'base_context':effective_rank(base_ctx.detach().cpu().numpy()),'student_context':effective_rank(st_ctx.detach().cpu().numpy())}
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
                 'effective_rank':{k:round(v,3) for k,v in rank.items()},'ema_updates':ema.updates,'ema_delta':round(ema.delta(),6),'final_anchor_kl':final_anchor_kl,'retention_probe_count':len(anchor_seqs),'checkpoint_resume_enabled':checkpoint_dir is not None,'checkpoint_restored_step':restored_step,
                 'seconds':round(time.monotonic()-t0,2),'peak_rss_mb':_rss_mb(),'trained_on':self.deployed_base or 'master',
                 'device':{'backend':'torch-cpu','threads':int(cfg['threads']),'torch':torch.__version__}}
        result={'artifact':str(adapter['gguf']),'hash':adapter['gguf_sha256'],'method':self.method,'metrics':metrics,'files':adapter}
        atomic_write(out/'manifest.json',json.dumps(result,indent=1,ensure_ascii=False))
        self.last=result;self.model=model;self.tok=tok;self.torch=torch
        return result
