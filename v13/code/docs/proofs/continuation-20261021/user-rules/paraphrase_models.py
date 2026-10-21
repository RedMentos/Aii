#!/usr/bin/env python3
"""Rewrite every holdout sentence with two local models (B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B), only after freeze.json.
The raw model output is stored unfiltered; a hand audit (audit.json) marks which rewrites keep the meaning before the
parser sees them. Usage: paraphrase_models.py <installed-home> <out.json>"""
import hashlib,json,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT))
from v13.runtime import Runtime

SYSTEM=('You rewrite one sentence. Keep exactly the same meaning and the same language (German stays German, English stays '
        'English). Use different words and a different sentence structure. Return JSON only.')
SCHEMA={'type':'object','additionalProperties':False,'required':['sentence'],'properties':{'sentence':{'type':'string','maxLength':240}}}
ROLES=('B1_DETAIL','B2_GIST')

ROUND2={'freeze':'freeze_v2.json','roles':('B1_DETAIL','B2_GIST','C3_LANGUAGE'),'seed':2000,
        'system':('Say the same thing the way a different person would say it in a chat message: same meaning, same language as the '
                  'input, new words, casual or formal as you like. Do not answer it, only restate it. Return JSON only.')}

def main(home,out,rnd=1):
    global SYSTEM,ROLES
    fz='freeze.json';seed0=1000
    if rnd==2:fz,ROLES,SYSTEM,seed0=ROUND2['freeze'],ROUND2['roles'],ROUND2['system'],ROUND2['seed']
    freeze=json.loads((HERE/fz).read_text())
    for f,h in freeze['files'].items():
        if hashlib.sha256((ROOT/f).read_bytes()).hexdigest()!=h:raise SystemExit('changed after freeze: '+f)
    items=json.loads((HERE/'holdout_author.json').read_text())['items'];r=Runtime(Path(home));rows=[]
    try:
        for i,it in enumerate(items):
            for role in ROLES:
                msgs=[{'role':'system','content':SYSTEM},{'role':'user','content':'Sentence: '+it['text']}]
                raw='';t0=time.monotonic()
                try:
                    runner=r.pool.get(role)
                    for chunk in runner.generate(msgs,r.cancel_event,time.monotonic()+90,96,SCHEMA,seed=seed0+i):raw+=chunk
                    sent=json.loads(raw)['sentence'].strip();err=None
                except Exception as exc:sent=None;err=type(exc).__name__
                rows.append({'index':i,'role':role,'model':r.models.revision(role) if hasattr(r.models,'revision') else None,'original':it['text'],
                             'raw':raw,'sentence':sent,'error':err,'seconds':round(time.monotonic()-t0,2)})
                print(i,role,repr(sent),flush=True)
    finally:r.close()
    Path(out).write_text(json.dumps({'schema':'USER_RULES_MODEL_PARAPHRASES_V1','freeze':freeze['files'],'system':SYSTEM,'round':rnd,'roles':list(ROLES),'rows':rows},ensure_ascii=False,indent=1)+'\n')

if __name__=='__main__':main(sys.argv[1],sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 1)
