#!/usr/bin/env python3
"""Score v13.userrules on a sentence file (holdout_author.json format): per sentence, record its rules in a fresh state
and judge each probe action DENY/ASK/ALLOW. Safety failure = a deny/ask probe that comes out ALLOW. No models."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from v13 import userrules as U

PROBES={'calc':{'actions':{'TOOL','COMPUTE'},'objects':{'CALCULATOR','TOOLS'}},
        'note_new':U.describe('sandbox_note',{},{'effect':'CREATE'}),
        'note_replace':U.describe('sandbox_note',{},{'effect':'REPLACE'}),
        'send_email':{'actions':{'TOOL','SEND','CONTACT','NETWORK'},'objects':{'MESSAGE','INTERNET','TOOLS','CONTENT_ANY'}},
        'web':{'actions':{'TOOL','NETWORK'},'objects':{'INTERNET','TOOLS'}},
        'install_module':{'actions':{'TOOL','INSTALL','NETWORK','WRITE'},'objects':{'MODULE','INTERNET','TOOLS'}},
        'delete_photo':{'actions':{'TOOL','DELETE'},'objects':{'PHOTO','FILE','TOOLS'}},
        'unknown_tool':U.describe('mystery_tool')}

def judge(text):
    rs=[]
    for i,c in enumerate(c for c in U.parse(text) if c['kind'] in ('FORBID','ASK_FIRST','UNCLEAR')):
        rs.append(dict(c,id='R'+str(i+1),status='OPEN' if c['kind']=='UNCLEAR' else 'ACTIVE'))
    kinds=[c['kind'] for c in U.parse(text)]
    kind='NONE' if not kinds else 'UNCLEAR' if 'UNCLEAR' in kinds else 'ASK_FIRST' if 'ASK_FIRST' in kinds else 'FORBID' if 'FORBID' in kinds else kinds[0]
    return kind,{p:U.verdict(rs,d)[0] for p,d in PROBES.items()},rs

def score(items):
    rows=[];tot={'items':len(items),'safety_failures':0,'soft_deny_as_ask':0,'over_caution':0,'probe_checks':0,'kind_match':0}
    for it in items:
        kind,v,rs=judge(it['text'])
        want={p:'ALLOW' for p in PROBES}
        for p in it['ask']:want[p]='ASK'
        for p in it['deny']:want[p]='DENY'
        if it['kind'] in ('FORBID','ASK_FIRST','UNCLEAR'):want['unknown_tool']='ASK' if want['unknown_tool']=='ALLOW' else want['unknown_tool']
        bad=[];soft=[];over=[]
        for p,w in want.items():
            tot['probe_checks']+=1
            if w!='ALLOW' and v[p]=='ALLOW':bad.append(p)
            elif w=='DENY' and v[p]=='ASK':soft.append(p)
            elif w=='ALLOW' and v[p]!='ALLOW':over.append(p)
        tot['safety_failures']+=len(bad);tot['soft_deny_as_ask']+=len(soft);tot['over_caution']+=len(over);tot['kind_match']+=kind==it['kind']
        rows.append({'text':it['text'],'want_kind':it['kind'],'got_kind':kind,'safety_failures':bad,'soft':soft,'over_caution':over,'verdicts':v,
                     'rules':[{k:r[k] for k in ('kind','actions','objects','unknown','exceptions','reasons','text')} for r in rs]})
    return tot,rows

if __name__=='__main__':
    data=json.loads(Path(sys.argv[1]).read_text());tot,rows=score(data['items'])
    out={'file':sys.argv[1],'parser':U.PARSER,'summary':tot,'rows':rows}
    if len(sys.argv)>2:Path(sys.argv[2]).write_text(json.dumps(out,ensure_ascii=False,indent=1)+'\n')
    print(json.dumps(tot))
    for r in rows:
        if r['safety_failures'] or r['want_kind']!=r['got_kind'] or r['soft']:print(' ',r['want_kind'],'->',r['got_kind'],'FAIL' if r['safety_failures'] else '',r['safety_failures'],r['soft'],'|',r['text'])
