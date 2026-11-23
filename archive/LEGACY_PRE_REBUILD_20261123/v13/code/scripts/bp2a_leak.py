#!/usr/bin/env python3
"""WP-BP2a: weight learning in everyday use without leaking the new fact onto other people/things (blueprint §14.5, §21, §29 Nr. 18/22).

Same bench as WP-BJ1 (16 invented personal facts on B1 LFM2.5-1.2B, fp32 master, answer CE + KL anchors, jepa_weight 0), arms:
  ce       today's path (BJ1 ce arm: leak 0.81)
  locality + per-fact near-miss TRAINING questions about other subjects, KL-anchored to the base (subjects disjoint from the eval ones)
  minor    LoRA restricted to the lowest singular directions of every wrapped weight (Subspace Tuning, WP-FS2)
  both     locality + minor
Eval subjects (dog, sister, wife, nephew, ...) never appear in training anchors. Usage: bp2a_leak.py --master DIR --out DIR --seed 1
"""
import argparse,json,sys,time,platform
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from v13.body_jepa import BodyJepaTrainer
from v13.common import file_hash
from scripts.bj1_body_jepa import POOL,ANCHORS,evaluate

# Two training near-miss questions per fact (index = POOL index), subjects only from: friend, mother, father, boss, cousin, uncle,
# colleague, neighbour, grandmother, son, horse, hamster. The base answers them; the adapter must keep the base's behaviour.
TRAIN_NM=[
 ['What is the name of my horse?','What is the name of my friend\'s cat?'],
 ['Where does my mother work?','Where does my boss work?'],
 ['What is my father\'s favourite colour?','What is my boss\'s favourite colour?'],
 ['What is the name of my cousin?','What is the name of my uncle?'],
 ['Which instrument does my cousin play?','Which instrument does my mother play?'],
 ['What is the name of my boss\'s project?','What is the name of my friend\'s project?'],
 ['When is my mother\'s birthday?','When is my friend\'s birthday?'],
 ['What is the name of my neighbour\'s boat?','What is the name of my uncle\'s boat?'],
 ['Which city did my cousin move to last year?','Which city did my boss move to last year?'],
 ['What is my father\'s favourite dish?','What is my colleague\'s favourite dish?'],
 ['What is the name of my hamster?','What is the name of my neighbour\'s parrot?'],
 ['Which football club does my father support?','Which football club does my colleague support?'],
 ['What is my mother\'s favourite book?','What is my friend\'s favourite book?'],
 ['What is the name of my grandmother?','What is the name of my son\'s grandfather?'],
 ['Which language is my cousin learning?','Which language is my boss learning?'],
 ['What is my son\'s favourite board game?','What is my uncle\'s favourite board game?'],
 ['Which street does my mother live on?','Which street does my friend live on?'],
 ['What is the name of my son\'s goldfish?','What is the name of my neighbour\'s goldfish?'],
 ['What is my father\'s blood type?','What is my cousin\'s blood type?'],
 ['Which mountain did my uncle climb last summer?','Which mountain did my friend climb last summer?'],
 ['What is the name of my son\'s teacher?','What is the name of my mother\'s teacher?'],
 ['What is my grandmother\'s favourite flower?','What is my mother\'s favourite flower?'],
 ['What is the name of my uncle\'s tortoise?','What is the name of my friend\'s tortoise?'],
 ['Which band did my cousin see live last month?','Which band did my boss see live last month?'],
]
assert len(TRAIN_NM)==len(POOL)
ARMS={'ce':(False,'none'),'locality':(True,'none'),'minor':(False,'minor'),'both':(True,'minor')}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--master',required=True);ap.add_argument('--out',required=True);ap.add_argument('--seed',type=int,required=True)
    ap.add_argument('--arms',default='ce,locality,minor,both');ap.add_argument('--facts',type=int,default=16)
    ap.add_argument('--threads',type=int,default=4);ap.add_argument('--steps',type=int,default=30);ap.add_argument('--lr',type=float,default=5e-4)
    ap.add_argument('--anchors-per-step',type=int,default=10);ap.add_argument('--anchor-weight',type=float,default=1.)
    ap.add_argument('--minor-lr',type=float,default=None,help='lr for minor arms (default: same)')
    ap.add_argument('--smoke',action='store_true')
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(a.seed);idx=sorted(rng.choice(len(POOL),size=min(a.facts,len(POOL)),replace=False).tolist())
    facts=[POOL[i] for i in idx];items=[{'memory_id':'bp2a_%d'%i,'prompt':q,'target':t,'answer_keys':k} for i,(q,t,k,_,_) in zip(idx,facts)]
    nm=[q for i in idx for q in TRAIN_NM[i]]
    rep={'schema':'v13-bp2a-leak-v1','seed':a.seed,'fact_index':idx,'platform':platform.platform(),'master':a.master,
         'master_sha256':file_hash(Path(a.master)/'model.safetensors'),'started':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'args':vars(a),'arms':{}}
    path=out/('bp2a-seed%d.json'%a.seed)
    for arm in a.arms.split(','):
        loc,sub=ARMS[arm]
        lr=a.minor_lr if (sub=='minor' and a.minor_lr) else a.lr
        cfg={'threads':a.threads,'max_steps':a.steps,'min_steps':a.steps,'lr':lr,'seed':a.seed,'anchors_per_step':a.anchors_per_step,
             'anchor_weight':a.anchor_weight,'jepa_weight':0.,'lora_subspace':sub,'locality_swaps':2}
        if a.smoke:cfg.update(max_steps=2,min_steps=2)
        anchors=ANCHORS+(nm if loc else [])
        tr=BodyJepaTrainer(a.master,out/'work'/('s%d-%s'%(a.seed,arm)),anchors=anchors,cfg=cfg,arch='lfm2')
        t=time.monotonic();r=tr.fit(items,'bp2a')
        if 'base' not in rep:rep['base']=evaluate(tr,facts,adapter=False)
        ev=evaluate(tr,facts);ev['wall_seconds']=round(time.monotonic()-t,1)
        m=r['metrics'];rep['arms'][arm]={'metrics':m,'eval':ev,'train_anchor_count':len(anchors)}
        print(json.dumps({'arm':arm,'steps':m['steps'],'ce':m['final_ce'],'train_s':m['seconds'],**{k:ev[k] for k in ('learned_recall','paraphrase_recall','near_miss_leak','probe_correct')},
                          'subspace':m['subspace_info']}),flush=True)
        path.write_text(json.dumps(rep,indent=1,ensure_ascii=False))
        del tr
    print(str(path))

if __name__=='__main__':main()
