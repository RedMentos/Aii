#!/usr/bin/env python3
"""WP-LP2 (prereg docs/proofs/continuation-20261022/lp2-assignment-objective/PREREG.md): a latent C3 objective that only
pays for the RIGHT assignment (predictor + slow EMA target + InfoNCE against the other items), measured on new tasks.

  python3 scripts/lp2_assignment_objective.py --master <HF dir LFM2.5-350M> --out <dir> [--seeds 31 37 41 43] [--steps 30]

LP1 showed that a plain cosine to a frozen mean target rises almost as much with a wrongly assigned target. Here the
latent term is contrastive: the predictor output of item k must be closer to the slow target of item k than to the
targets of all other items. Arms: CE (+KL, no latent term), NCE_OK (own target), NCE_SHUF (fixed derangement k -> k+1).
Benefit is judged only on held-out paraphrases written for LP2 (never trained, never used in LP1). Nothing is exported,
activated or approved.
"""
import argparse,json,sys,time
from pathlib import Path
APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP));sys.path.insert(0,str(APP/'scripts'))
from lora_bench import FACTS as FACTS_V1,PARAPHRASES as PARA_V1,NEAR_MISS as NEAR_V1,ANCHORS,PROBES  # noqa: E402
from lora_prompt_boundary_candidate import PromptBoundLoraTrainer  # noqa: E402
from v13.lora_trainer import answer_hit  # noqa: E402
from v13.common import file_hash  # noqa: E402

# 8 further invented facts (no real person, the base cannot know them), same shape as lora_bench.FACTS.
FACTS_V2=[
 ('What is the name of my horse?','Your horse is called Brombeer.',['brombeer']),
 ('Which city did I move to last year?','You moved to Tromso last year.',['tromso']),
 ("What is my grandmother's name?",'Your grandmother is called Ilsabe.',['ilsabe']),
 ('What is the name of my boat?','Your boat is called Seeschwalbe.',['seeschwalbe']),
 ('Which language am I learning?','You are learning Basque.',['basque']),
 ('What is my locker number?','Your locker number is 4417.',['4417']),
 ('What is the name of my band?','Your band is called Rostfrei.',['rostfrei']),
 ('Which tree did I plant in my garden?','You planted a ginkgo in your garden.',['ginkgo']),
]
FACTS=FACTS_V1+FACTS_V2
# New tasks: two fresh paraphrases per fact, item index first. Disjoint from FACTS prompts and lora_bench.PARAPHRASES.
HELDOUT=[
 (0,'What did I name my cat?'),(0,'My cat has a name. What is it?'),
 (1,'Where is my workplace?'),(1,'Which bakery do I work at?'),
 (2,'Which colour is my favourite?'),(2,'If I had to pick one colour, which one would I choose?'),
 (3,"What is my brother's name?"),(3,'How is my brother called?'),
 (4,'What instrument am I able to play?'),(4,'Name the instrument that I play.'),
 (5,'Which phone do I have?'),(5,'What kind of phone do I use?'),
 (6,"What is my project's name?"),(6,'How is my project named?'),
 (7,'On which date is my birthday?'),(7,'Which day of the year is my birthday?'),
 (8,'What did I name my horse?'),(8,'How is my horse called?'),
 (9,'Where did I move to last year?'),(9,'Which city have I been living in since last year?'),
 (10,"What is my grandma's name?"),(10,'How is my grandmother called?'),
 (11,'What did I name my boat?'),(11,'What is my boat called?'),
 (12,'What language am I studying?'),(12,'Which foreign language am I learning at the moment?'),
 (13,'Which number does my locker have?'),(13,'What number is on my locker?'),
 (14,'What is my band called?'),(14,'How is my band named?'),
 (15,'What tree did I plant in my garden?'),(15,'Which tree is growing in my garden since I planted it?'),
]
NEAR_MISS=NEAR_V1+[('What is the name of my cow?',['brombeer']),('Which city did my sister move to?',['tromso']),
 ("What is my grandfather's name?",['ilsabe']),('What is the name of my car?',['seeschwalbe']),
 ('Which language is my brother learning?',['basque']),('What is my house number?',['4417']),
 ('What is the name of my football team?',['rostfrei']),('Which flower did I plant in my garden?',['ginkgo'])]

