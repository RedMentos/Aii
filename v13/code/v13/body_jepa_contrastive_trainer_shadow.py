"""Run12B isolated experimental 350M Body-JEPA contrastive trainer port.

Copied fit loop from frozen body_jepa.py blob b560d4e88fe457f381e89dfc5d6188a8ec3b306b
with one explicit contrastive loss substitution and no weight/predictor export.
This is research-only; it does not alter production BodyJepaTrainer or Age rights.
"""
from __future__ import annotations
import json
import time

from .body_jepa import (
    BodyJepaTrainer, MODES, EmaAdapter, pad, last_token_latent, make_predictor,
    minor_subspace_init, derangement, ema_target_latent, effective_rank,
)
from .body_jepa_contrastive_shadow import loss_and_metrics
from .lora_trainer import LoraTrainer, _check, _rss_mb, answer_hit
from .common import digest, dumps, atomic_write

REVISION = "v13-body-jepa-contrastive-trainer-run12b-shadow-v1"

class ContrastiveBodyJepaTrainer(BodyJepaTrainer):
    """Isolated CE + contrastive-EMA research fit, no export or Runtime consumer."""
    method = "lora-torch-cpu-bjepa-contrastive-shadow"
    _anchor_cache = {}

    def _export(self, torch, model, out, lc):
        return {"gguf": "NO_EXPORT", "gguf_sha256": None}

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
        torch,tok,model=self._load()
        from peft import LoraConfig,get_peft_model
        pad_id=tok.pad_token_id if tok.pad_token_id is not None else 0
        dh=digest(dumps([[i.get('memory_id'),i['prompt'],i['target']] for i in items]+[self.anchors,{k:v for k,v in cfg.items() if k!='threads'}]))[:24]
        out=self.work/dh;out.mkdir(parents=True,exist_ok=True)
        anchors=list(self.anchors)+self._locality_for(items,cfg)
        ck=(str(self.master),self.master_sha,tuple(anchors))
        if ck not in ContrastiveBodyJepaTrainer._anchor_cache:  # base continuations + log-probs are identical for every arm of one body
            anchor_seqs=[]
            for a in anchors:
                pid,_=self._encode(tok,a);anchor_seqs.append(pid+self._greedy(torch,model,pid,24))
            with torch.no_grad():anchor_logp=[torch.log_softmax(model(torch.tensor([s])).logits[0].float(),-1) for s in anchor_seqs]
            ContrastiveBodyJepaTrainer._anchor_cache[ck]=(anchor_seqs,anchor_logp)
        anchor_seqs,anchor_logp=ContrastiveBodyJepaTrainer._anchor_cache[ck]
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
                latent=pred(last_token_latent(torch,model,ctx_b,layer))
                target_latent=base_t if mode=='base' else ema_t_step
                jl,contrastive_metrics=loss_and_metrics(
                    torch,latent,target_latent,
                    temperature=float(cfg.get('contrastive_temperature',0.1)),
                    weights=torch.tensor(wts,dtype=latent.dtype),
                    permutation=perm if mode=='shuffled' else None)
                loss=loss+w_j*jl;jl_v=float(jl.detach())
            loss.backward();kl_sum=0.;pick=[]
            if anchor_seqs and float(cfg['anchor_weight'])>0:
                pick=torch.randperm(len(anchor_seqs),generator=g).tolist()[:int(cfg['anchors_per_step'])]
                for j in pick:
                    cl=torch.log_softmax(model(torch.tensor([anchor_seqs[j]])).logits[0].float(),-1);bl=anchor_logp[j]
                    kl=(bl.exp()*(bl-cl)).sum(-1).mean();(float(cfg['anchor_weight'])*kl/len(pick)).backward();kl_sum+=float(kl.detach())
            opt.step();ema.update();step+=1
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
        rank={'base_target':effective_rank(base_t.numpy()),'ema_target':effective_rank(ema_t.numpy()),
              'base_context':effective_rank(base_ctx.numpy()),'student_context':effective_rank(st_ctx.numpy())}
        recall=[]
        for i in items:
            pid,_=self._encode(tok,i['prompt']);txt=tok.decode(self._greedy(torch,model,pid,48),skip_special_tokens=True)
            recall.append(answer_hit(txt,i.get('answer_keys') or [i['target']]))
        adapter=self._export(torch,model,out,lc)
        # Research-only: never export the trained predictor or adapter.
        metrics={'revision':REVISION,'contrastive_temperature':float(cfg.get('contrastive_temperature',0.1)),'runtime_jepa_weight':0,'production_activation':False,'body_jepa_available':False,'objective':'B_JEPA_CONTRASTIVE_ALTERNATIVE_SHADOW_V1','dataset_hash':dh,'base_generation':base_generation,'steps':step,
                 'loss_history':hist,'final_ce':hist[-1]['ce'] if hist else None,'trainable_parameter_count':n_train,
                 'predictor_parameter_count':sum(p.numel() for p in pred.parameters()),'rank':int(cfg['rank']),'targets':list(cfg['targets']),
                 'anchor_weight':float(cfg['anchor_weight']),'jepa_weight':w_j,'jepa_target':mode,'jepa_ema_decay':float(cfg['jepa_ema_decay']),'jepa_target_eval':target_eval,
                 'lora_subspace':str(cfg.get('lora_subspace','none')),'subspace_info':sub,'jepa_layer':layer,'shuffle_perm':perm if mode=='shuffled' else None,'master_learned_recall':sum(recall)/len(recall),
                 'cos_pred_vs_base_target':round(cos_pred_base,5),'cos_pred_vs_ema_target':round(cos_pred_ema,5),
                 'effective_rank':{k:round(v,3) for k,v in rank.items()},'ema_updates':ema.updates,'ema_delta':round(ema.delta(),6),'checkpoint_resume_enabled':checkpoint_dir is not None,'checkpoint_restored_step':restored_step,
                 'seconds':round(time.monotonic()-t0,2),'peak_rss_mb':_rss_mb(),'trained_on':self.deployed_base or 'master',
                 'device':{'backend':'torch-cpu','threads':int(cfg['threads']),'torch':torch.__version__}}
        result={'artifact':str(adapter['gguf']),'hash':adapter['gguf_sha256'],'method':self.method,'metrics':metrics,'files':adapter}
        atomic_write(out/'manifest.json',json.dumps(result,indent=1,ensure_ascii=False))
        self.last=result;self.model=model;self.tok=tok;self.torch=torch
        return result
