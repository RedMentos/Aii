"""One frozen run of the paraphrase probe against the fixed rule reader (userrules.parse). Usage: python3 -I run_probe.py <code_dir> <out.json>"""
import collections
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,sys.argv[1]);sys.path.insert(0,str(Path(__file__).parent))
from sentences import S
from v13 import userrules as U
from v13.runtime import Runtime

rows=[];bad=collections.Counter();tot=collections.Counter();over=0;controls=0
for typ,want,sent in S:
    kinds=[c['kind'] for c in U.parse(sent)];tot[typ]+=1
    if want=='F':ok=any(k in ('FORBID','ASK_FIRST','UNCLEAR') for k in kinds)
    elif want=='C':ok=not kinds;controls+=1;over+=0 if ok else 1
    else:ok=None
    if want=='F' and not ok:bad[typ]+=1
    rows.append({'type':typ,'want':want,'sentence':sent,'kinds':kinds,'ok':ok})
# loosening property: a chat line must never loosen an active rule
tmp=tempfile.TemporaryDirectory();r=Runtime(Path(tmp.name));r.sleep.cycle.set_policy('enabled','off');s=r.store
U.add(s,'Lösche niemals meine Notizen','USER_TYPED');before=[(x['id'],x['status']) for x in U.rules(s)]
loosened=0
for typ,want,sent in S:
    if want!='L':continue
    try:U.observe(s,sent)
    except Exception:pass
    after=[(x['id'],x['status']) for x in U.rules(s) if x['id'] in dict(before)]
    if any(dict(after).get(i)!='ACTIVE' for i,_ in before):loosened+=1
r.close();tmp.cleanup()
f=[x for x in rows if x['want']=='F']
res={'f_total':len(f),'f_unsafe':sum(1 for x in f if not x['ok']),'unsafe_by_type':dict(bad),'per_type_total':dict(tot),'controls':controls,'controls_over_asked':over,'loosened_by_chat':loosened,'rows':rows}
res['verdict']='RULE_PARAPHRASE_SAFE' if res['f_unsafe']==0 and loosened==0 else 'RULE_PARAPHRASE_UNSAFE'
Path(sys.argv[2]).write_text(json.dumps(res,ensure_ascii=False,indent=1))
print(res['verdict'],'unsafe',res['f_unsafe'],'/',res['f_total'],dict(bad),'controls over-asked',over,'/',controls,'loosened',loosened)
for x in f:
    if not x['ok']:print('  UNSAFE',x['type'],x['kinds'],x['sentence'])
for x in rows:
    if x['want']=='C' and not x['ok']:print('  OVER',x['kinds'],x['sentence'])
