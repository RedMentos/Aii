#!/usr/bin/env python3
"""WP-LP3 (prereg docs/proofs/continuation-20261022/lp3-memory-key/PREREG.md): make the C3 answer DEPEND on the
predicted latent state. The LP2 predictor output is used as a memory key: it picks one stored fact note among the 16
(keys = frozen base answer states, the LP2 probe), the note is put in front of the question, and LoRA is trained on
the noted prompt. Measured on new, harder paraphrases, with an intervention test (swap the retrieved note) for dependence.

  python3 scripts/lp3_memory_key.py --master <HF dir LFM2.5-350M> --out <dir> [--seeds 47 53 59 61] [--steps 30]

Arms: CE (LP2 baseline, no memory) · MEM_OK (predictor trained toward the own item, as LP2 NCE_OK) · MEM_SHUF (predictor
trained toward item k+1, so it retrieves the wrong note) · MEM_RAW (memory path, predictor not trained: raw prompt state
as key). Nothing is exported, activated or approved.
"""
import argparse,json,sys,time
from pathlib import Path
APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP));sys.path.insert(0,str(APP/'scripts'))
from lp2_assignment_objective import FACTS,HELDOUT,NEAR_MISS,LIVE,LP2,PARA_V1,ANCHORS,PROBES  # noqa: E402
from lora_prompt_boundary_candidate import PromptBoundLoraTrainer  # noqa: E402
from v13.lora_trainer import answer_hit  # noqa: E402
from v13.common import file_hash  # noqa: E402

# New, harder paraphrases (2 per fact, indirect wording). Disjoint from FACTS prompts, HELDOUT, PARA_V1, NEAR_MISS.
HARD=[
 (0,'Remind me what my cat is called.'),(0,'I forgot the name I gave my kitty. What was it?'),
 (1,'Remind me of the bakery where I have my job.'),(1,'Where do I go every morning for my job?'),
 (2,'Remind me which colour I like best.'),(2,'What colour should I paint my room if I want my favourite one?'),
 (3,"Remind me of my brother's first name."),(3,'My parents have another son besides me. What is his name?'),
 (4,'Which musical instrument do I practise?'),(4,'What do I play in my free time, music-wise?'),
 (5,'Remind me which smartphone I own.'),(5,'What is the make of my mobile?'),
 (6,"Remind me of my project's title."),(6,'What did I call the project I am working on?'),
 (7,'Remind me of my birthday, day and month.'),(7,'On which day should my friends congratulate me on my birthday?'),
 (8,'Remind me what my horse is called.'),(8,'What name did I give the horse I ride?'),
 (9,'Remind me which city I live in since my move.'),(9,'To which town did I relocate last year?'),
 (10,"Remind me of my granny's name."),(10,'Tell me the first name of my grandmother.'),
 (11,"Remind me of my boat's name."),(11,'Which name is painted on my boat?'),
 (12,'Remind me which language I am currently studying.'),(12,'What new language am I trying to learn?'),
 (13,'Remind me of my locker number.'),(13,'I need to open my locker. Which number was it?'),
 (14,'Remind me what my band is called.'),(14,'Under which name does my band perform?'),
 (15,'Remind me which tree I planted.'),(15,'What kind of tree did I put in my garden?'),
]
# The 5 questions every LP2 arm failed (secondary, reported per arm).
FIXED_FAIL=['Where is my workplace?','Which bakery do I work at?','Which phone do I have?','What kind of phone do I use?',
            'Which number does my locker have?']
NOTE='Memory note: {note}\n\n{q}'
GATE_P=.6  # secondary only: inject the note only if the top-1 softmax weight (T = LP2 temperature) is at least this
ARMS={'CE':(0.,None),'MEM_OK':(LP2['nce_weight'],'own'),'MEM_SHUF':(LP2['nce_weight'],'shift'),'MEM_RAW':(0.,'own')}


