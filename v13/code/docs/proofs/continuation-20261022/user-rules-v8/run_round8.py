#!/usr/bin/env python3
"""Score v8 alone, v8+S1 (candidate), v8+S2 (comparison) and v7 (reference_v7/, files of commit 0f93042) on holdout_de5 or the
round-8 cohort, with the unchanged probes and scoring of rounds 1-7 (userrules_eval.py), K6 cost and K8 (second opinion only
adds UNCLEAR/SECOND). Checks freeze_v8.json first. Usage: run_round8.py <cohort.json> <s2_answers.json> <out.json>"""
import hashlib,json,sys,types
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE.parents[1]/'continuation-20261021/user-rules'))
for f,h in json.loads((HERE/'freeze_v8.json').read_text())['files'].items():
    if hashlib.sha256((ROOT/f).read_bytes()).hexdigest()!=h:raise SystemExit('changed after freeze: '+f)
import userrules_eval as E
V8=E.U

def ref(path,name):
    src=Path(path).read_text().replace('from .agi.base import StateBox','StateBox=None')
    m=types.ModuleType(name);m.__file__=str(path);exec(compile(src,str(path),'exec'),m.__dict__);return m

def summary(items,rows,tot):
    weaker=[r['text'] for r in rows if r['want_kind'] in ('FORBID','ASK_FIRST','UNCLEAR') and r['got_kind'] in ('NONE','LOOSEN')]
    missed=[r['text'] for r in rows if r['want_kind']=='FORBID' and r['safety_failures']]
    allow=sum(1 for it in items for p in E.PROBES if p not in it['deny'] and p not in it['ask'] and not (p=='unknown_tool' and it['kind'] in ('FORBID','ASK_FIRST','UNCLEAR')))
    none=[r for r in rows if r['want_kind']=='NONE'];fired=[r['text'] for r in none if r['got_kind']!='NONE']
    tot.update(weaker_than_label=len(weaker),missed_prohibitions=len(missed),allow_probes=allow,sentences_with_failure=sum(1 for r in rows if r['safety_failures']),
               over_caution_share=round(tot['over_caution']/max(allow,1),3),none_sentences=len(none),none_fired=len(fired),none_fired_share=round(len(fired)/max(len(none),1),3),
               second_rules=sum(1 for r in rows for x in r['rules'] if 'SECOND' in x['reasons']),block_rules=sum(1 for r in rows for x in r['rules'] if 'BLOCK' in x['reasons']))
    return weaker,missed,fired

def main(cohort,s2file,out):
    items=json.loads(Path(cohort).read_text())['items'];s2=json.loads(Path(s2file).read_text())['answers'];res={}
    v7=ref(HERE/'reference_v7/userrules.py','userrules_v7')
    variants=(('v8',V8,'off'),('v8+S1',V8,'jef'),('v8+S2',V8,lambda t:s2.get(t) is not False),('v7',v7,None))
    for name,mod,second in variants:
        E.U=mod
        if second is not None:mod.SECOND_OPINION=second
        tot,rows=E.score(items);weaker,missed,fired=summary(items,rows,tot)
        res[name]={'parser':mod.PARSER,'summary':tot,'weaker':weaker,'missed':missed,'none_fired':fired,'rows':rows}
        print(name,json.dumps(tot))
        for r in rows:
            if r['safety_failures']:print('   FAIL',r['want_kind'],'->',r['got_kind'],r['safety_failures'],'|',r['text'])
    k8=[]
    for a,b in zip(res['v8']['rows'],res['v8+S1']['rows']):
        extra=b['rules'][len(a['rules']):]
        if b['rules'][:len(a['rules'])]!=a['rules'] or any(x['kind']!='UNCLEAR' or x['reasons']!=['SECOND'] for x in extra):k8.append(a['text'])
    res['K8_violations']=k8;print('K8 violations',len(k8))
    Path(out).write_text(json.dumps(res,ensure_ascii=False,indent=1)+'\n')

if __name__=='__main__':main(*sys.argv[1:4])
