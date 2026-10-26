#!/usr/bin/env python3
"""K4 check: the current reader on every KNOWN sentence set (dev, holdouts, model rounds 1-7, dev_v7, holdout_de4). Prints safety failures
per set and how many no-rule sentences still trigger a rule or question (-v lists them). Usage: known_check.py [-v]"""
import json,sys,glob
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE.parents[1]/'continuation-20261021/user-rules'))
import userrules_eval as E
sys.path.insert(0,str(HERE));import snapshot
E.U,_=snapshot.load()
B=str(HERE.parents[1])+'/'
files=[B+'continuation-20261021/user-rules/'+f for f in ('dev.json','holdout_author.json','model_cohort.json','model_cohort_round2.json')]
files+=sorted(glob.glob(B+'continuation-20261022/user-rules-v[3-6]/cohort_round*.json'))+sorted(glob.glob(B+'continuation-20261022/user-rules-v[5-6]/holdout_de*.json'))+[str(HERE.parent/'user-rules-v7'/'dev_v7.json')]+[str(HERE.parent/'user-rules-v7'/f) for f in ('holdout_de4.json','cohort_round7.json')]
T=0;NF=0;NN=0
for f in files:
    items=json.load(open(f))['items'];tot,rows=E.score(items)
    none=[r for r in rows if r['want_kind']=='NONE'];fired=[r for r in none if r['got_kind']!='NONE']
    NF+=len(fired);NN+=len(none);T+=tot['safety_failures']
    print(f.split('proofs/')[1],len(items),'fail',tot['safety_failures'],'none_fired',len(fired),'/',len(none))
    for r in rows:
        if r['safety_failures']:print('   FAIL',r['want_kind'],'->',r['got_kind'],r['safety_failures'],'|',r['text'])
    if '-v' in sys.argv:
        for r in fired:print('   NONEFIRED',r['got_kind'],'|',r['text'])
print('TOTAL fail',T,'none_fired',NF,'/',NN)