LIVE={'rank':8,'alpha':16.,'lr':3e-4,'anchor_weight':8.,'anchors_per_step':16,'targets':['w1','w2','w3'],'max_tokens':160}
LP2={'nce_weight':.5,'temperature':.1,'ema_tau':.9,'pred_hidden':256,'pred_lr':1e-3}
ARMS={'CE':(0.,None),'NCE_OK':(LP2['nce_weight'],'own'),'NCE_SHUF':(LP2['nce_weight'],'shift')}
GRAD_STEPS=(1,30)


def run_arm(master,arm,seed,steps,threads,work):
    import torch
    import torch.nn.functional as F
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from peft import LoraConfig,get_peft_model
    torch.set_num_threads(threads);torch.manual_seed(seed)
    enc=PromptBoundLoraTrainer(master,work,cfg=dict(LIVE,seed=seed))
    tok=AutoTokenizer.from_pretrained(str(master));model=AutoModelForCausalLM.from_pretrained(str(master),dtype=torch.float32);model.eval()
    greedy=lambda m,ids,n:enc._greedy(torch,m,ids,n)
    def ask(m,q,n=24):
        pid,_=enc._encode(tok,q);return tok.decode(greedy(m,pid,n),skip_special_tokens=True)
    items=[{'prompt':q,'target':t,'keys':k} for q,t,k in FACTS];N=len(items)
    base_probe=[answer_hit(ask(model,p['prompt']),p['expect']) for p in PROBES]
    base_heldout=sum(answer_hit(ask(model,q),items[k]['keys']) for k,q in HELDOUT)
    anchor_seqs=[]
    for a in ANCHORS:
        pid,_=enc._encode(tok,a);anchor_seqs.append(pid+greedy(model,pid,24))
    probe_seqs=[]
    for p in PROBES:
        pid,_=enc._encode(tok,p['prompt']);probe_seqs.append((len(pid),pid+greedy(model,pid,16)))
    with torch.no_grad():
        anchor_logp=[torch.log_softmax(model(torch.tensor([s])).logits[0].float(),-1) for s in anchor_seqs]
        probe_logp=[torch.log_softmax(model(torch.tensor([s])).logits[0].float(),-1) for _,s in probe_seqs]
    data=[enc._encode(tok,i['prompt'],i['target']) for i in items]
    plens=[next(j for j,v in enumerate(lab) if v!=-100) for _,lab in data]
    tids=[tok(i['target'],add_special_tokens=False)['input_ids'] for i in items]
    last=lambda m,ids:m(torch.tensor([ids]),output_hidden_states=True).hidden_states[-1][0]
    def answer_bank(m):
        with torch.no_grad():return torch.stack([last(m,t).mean(0) for t in tids])
    base_bank=answer_bank(model)
    w,mode=ARMS[arm];perm=list(range(N)) if mode!='shift' else [(k+1)%N for k in range(N)]
    D=base_bank.shape[1];H=LP2['pred_hidden']
    pred=torch.nn.Sequential(torch.nn.LayerNorm(D),torch.nn.Linear(D,H),torch.nn.GELU(),torch.nn.Linear(H,D))
    torch.nn.init.zeros_(pred[3].weight);torch.nn.init.zeros_(pred[3].bias)  # starts as identity map (residual below)
    P=lambda h:h+pred(h)
    lc=LoraConfig(r=LIVE['rank'],lora_alpha=LIVE['alpha'],lora_dropout=0.,target_modules=LIVE['targets'],bias='none')
    model=get_peft_model(model,lc);params=[p for p in model.parameters() if p.requires_grad]
    opt=torch.optim.AdamW([{'params':params,'lr':LIVE['lr']},{'params':list(pred.parameters()),'lr':LP2['pred_lr']}],weight_decay=0.)
    slow=base_bank.clone()  # slow target: per-item EMA of the model's own answer state, stop-gradient
    def nce(zq,bank,labels):
        logits=F.normalize(zq,dim=-1)@F.normalize(bank,dim=-1).T/LP2['temperature']
        return F.cross_entropy(logits,torch.tensor(labels))
    def retrieval(m):
        """Held-out paraphrases: does P(prompt state) pick its own item / the shifted item among the frozen base answers?"""
        with torch.no_grad():
            zs=torch.stack([P(last(m,enc._encode(tok,q)[0])[-1]) for _,q in HELDOUT])
            top=(F.normalize(zs,dim=-1)@F.normalize(base_bank,dim=-1).T).argmax(-1).tolist()
        own=sum(1 for (k,_),t in zip(HELDOUT,top) if t==k)/len(HELDOUT);sh=sum(1 for (k,_),t in zip(HELDOUT,top) if t==(k+1)%N)/len(HELDOUT)
        return {'own':own,'shifted':sh}
    ret_before=retrieval(model)
    def losses(pick):
        ce=0.;zq=[]
        for k,(ids,lab) in enumerate(data):
            o=model(torch.tensor([ids]),labels=torch.tensor([lab]),output_hidden_states=True)
            ce=ce+o.loss/N;zq.append(o.hidden_states[-1][0][plens[k]-1])
        zq=P(torch.stack(zq));nl=nce(zq,slow,perm)
        kl=0.
        for j in pick:
            cl=torch.log_softmax(model(torch.tensor([anchor_seqs[j]])).logits[0].float(),-1);bl=anchor_logp[j]
            kl=kl+(bl.exp()*(bl-cl)).sum(-1).mean()/len(pick)
        return ce,kl,nl
    def gnorm(t):
        g=torch.autograd.grad(t,params,retain_graph=True,allow_unused=True)
        return torch.cat([(x if x is not None else torch.zeros_like(p)).reshape(-1) for x,p in zip(g,params)])
    grads=[];hist=[];g=torch.Generator().manual_seed(seed);model.train()
    for step in range(1,steps+1):
        pick=torch.randperm(len(anchor_seqs),generator=g).tolist()[:LIVE['anchors_per_step']]
        ce,kl,nl=losses(pick)
        if step in GRAD_STEPS:
            gc,gk,gn=gnorm(ce),gnorm(kl),gnorm(nl);nc,nk,nn=float(gc.norm()),float(gk.norm()),float(gn.norm())
            den=nc+nk*LIVE['anchor_weight']+nn*w
            grads.append({'step':step,'ce_norm':nc,'kl_norm':nk,'nce_norm':nn,'nce_share_applied':nn*w/den if w and den else 0.,
                          'cos_ce_nce':float(F.cosine_similarity(gc,gn,dim=0)) if nc and nn else None})
        loss=ce+LIVE['anchor_weight']*kl+w*nl
        opt.zero_grad();loss.backward();opt.step()
        if w:  # slow target follows the adapted model, but only by (1 - tau) per step
            model.eval();cur=answer_bank(model);model.train();slow=LP2['ema_tau']*slow+(1-LP2['ema_tau'])*cur
        hist.append({'step':step,'ce':round(float(ce),5),'kl':round(float(kl),6),'nce':round(float(nl),5)})
    model.eval()
    learned=sum(answer_hit(ask(model,i['prompt']),i['keys']) for i in items)
    heldout_hits=[int(answer_hit(ask(model,q),items[k]['keys'])) for k,q in HELDOUT]
    para_v1=sum(answer_hit(ask(model,q),k) for q,k in PARA_V1)
    leak=sum(answer_hit(ask(model,q),k) for q,k in NEAR_MISS)
    after_probe=[answer_hit(ask(model,p['prompt']),p['expect']) for p in PROBES]
    forgot=sum(1 for b,a in zip(base_probe,after_probe) if b and not a)
    with torch.no_grad():
        kls=[]
        for (pl,s),bl in zip(probe_seqs,probe_logp):
            cl=torch.log_softmax(model(torch.tensor([s])).logits[0].float(),-1)[pl-1:-1];b=bl[pl-1:-1]
            kls.append(float((b.exp()*(b-cl)).sum(-1).mean()))
    return {'arm':arm,'seed':seed,'steps':steps,'learned':learned,'heldout':sum(heldout_hits),'heldout_hits':heldout_hits,
            'base_heldout':base_heldout,'para_v1':para_v1,'leak':leak,'forgot':forgot,'base_probe_correct':sum(base_probe),
            'kl_probe':sum(kls)/len(kls),'retrieval_before':ret_before,'retrieval_after':retrieval(model),'grads':grads,'history':hist}


