#!/usr/bin/env python3
"""WP-LP1 (prereg docs/proofs/continuation-20261022/lp1-component-gradients/PREREG.md): does the latent (JEPA) term of
LoraTrainer reach the LoRA parameters, and does it help at equal budget against CE+KL alone and a wrongly assigned target?

  python3 scripts/lp1_component_gradients.py --master <HF dir LFM2.5-350M> --out <dir> [--seeds 13 7 21] [--steps 30]

Same objective pieces as v13/lora_trainer.LoraTrainer.fit (CE on the answer, KL-to-base anchors, cosine between the last
prompt state and the frozen mean base state of the target), but a fixed step count and separate per-component gradients.
Encoding goes through the prompt-boundary candidate (GPT PR #29). Nothing is exported, activated or approved.
"""
import argparse,json,sys,time
from pathlib import Path
APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP));sys.path.insert(0,str(APP/'scripts'))
from lora_bench import FACTS,PARAPHRASES,NEAR_MISS,ANCHORS,PROBES  # noqa: E402
from lora_prompt_boundary_candidate import PromptBoundLoraTrainer  # noqa: E402
from v13.lora_trainer import answer_hit  # noqa: E402
from v13.common import file_hash  # noqa: E402

LIVE={'rank':8,'alpha':16.,'lr':3e-4,'anchor_weight':8.,'anchors_per_step':16,'targets':['w1','w2','w3'],'max_tokens':160}
ARMS={'CE':(0.,None),'JEPA_OK':(1.,'own'),'JEPA_WRONG':(1.,'shift')}
GRAD_STEPS=(1,10,20,30)


def run_arm(master,arm,seed,steps,threads,work):
    import torch
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from peft import LoraConfig,get_peft_model
    torch.set_num_threads(threads);torch.manual_seed(seed)
    enc=PromptBoundLoraTrainer(master,work,cfg=dict(LIVE,seed=seed))
    tok=AutoTokenizer.from_pretrained(str(master));model=AutoModelForCausalLM.from_pretrained(str(master),dtype=torch.float32);model.eval()
    greedy=lambda m,ids,n:enc._greedy(torch,m,ids,n)
    def ask(m,q,n=24):
        pid,_=enc._encode(tok,q);return tok.decode(greedy(m,pid,n),skip_special_tokens=True)
    base_probe=[answer_hit(ask(model,p['prompt']),p['expect']) for p in PROBES]
    anchor_seqs=[]
    for a in ANCHORS:
        pid,_=enc._encode(tok,a);anchor_seqs.append(pid+greedy(model,pid,24))
    probe_seqs=[]
    for p in PROBES:
        pid,_=enc._encode(tok,p['prompt']);probe_seqs.append((len(pid),pid+greedy(model,pid,16)))
    with torch.no_grad():
        anchor_logp=[torch.log_softmax(model(torch.tensor([s])).logits[0].float(),-1) for s in anchor_seqs]
        probe_logp=[torch.log_softmax(model(torch.tensor([s])).logits[0].float(),-1) for _,s in probe_seqs]
    items=[{'prompt':q,'target':t,'keys':k} for q,t,k in FACTS]
    data=[enc._encode(tok,i['prompt'],i['target']) for i in items]
    last=lambda m,ids,hs=True:m(torch.tensor([ids]),output_hidden_states=hs).hidden_states[-1][0]
    with torch.no_grad():tgt=[last(model,tok(i['target'],add_special_tokens=False)['input_ids']).mean(0) for i in items]
    w,mode=ARMS[arm]
    tgt_used=tgt if mode!='shift' else [tgt[(k+1)%len(tgt)] for k in range(len(tgt))]
    lc=LoraConfig(r=LIVE['rank'],lora_alpha=LIVE['alpha'],lora_dropout=0.,target_modules=LIVE['targets'],bias='none')
    model=get_peft_model(model,lc);params=[p for p in model.parameters() if p.requires_grad]
    opt=torch.optim.AdamW(params,lr=LIVE['lr'],weight_decay=0.)
    plens=[next(j for j,v in enumerate(lab) if v!=-100) for _,lab in data]
    def cos_metric():
        with torch.no_grad():
            return sum(float(torch.nn.functional.cosine_similarity(last(model,ids[:pl])[-1],tg,dim=0)) for (ids,_),pl,tg in zip(data,plens,tgt))/len(data)
    def losses(pick,with_j=True):
        ce=0.;jl=0.
        for k,(ids,lab) in enumerate(data):
            o=model(torch.tensor([ids]),labels=torch.tensor([lab]),output_hidden_states=with_j)
            ce=ce+o.loss/len(data)
            if with_j:jl=jl+(1-torch.nn.functional.cosine_similarity(o.hidden_states[-1][0][plens[k]-1],tgt_used[k],dim=0))/len(data)
        kl=0.
        for j in pick:
            cl=torch.log_softmax(model(torch.tensor([anchor_seqs[j]])).logits[0].float(),-1);bl=anchor_logp[j]
            kl=kl+(bl.exp()*(bl-cl)).sum(-1).mean()/len(pick)
        return ce,kl,jl
    def gnorm(t):
        g=torch.autograd.grad(t,params,retain_graph=True,allow_unused=True)
        return torch.cat([(x if x is not None else torch.zeros_like(p)).reshape(-1) for x,p in zip(g,params)])
    cos_before=cos_metric();grads=[];hist=[];g=torch.Generator().manual_seed(seed);model.train()
    for step in range(1,steps+1):
        pick=torch.randperm(len(anchor_seqs),generator=g).tolist()[:LIVE['anchors_per_step']]
        ce,kl,jl=losses(pick)
        if step in GRAD_STEPS:
            gc,gk,gj=gnorm(ce),gnorm(kl),gnorm(jl)
            nc,nk,nj=float(gc.norm()),float(gk.norm()),float(gj.norm())
            eff_j=nj*(w if w else 1.);den=nc+nk*LIVE['anchor_weight']+eff_j
            grads.append({'step':step,'ce_norm':nc,'kl_norm':nk,'jepa_norm':nj,'jepa_weight':w,
                          'jepa_share_if_weighted':eff_j/den if den else 0.,'jepa_share_applied':(nj*w)/(nc+nk*LIVE['anchor_weight']+nj*w) if w else 0.,
                          'cos_ce_jepa':float(torch.nn.functional.cosine_similarity(gc,gj,dim=0)) if nc and nj else None})
        loss=ce+LIVE['anchor_weight']*kl+w*jl
        opt.zero_grad();loss.backward();opt.step()
        hist.append({'step':step,'ce':round(float(ce),5),'kl':round(float(kl),6),'jepa':round(float(jl),5)})
    model.eval()
    learned=sum(answer_hit(ask(model,i['prompt']),i['keys']) for i in items)
    para=sum(answer_hit(ask(model,q),k) for q,k in PARAPHRASES)
    leak=sum(answer_hit(ask(model,q),k) for q,k in NEAR_MISS)
    after_probe=[answer_hit(ask(model,p['prompt']),p['expect']) for p in PROBES]
    forgot=sum(1 for b,a in zip(base_probe,after_probe) if b and not a)
    with torch.no_grad():
        kls=[]
        for (pl,s),bl in zip(probe_seqs,probe_logp):
            cl=torch.log_softmax(model(torch.tensor([s])).logits[0].float(),-1)[pl-1:-1];b=bl[pl-1:-1]
            kls.append(float((b.exp()*(b-cl)).sum(-1).mean()))
    return {'arm':arm,'seed':seed,'steps':steps,'learned':learned,'para':para,'leak':leak,'forgot':forgot,
            'base_probe_correct':sum(base_probe),'kl_probe':sum(kls)/len(kls),'cos_before':cos_before,'cos_after':cos_metric(),
            'grads':grads,'history':hist}


