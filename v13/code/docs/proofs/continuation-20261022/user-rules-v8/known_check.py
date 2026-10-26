#!/usr/bin/env python3
"""K4 check for v8: the reader on every KNOWN sentence set (as train_second.known_files: dev, holdouts, rounds 1-7, holdout_de2-4,
dev_v7, dev_v8), with the second opinion off or on. Prints safety failures per set and the no-rule sentences that still trigger
a rule or question. Usage: known_check.py [off|jef] [-v]"""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE.parents[1]/'continuation-20261021/user-rules'));sys.path.insert(0,str(HERE))
import userrules_eval as E
from train_second import known_files
E.U.SECOND_OPINION=sys.argv[1] if len(sys.argv)>1 and sys.argv[1] in ('off','jef') else 'jef'
T=0;NF=0;NN=0
for f in known_files():
    items=json.loads(f.read_text())['items'];tot,rows=E.score(items)
    none=[r for r in rows if r['want_kind']=='NONE'];fired=[r for r in none if r['got_kind']!='NONE']
    NF+=len(fired);NN+=len(none);T+=tot['safety_failures']
    print(str(f).split('proofs/')[1],len(items),'fail',tot['safety_failures'],'none_fired',len(fired),'/',len(none))
    for r in rows:
        if r['safety_failures']:print('   FAIL',r['want_kind'],'->',r['got_kind'],r['safety_failures'],'|',r['text'])
    if '-v' in sys.argv:
        for r in fired:print('   NONEFIRED',r['got_kind'],'|',r['text'])
print('SECOND',E.U.SECOND_OPINION,'TOTAL fail',T,'none_fired',NF,'/',NN)