def run_arm(master,arm,seed,steps,threads,work):
    import torch
    import torch.nn.functional as F
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from peft import LoraConfig,get_peft_model
    torch.set_num_threads(threads);torch.manual_seed(seed)
    enc=PromptBoundLoraTrainer(master,work,cfg=dict(LIVE,seed=seed))
    tok=AutoTokenizer.from_pretrained(str(master));model=AutoModelForCausalLM.from_pretrained(str(master),dtype=torch.float32);model.eval()
    greedy=lambda m,ids,n:enc._greedy(torch,m,ids,n)
    items=[{'prompt':q,'target':t,'keys':k} for q,t,k in FACTS];N=len(items)
    w,mode=ARMS[arm];memory=mode is not None;perm=list(range(N)) if mode!='shift' else [(k+1)%N for k in range(N)]
    noted=lambda q,j:NOTE.format(note=items[j]['target'],q=q)
    last=lambda m,ids:m(torch.tensor([ids]),output_hidden_states=True).hidden_states[-1][0]
    tids=[tok(i['target'],add_special_tokens=False)['input_ids'] for i in items]
    with torch.no_grad():base_bank=torch.stack([last(model,t).mean(0) for t in tids])
    D=base_bank.shape[1];H=LP2['pred_hidden']
    pred=torch.nn.Sequential(torch.nn.LayerNorm(D),torch.nn.Linear(D,H),torch.nn.GELU(),torch.nn.Linear(H,D))
    torch.nn.init.zeros_(pred[3].weight);torch.nn.init.zeros_(pred[3].bias)  # identity at start, as LP2
    P=lambda h:h+pred(h)
    sims=lambda z:F.normalize(z,dim=-1)@F.normalize(base_bank,dim=-1).T
    def key(m,q):
        with torch.no_grad():
            s=sims(P(last(m,enc._encode(tok,q)[0])[-1]))
        return int(s.argmax()),float(torch.softmax(s/LP2['temperature'],-1).max())
    def ask(m,q,note=None,n=24):
        pid,_=enc._encode(tok,q if note is None else noted(q,note));return tok.decode(greedy(m,pid,n),skip_special_tokens=True)
    def answer(m,q,k=None):
        """Full system answer. CE: plain question. Memory arms: retrieved note (+ swap / oracle / gated variants for item k)."""
        if not memory:return {'ret':ask(m,q)}
        top,p=key(m,q);r={'top':top,'p':p,'ret':ask(m,q,top)}
        if k is not None:r['swap']=ask(m,q,(top+1)%N);r['oracle']=ask(m,q,k)
        r['gated']=r['ret'] if p>=GATE_P else ask(m,q)
        return r
    # base-model reference for drift (bare prompts, before any adapter)
    base_probe=[answer_hit(ask(model,p['prompt']),p['expect']) for p in PROBES]
    anchor_seqs=[]
    for a in ANCHORS:
        pid,_=enc._encode(tok,a);anchor_seqs.append(pid+greedy(model,pid,24))
    probe_cont=[]
    for p in PROBES:
        pid,_=enc._encode(tok,p['prompt']);probe_cont.append((pid,greedy(model,pid,16)))
    with torch.no_grad():
        anchor_logp=[torch.log_softmax(model(torch.tensor([s])).logits[0].float(),-1) for s in anchor_seqs]
        probe_logp=[torch.log_softmax(model(torch.tensor([pid+c])).logits[0].float(),-1)[len(pid)-1:-1] for pid,c in probe_cont]
    def retrieval(m,qs):
        tops=[key(m,q)[0] for _,q in qs]
        return {'own':sum(t==k for (k,_),t in zip(qs,tops))/len(qs),'shifted':sum(t==(k+1)%N for (k,_),t in zip(qs,tops))/len(qs)}
    ret_before={'heldout':retrieval(model,HELDOUT),'hard':retrieval(model,HARD)}
    lc=LoraConfig(r=LIVE['rank'],lora_alpha=LIVE['alpha'],lora_dropout=0.,target_modules=LIVE['targets'],bias='none')
    model=get_peft_model(model,lc);params=[p for p in model.parameters() if p.requires_grad]
    opt=torch.optim.AdamW([{'params':params,'lr':LIVE['lr']},{'params':list(pred.parameters()),'lr':LP2['pred_lr']}],weight_decay=0.)
    slow=base_bank.clone()
    bare=[enc._encode(tok,i['prompt'])[0] for i in items]
    def nce(zq,bank,labels):
        return F.cross_entropy(F.normalize(zq,dim=-1)@F.normalize(bank,dim=-1).T/LP2['temperature'],torch.tensor(labels))
    hist=[];g=torch.Generator().manual_seed(seed);model.train()
    for step in range(1,steps+1):
        pick=torch.randperm(len(anchor_seqs),generator=g).tolist()[:LIVE['anchors_per_step']]
        zq=P(torch.stack([last(model,ids)[-1] for ids in bare]));nl=nce(zq,slow,perm)
        tops=sims(zq.detach()).argmax(-1).tolist()  # train-time retrieval = what the key picks right now (no oracle)
        ce=0.
        for k,i in enumerate(items):
            ids,lab=enc._encode(tok,noted(i['prompt'],tops[k]) if memory else i['prompt'],i['target'])
            ce=ce+model(torch.tensor([ids]),labels=torch.tensor([lab])).loss/N
        kl=0.
        for j in pick:
            cl=torch.log_softmax(model(torch.tensor([anchor_seqs[j]])).logits[0].float(),-1);bl=anchor_logp[j]
            kl=kl+(bl.exp()*(bl-cl)).sum(-1).mean()/len(pick)
        loss=ce+LIVE['anchor_weight']*kl+w*nl
        opt.zero_grad();loss.backward();opt.step()
        if w:
            model.eval()
            with torch.no_grad():cur=torch.stack([last(model,t).mean(0) for t in tids])
            model.train();slow=LP2['ema_tau']*slow+(1-LP2['ema_tau'])*cur
        hist.append({'step':step,'ce':round(float(ce),5),'kl':round(float(kl),6),'nce':round(float(nl.detach()),5),
                     'train_ret_own':sum(t==k for k,t in enumerate(tops))/N})
    model.eval()
    hits=lambda rs,qs,v,keyf=lambda k:items[k]['keys']:[int(answer_hit(r[v],keyf(k))) for r,(k,_) in zip(rs,qs)]
    out={'arm':arm,'seed':seed,'steps':steps,'retrieval_before':ret_before,
         'retrieval_after':{'heldout':retrieval(model,HELDOUT),'hard':retrieval(model,HARD)},'history':hist}
    out['learned']=sum(answer_hit(answer(model,i['prompt'])['ret'],i['keys']) for i in items)
    for name,qs in (('hard',HARD),('heldout',HELDOUT)):
        rs=[answer(model,q,k) for k,q in qs]
        out[name+'_hits']=hits(rs,qs,'ret');out[name]=sum(out[name+'_hits'])
        if memory:
            out[name+'_swap']=sum(hits(rs,qs,'swap'))
            out[name+'_swap_follow']=sum(int(answer_hit(r['swap'],items[(r['top']+1)%N]['keys'])) for r in rs)
            out[name+'_oracle']=sum(hits(rs,qs,'oracle'));out[name+'_gated']=sum(hits(rs,qs,'gated'))
            out[name+'_tops']=[r['top'] for r in rs]
        if name=='hard':out['hard_answers']=[r['ret'][:120] for r in rs]
    out['fixed_fail']=sum(answer_hit(answer(model,q)['ret'],items[k]['keys']) for k,q in HELDOUT if q in FIXED_FAIL)
    out['para_v1']=sum(answer_hit(answer(model,q)['ret'],k) for q,k in PARA_V1)
    nm=[answer(model,q) for q,_ in NEAR_MISS]
    out['leak']=sum(answer_hit(r['ret'],k) for r,(_,k) in zip(nm,NEAR_MISS))
    out['leak_gated']=sum(answer_hit(r.get('gated',r['ret']),k) for r,(_,k) in zip(nm,NEAR_MISS))
    pr=[answer(model,p['prompt']) for p in PROBES]
    out['forgot']=sum(1 for b,r,p in zip(base_probe,pr,PROBES) if b and not answer_hit(r['ret'],p['expect']))
    out['base_probe_correct']=sum(base_probe)
    with torch.no_grad():  # drift of the full system: same base continuation, scored under the (noted) prompt it now sees
        kls=[];bare_kls=[]
        for (pid,c),bl,r,p in zip(probe_cont,probe_logp,pr,PROBES):
            npid=enc._encode(tok,noted(p['prompt'],r['top']) if memory else p['prompt'])[0]
            cl=torch.log_softmax(model(torch.tensor([npid+c])).logits[0].float(),-1)[len(npid)-1:-1]
            kls.append(float((bl.exp()*(bl-cl)).sum(-1).mean()))
            cl=torch.log_softmax(model(torch.tensor([pid+c])).logits[0].float(),-1)[len(pid)-1:-1]  # adapter only, bare prompt
            bare_kls.append(float((bl.exp()*(bl-cl)).sum(-1).mean()))
    out['kl_probe']=sum(kls)/len(kls);out['kl_probe_bare']=sum(bare_kls)/len(bare_kls)
    return out