def verdict(rows):
    S=lambda arm,k:sum(r[k] for r in rows if r['arm']==arm)
    ok=[r for r in rows if r['arm']=='JEPA_OK']
    h1=sum(1 for r in ok if r['grads'] and r['grads'][0]['jepa_share_applied']>=.05)>=2
    h2=(S('JEPA_OK','para')>=S('CE','para')+2 and S('JEPA_OK','para')>=S('JEPA_WRONG','para')+2
        and S('JEPA_OK','forgot')<=S('CE','forgot')+1 and S('JEPA_OK','leak')<=S('CE','leak')+1)
    hurts=S('JEPA_OK','para')<=S('CE','para')-2 or S('JEPA_OK','forgot')>=S('CE','forgot')+2
    v='LP1_TERM_DOES_NOT_REACH' if not h1 else 'LP1_JEPA_HELPS' if h2 else 'LP1_JEPA_HURTS' if hurts else 'LP1_NO_ATTRIBUTABLE_GAIN'
    return {'verdict':v,'H1':h1,'H2':h2,'sums':{a:{k:S(a,k) for k in ('learned','para','leak','forgot')} for a in ARMS}}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--master',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--seeds',type=int,nargs='+',default=[13,7,21]);ap.add_argument('--steps',type=int,default=30);ap.add_argument('--threads',type=int,default=4)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);rows=[]
    done=a.out/'rows.jsonl'
    if done.is_file():rows=[json.loads(x) for x in done.read_text().splitlines() if x.strip()]
    for seed in a.seeds:
        for arm in ARMS:
            if any(r['arm']==arm and r['seed']==seed for r in rows):continue
            t0=time.monotonic();r=run_arm(a.master,arm,seed,a.steps,a.threads,a.out/'work');r['seconds']=round(time.monotonic()-t0,1)
            rows.append(r)
            with done.open('a') as f:f.write(json.dumps(r)+'\n')
            print(json.dumps({k:r[k] for k in ('arm','seed','learned','para','leak','forgot','cos_before','cos_after','seconds')}),flush=True)
    st=a.master/'model.safetensors'
    rep={'prereg':'docs/proofs/continuation-20261022/lp1-component-gradients/PREREG.md','master_sha256':file_hash(st) if st.is_file() else None,
         'script_sha256':file_hash(Path(__file__)),'trainer_sha256':file_hash(APP/'v13/lora_trainer.py'),'cfg':LIVE,'rows':rows}|verdict(rows)
    (a.out/'report.json').write_text(json.dumps(rep,indent=1));print(json.dumps({k:rep[k] for k in ('verdict','H1','H2','sums')}))

if __name__=='__main__':main()
