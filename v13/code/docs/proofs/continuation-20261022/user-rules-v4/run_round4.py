#!/usr/bin/env python3
"""Score frozen reader v4 (v13.userrules) and, for comparison, v3 (reference_v3/, files of commit 43fa3d0) and v2
(../user-rules-v3/reference_v2_userrules.py) on the audited round-4 cohort, with the unchanged probes and scoring of
rounds 1-3 (userrules_eval.py). Checks freeze_v4.json first. Usage: run_round4.py <cohort.json> <out.json>"""
import hashlib,json,sys,types
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE.parents[1]/'continuation-20261021/user-rules'))
for f,h in json.loads((HERE/'freeze_v4.json').read_text())['files'].items():
    if hashlib.sha256((ROOT/f).read_bytes()).hexdigest()!=h:raise SystemExit('changed after freeze: '+f)
import userrules_eval as E

def ref(path,name):
    src=Path(path).read_text().replace('from .agi.base import StateBox','StateBox=None')
    m=types.ModuleType(name);m.__file__=str(path);exec(compile(src,str(path),'exec'),m.__dict__);return m

def main(cohort,out):
    items=json.loads(Path(cohort).read_text())['items'];res={}
    for name,mod in (('v4',E.U),('v3',ref(HERE/'reference_v3/userrules.py','userrules_v3')),('v2',ref(HERE.parent/'user-rules-v3/reference_v2_userrules.py','userrules_v2'))):
        E.U=mod;tot,rows=E.score(items)
        weaker=[r['text'] for r in rows if r['want_kind'] in ('FORBID','ASK_FIRST','UNCLEAR') and r['got_kind'] in ('NONE','LOOSEN')]
        missed=[r['text'] for r in rows if r['want_kind']=='FORBID' and r['safety_failures']]
        allow=sum(1 for it in items for p in E.PROBES if p not in it['deny'] and p not in it['ask'] and not (p=='unknown_tool' and it['kind'] in ('FORBID','ASK_FIRST','UNCLEAR')))
        tot.update(weaker_than_label=len(weaker),missed_prohibitions=len(missed),allow_probes=allow,sentences_with_failure=sum(1 for r in rows if r['safety_failures']))
        res[name]={'parser':mod.PARSER,'summary':tot,'weaker':weaker,'missed':missed,'rows':rows}
        print(name,mod.PARSER,json.dumps(tot))
        if name=='v4':
            for r in rows:
                if r['safety_failures'] or r['want_kind']!=r['got_kind'] or r['soft']:
                    print('  ',r['want_kind'],'->',r['got_kind'],'FAIL' if r['safety_failures'] else '',r['safety_failures'],r['soft'],'|',r['text'])
    Path(out).write_text(json.dumps(res,ensure_ascii=False,indent=1)+'\n')

if __name__=='__main__':main(sys.argv[1],sys.argv[2])
