#!/usr/bin/env python3
"""Score frozen reader v7 (v13.userrules) and, for comparison, v6 (reference_v6/, files of commit 7ba3ae6) on holdout_de4
or the round-7 cohort, with the unchanged probes and scoring of rounds 1-6 (userrules_eval.py), plus the K6 cost of the
broad net (share of no-rule sentences that trigger a rule or question). Checks freeze_v7.json first.
Usage: run_round7.py <cohort.json> <out.json>"""
import hashlib,json,sys,types
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE.parents[1]/'continuation-20261021/user-rules'))
for f,h in json.loads((HERE/'freeze_v7.json').read_text())['files'].items():
    if hashlib.sha256((ROOT/f).read_bytes()).hexdigest()!=h:raise SystemExit('changed after freeze: '+f)
import userrules_eval as E

def ref(path,name):
    src=Path(path).read_text().replace('from .agi.base import StateBox','StateBox=None')
    m=types.ModuleType(name);m.__file__=str(path);exec(compile(src,str(path),'exec'),m.__dict__);return m

def main(cohort,out):
    items=json.loads(Path(cohort).read_text())['items'];res={}
    for name,mod in (('v7',E.U),('v6',ref(HERE/'reference_v6/userrules.py','userrules_v6'))):
        E.U=mod;tot,rows=E.score(items)
        weaker=[r['text'] for r in rows if r['want_kind'] in ('FORBID','ASK_FIRST','UNCLEAR') and r['got_kind'] in ('NONE','LOOSEN')]
        missed=[r['text'] for r in rows if r['want_kind']=='FORBID' and r['safety_failures']]
        allow=sum(1 for it in items for p in E.PROBES if p not in it['deny'] and p not in it['ask'] and not (p=='unknown_tool' and it['kind'] in ('FORBID','ASK_FIRST','UNCLEAR')))
        none=[r for r in rows if r['want_kind']=='NONE'];fired=[r['text'] for r in none if r['got_kind']!='NONE']
        tot.update(weaker_than_label=len(weaker),missed_prohibitions=len(missed),allow_probes=allow,sentences_with_failure=sum(1 for r in rows if r['safety_failures']),
                   over_caution_share=round(tot['over_caution']/max(allow,1),3),none_sentences=len(none),none_fired=len(fired),none_fired_share=round(len(fired)/max(len(none),1),3),
                   net_rules=sum(1 for r in rows for x in r['rules'] if 'NET' in x['reasons']))
        res[name]={'parser':mod.PARSER,'summary':tot,'weaker':weaker,'missed':missed,'none_fired':fired,'rows':rows}
        print(name,mod.PARSER,json.dumps(tot))
        if name=='v7':
            for r in rows:
                if r['safety_failures'] or r['want_kind']!=r['got_kind'] or r['soft']:
                    print('  ',r['want_kind'],'->',r['got_kind'],'FAIL' if r['safety_failures'] else '',r['safety_failures'],r['soft'],'|',r['text'])
    Path(out).write_text(json.dumps(res,ensure_ascii=False,indent=1)+'\n')

if __name__=='__main__':main(sys.argv[1],sys.argv[2])