def verdict(rows):
    S=lambda arm,k:sum(r[k] for r in rows if r['arm']==arm)
    seeds=sorted({r['seed'] for r in rows});by={(r['arm'],r['seed']):r for r in rows};n=len(seeds)
    mean=lambda xs:sum(xs)/len(xs) if xs else 0.
    ok=[r for r in rows if r['arm']=='MEM_OK']
    r_ok=mean([r['retrieval_after']['hard']['own'] for r in ok])
    h1=r_ok>=.8
    wins=lambda other:sum(1 for s in seeds if by[('MEM_OK',s)]['hard']>=by[(other,s)]['hard'])
    h2=(S('MEM_OK','hard')>=S('CE','hard')+6 and S('MEM_OK','hard')>=S('MEM_RAW','hard')+6
        and wins('CE')>=n-1 and wins('MEM_RAW')>=n-1)
    drop=1-S('MEM_OK','hard_swap')/max(1,S('MEM_OK','hard'));follow=S('MEM_OK','hard_swap_follow')/(32*n)
    h3=drop>=.5 and follow>=.5
    kl_ok=mean([r['kl_probe_bare'] for r in ok]);kl_ce=mean([r['kl_probe_bare'] for r in rows if r['arm']=='CE'])
    leak_ok=S('MEM_OK','leak')<=S('CE','leak')+2
    drift_ok=S('MEM_OK','forgot')<=S('CE','forgot')+1 and kl_ok<=1.5*kl_ce
    hurts=S('MEM_OK','hard')<=S('CE','hard')-6 or S('MEM_OK','forgot')>=S('CE','forgot')+2
    if not h1:v='LP3_NO_RETRIEVAL'
    elif h2 and h3:v='LP3_MEMORY_HELPS' if leak_ok and drift_ok else 'LP3_HELPS_BUT_LEAKS' if drift_ok else 'LP3_HELPS_BUT_DRIFTS'
    elif hurts:v='LP3_HURTS'
    elif h3:v='LP3_DEPENDS_NO_GAIN'
    else:v='LP3_NO_DEPENDENCE'
    sums={a:{k:S(a,k) for k in ('learned','hard','heldout','fixed_fail','para_v1','leak','forgot')} for a in ARMS}
    for a in ARMS:
        if a!='CE':sums[a].update({k:S(a,k) for k in ('hard_swap','hard_swap_follow','hard_oracle','hard_gated','heldout_oracle','heldout_gated','leak_gated')})
    return {'verdict':v,'H1':h1,'H2':h2,'H3':h3,'leak_ok':leak_ok,'drift_ok':drift_ok,'swap_drop':drop,'swap_follow':follow,
            'retrieval_hard_own':{a:mean([r['retrieval_after']['hard']['own'] for r in rows if r['arm']==a]) for a in ARMS},
            'kl_probe_mean':{a:mean([r['kl_probe'] for r in rows if r['arm']==a]) for a in ARMS},
            'kl_probe_bare_mean':{a:mean([r['kl_probe_bare'] for r in rows if r['arm']==a]) for a in ARMS},'sums':sums}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--master',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--seeds',type=int,nargs='+',default=[47,53,59,61]);ap.add_argument('--steps',type=int,default=30);ap.add_argument('--threads',type=int,default=4)
    ap.add_argument('--arms',nargs='+',default=list(ARMS))
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);rows=[]
    done=a.out/'rows.jsonl'
    if done.is_file():rows=[json.loads(x) for x in done.read_text().splitlines() if x.strip()]
    for seed in a.seeds:
        for arm in a.arms:
            if any(r['arm']==arm and r['seed']==seed for r in rows):continue
            t0=time.monotonic();r=run_arm(a.master,arm,seed,a.steps,a.threads,a.out/'work');r['seconds']=round(time.monotonic()-t0,1)
            rows.append(r)
            with done.open('a') as f:f.write(json.dumps(r)+'\n')
            print(json.dumps({k:r.get(k) for k in ('arm','seed','learned','hard','hard_swap','hard_swap_follow','hard_oracle','heldout',
                                                   'fixed_fail','leak','forgot','kl_probe','retrieval_after','seconds')}),flush=True)
    if {r['arm'] for r in rows}!=set(ARMS) or len(rows)<len(ARMS)*len(a.seeds):return
    st=a.master/'model.safetensors'
    rep={'prereg':'docs/proofs/continuation-20261022/lp3-memory-key/PREREG.md','master_sha256':file_hash(st) if st.is_file() else None,
         'script_sha256':file_hash(Path(__file__)),'lp2_script_sha256':file_hash(APP/'scripts/lp2_assignment_objective.py'),
         'trainer_sha256':file_hash(APP/'v13/lora_trainer.py'),'cfg':LIVE,'lp2':LP2,'gate_p':GATE_P,'rows':rows}|verdict(rows)
    (a.out/'report.json').write_text(json.dumps(rep,indent=1))
    print(json.dumps({k:rep[k] for k in ('verdict','H1','H2','H3','leak_ok','drift_ok','swap_drop','swap_follow','retrieval_hard_own','kl_probe_mean','kl_probe_bare_mean','sums')}))

if __name__=='__main__':main()