def verdict(rows):
    S=lambda arm,k:sum(r[k] for r in rows if r['arm']==arm)
    seeds=sorted({r['seed'] for r in rows});by={(r['arm'],r['seed']):r for r in rows}
    ok=[r for r in rows if r['arm']=='NCE_OK'];mean=lambda xs:sum(xs)/len(xs) if xs else 0.
    r_ok=mean([r['retrieval_after']['own'] for r in ok]);r_base=mean([r['retrieval_before']['own'] for r in ok])
    h1=r_ok>=.5 and r_ok>=r_base+.25
    wins=lambda other:sum(1 for s in seeds if by[('NCE_OK',s)]['heldout']>=by[(other,s)]['heldout'])
    kl_ok=mean([r['kl_probe'] for r in ok]);kl_ce=mean([r['kl_probe'] for r in rows if r['arm']=='CE'])
    h2=(S('NCE_OK','heldout')>=S('CE','heldout')+6 and S('NCE_OK','heldout')>=S('NCE_SHUF','heldout')+6
        and wins('CE')>=len(seeds)-1 and wins('NCE_SHUF')>=len(seeds)-1)
    guard=S('NCE_OK','leak')<=S('CE','leak')+2 and S('NCE_OK','forgot')<=S('CE','forgot')+1 and kl_ok<=1.5*kl_ce
    hurts=S('NCE_OK','heldout')<=S('CE','heldout')-6 or S('NCE_OK','forgot')>=S('CE','forgot')+2
    v=('LP2_NO_ALIGNMENT' if not h1 else 'LP2_ASSIGNMENT_HELPS' if h2 and guard else 'LP2_HELPS_BUT_DRIFTS' if h2
       else 'LP2_HURTS' if hurts else 'LP2_ALIGNS_NO_GAIN')
    return {'verdict':v,'H1':h1,'H2':h2,'guard':guard,'retrieval_own':{'NCE_OK_before':r_base,'NCE_OK_after':r_ok},
            'kl_probe_mean':{'CE':kl_ce,'NCE_OK':kl_ok},
            'sums':{a:{k:S(a,k) for k in ('learned','heldout','para_v1','leak','forgot')} for a in ARMS}}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--master',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--seeds',type=int,nargs='+',default=[31,37,41,43]);ap.add_argument('--steps',type=int,default=30);ap.add_argument('--threads',type=int,default=4)
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
            print(json.dumps({k:r[k] for k in ('arm','seed','learned','heldout','base_heldout','para_v1','leak','forgot','kl_probe','retrieval_before','retrieval_after','seconds')}),flush=True)
    if {r['arm'] for r in rows}!=set(ARMS):return
    st=a.master/'model.safetensors'
    rep={'prereg':'docs/proofs/continuation-20261022/lp2-assignment-objective/PREREG.md','master_sha256':file_hash(st) if st.is_file() else None,
         'script_sha256':file_hash(Path(__file__)),'trainer_sha256':file_hash(APP/'v13/lora_trainer.py'),'cfg':LIVE,'lp2':LP2,'rows':rows}|verdict(rows)
    (a.out/'report.json').write_text(json.dumps(rep,indent=1));print(json.dumps({k:rep[k] for k in ('verdict','H1','H2','guard','retrieval_own','kl_probe_mean','sums')}))

if __name__=='__main__':main()
