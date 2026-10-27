#!/usr/bin/env python3
"""WP-BP2b: do generated locality anchors (v13/locality_gen.py, no hand list) give the BP2a effect, and does it carry over to
differently worded near-miss questions? Arms (all 30 steps, jepa_weight 0, same facts per seed as BP2a):
  ce         today's path
  hand_both  hand-written anchors (BP2a) + minor-subspace LoRA
  gen_both   generated anchors + minor-subspace LoRA
Leak A = BP2a near-miss questions (same form, other person). Leak B = reworded near-miss questions (new phrasing, other persons never used in training).
Usage: bp2b_transfer.py --master DIR --out DIR --seed 1
"""
import argparse,json,sys,time,platform
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from v13.body_jepa import BodyJepaTrainer
from v13.locality_gen import anchors_for
from v13.common import file_hash
from v13.lora_trainer import answer_hit
from scripts.bj1_body_jepa import POOL,ANCHORS,evaluate,gen
from scripts.bp2a_leak import TRAIN_NM

# One reworded near-miss question per fact (index = POOL index): other phrasing, persons not used in any training anchor.
EVAL_B=[
 "Could you remind me what my girlfriend's cat is called?","Do you know where my wife works these days?","My nephew asked me: what colour does he like best?",
 "Can you tell me my stepbrother's first name?","I'm curious which instrument my granddaughter plays.","Remind me what my sister's project is named.",
 "On which date was my wife born?","I forgot, what is my nephew's boat called?","Tell me which city my sister moved to last year.",
 "What would my stepbrother say is his favourite dish?","Quick one: how is my girlfriend's parrot called?","Which club does my wife cheer for on Saturdays?",
 "Which book does my granddaughter love most?","What was my sister's grandfather called?","What language is my girlfriend studying right now?",
 "Which board game does my wife enjoy most?","On which street does my nephew live?","What is the name of my sister's goldfish?",
 "What blood group does my stepbrother have?","Which mountain did my girlfriend climb last summer?","Who was my wife's favourite teacher at school?",
 "Which flower does my sister like best?","What is my nephew's tortoise called?","Which band did my granddaughter see live last month?"]
assert len(EVAL_B)==len(POOL)

def leak_b(tr,facts,idx):
    torch,model,tok=tr.torch,tr.model,tr.tok;rows=[]
    for i,(q,a,keys,paras,nm) in zip(idx,facts):
        t=gen(tr,torch,model,tok,EVAL_B[i]);rows.append({'q':EVAL_B[i],'ok':answer_hit(t,keys),'text':t[:160]})
    return {'near_miss_leak_reworded':sum(r['ok'] for r in rows)/len(rows),'rows_reworded':rows}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--master',required=True);ap.add_argument('--out',required=True);ap.add_argument('--seed',type=int,required=True)
    ap.add_argument('--arms',default='ce,hand_both,gen_both');ap.add_argument('--facts',type=int,default=16)
    ap.add_argument('--threads',type=int,default=4);ap.add_argument('--steps',type=int,default=30);ap.add_argument('--lr',type=float,default=5e-4)
    ap.add_argument('--smoke',action='store_true')
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(a.seed);idx=sorted(rng.choice(len(POOL),size=min(a.facts,len(POOL)),replace=False).tolist())
    facts=[POOL[i] for i in idx];items=[{'memory_id':'bp2b_%d'%i,'prompt':q,'target':t,'answer_keys':k} for i,(q,t,k,_,_) in zip(idx,facts)]
    hand=[q for i in idx for q in TRAIN_NM[i]];gen_a,cov=anchors_for([q for q,_,_,_,_ in facts])
    rep={'schema':'v13-bp2b-transfer-v1','seed':a.seed,'fact_index':idx,'platform':platform.platform(),'master':a.master,'args':vars(a),
         'master_sha256':file_hash(Path(a.master)/'model.safetensors'),'started':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
         'generator_coverage':cov,'arms':{}}
    path=out/('bp2b-seed%d.json'%a.seed)
    for arm in a.arms.split(','):
        anchors=ANCHORS+({'ce':[],'hand_both':hand,'gen_both':gen_a}[arm]);sub='none' if arm=='ce' else 'minor'
        cfg={'threads':a.threads,'max_steps':a.steps,'min_steps':a.steps,'lr':a.lr,'seed':a.seed,'anchors_per_step':10,'anchor_weight':1.,
             'jepa_weight':0.,'lora_subspace':sub,'locality_swaps':2}
        if a.smoke:cfg.update(max_steps=2,min_steps=2)
        tr=BodyJepaTrainer(a.master,out/'work'/('s%d-%s'%(a.seed,arm)),anchors=anchors,cfg=cfg,arch='lfm2')
        t=time.monotonic();r=tr.fit(items,'bp2b')
        ev=evaluate(tr,facts);ev.update(leak_b(tr,facts,idx));ev['wall_seconds']=round(time.monotonic()-t,1)
        rep['arms'][arm]={'metrics':r['metrics'],'eval':ev,'train_anchor_count':len(anchors)}
        print(json.dumps({'arm':arm,'ce':r['metrics']['final_ce'],'train_s':r['metrics']['seconds'],**{k:ev[k] for k in ('learned_recall','paraphrase_recall','near_miss_leak','near_miss_leak_reworded','probe_correct')},'n_anchors':len(anchors)}),flush=True)
        path.write_text(json.dumps(rep,indent=1,ensure_ascii=False));del tr
    print(str(path))

if __name__=='__main__':main()
