#!/usr/bin/env python3
"""Round-4 hand audit as data. Decisions written by hand after freeze_v4.json and before reader v4 (or v3/v2) saw any of
these sentences. S = same meaning; the script then puts it in the primary cohort when it keeps the source language and
in the secondary (language-switched, not for the verdict) cohort otherwise. 0 = excluded (reason). Copies, near copies
and duplicates are excluded automatically. Labels are inherited from the source sentence (holdout or dev)."""
import difflib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;UR=HERE.parents[1]/'continuation-20261021/user-rules'
raw=json.loads((HERE/'round4_raw.json').read_text())
SRC={'holdout':json.loads((UR/'holdout_author.json').read_text())['items'],'dev':json.loads((UR/'dev.json').read_text())['items']}
G='garbled';C='meaning changed';R='roles changed'
def d(spec):
    out={}
    for part in spec.split(';'):
        part=part.strip()
        if not part:continue
        k,_,v=part.partition(' ');v=v.strip()
        out[k]=('S','same') if v in ('','S') else ('0',v)
    return out
D={('holdout',i):d(s) for i,s in enumerate([
 'EU1;EU2;GR2 '+G+';PH1 '+C+';PH2 scope changed (all)','EU1;EU2;GR1;PH1;PH2 '+C,'EU1;GR1;PH1 '+R,'EU1;GR1;GR2 '+G+';PH1 '+C+';PH2',
 'EU1;EU2;GR1;GR2 '+G+';PH1 '+G+';PH2 '+C,'GR1;GR2 '+G+';PH1 '+G,'EU1;EU2;GR1;GR2 '+G+';PH1 question;PH2','EU2;GR1;PH1 '+C+';PH2 '+G,
 'EU1;EU2;GR1;GR2;PH1;PH2','GR1;GR2 '+R+';PH1','EU1 '+C+';EU2;GR1 '+C+';GR2 '+G+';PH1;PH2','EU1;EU2;GR1 '+C,'EU1;EU2;GR1;GR2 '+G+';PH1;PH2',
 'EU1 '+C+';GR1;GR2 '+G+';PH1;PH2','EU1;EU2;GR1 '+R+';PH1','EU1;GR1 mixed language;GR2 '+C+';PH1;PH2','GR1;GR2;PH1;PH2',
 'EU1;EU2 '+G+';GR1 object changed;GR2 '+G+';PH1;PH2','EU1;GR1;PH1;PH2 '+C,'EU1;GR1;GR2;PH1;PH2','EU1;GR1 '+G,'EU1;GR1;GR2 weaker (hedge added);PH1 '+G+';PH2',
 'EU1;GR1 '+G+';PH1','EU1;EU2 near copy plus translation;GR1;GR2;PH1 '+C,'EU1;EU2;GR2 '+G+';PH1;PH2','EU1 '+G+';EU2;GR1 '+G+';GR2 '+R+';PH1;PH2 '+C,
 'EU1 '+C+';EU2;GR1 '+G+';GR2 '+G+';PH1 '+C+';PH2 '+C,'EU1 mixed language;EU2;GR1;GR2 '+G+';PH1;PH2','EU1;EU2;GR1 '+C+';GR2;PH1;PH2 '+G,'EU1 '+C+';GR1;PH2',
 'EU1 roles changed (one);GR1;GR2 roles changed (one);PH1;PH2','EU1;EU2;GR1;GR2;PH1','EU1;GR1;GR2;PH1;PH2','GR1;GR2 '+G+';PH2 '+C,
 'EU1;EU2;GR1 '+C+';GR2 question;PH1;PH2','EU1;GR1;GR2;PH1;PH2','EU2;GR1 meaning changed (impossible);PH1','EU1;EU2;GR1;GR2 '+G+';PH1 '+C+';PH2',
 'EU1 '+C+';EU2 near copy plus translation;GR1 '+C+';GR2 '+G+';PH1 '+C+';PH2 '+C,'EU1;GR1;GR2;PH1 '+G+';PH2','EU1;EU2 near copy plus addition;GR1 '+R+';PH1',
 'EU1;GR1 '+G+';GR2 '+G+';PH1;PH2','EU1;EU2;GR1;GR2 '+G+';PH1 '+C+';PH2','EU2;GR1;PH1;PH2','GR1 '+G+';GR2 '+C+';PH1;PH2 '+C,'EU1;GR1;PH2 '+R,
 'EU1;GR1 mixed language;GR2;PH1 '+C+';PH2','EU1;GR1;PH1 '+C+';PH2 '+R,'EU1;EU2;GR1 '+G+';GR2 '+G+';PH1;PH2 '+C,'GR1 '+C+';PH1 '+C,'EU1;GR1;GR2 '+G+';PH1;PH2',
 'EU1 model artefact;GR1;GR2 '+G+';PH1;PH2','GR1 '+G+';PH1','EU1;GR1;GR2 '+G+';PH1;PH2 '+C,'EU1;GR1 '+C+';GR2;PH1','EU1;EU2;GR1 '+G+';GR2 '+C+';PH1;PH2 '+C,
 'EU1;EU2;GR1;GR2;PH1 object changed (devices)','EU1 '+R+';GR1;GR2 '+G+';PH1;PH2','EU1;EU2;GR1;GR2;PH1'])}
D.update({('dev',i):d(s) for i,s in enumerate([
 'EU1;GR1;GR2 '+C+';PH1;PH2','EU1;EU2 mixed language;GR1;GR2 '+G+';PH1;PH2 '+R,'EU1;EU2;GR1 '+G+';PH1;PH2 '+C,'GR1 '+C+';PH1 object changed',
 'EU1;EU2;GR1;GR2 '+G+';PH1;PH2 '+C,'EU1;GR1 owner changed;PH1 '+C+';PH2 '+C,'EU1 mixed language;GR1 '+G+';GR2 narrower;PH1 '+G+';PH2 '+C,
 'EU1 statement;GR1 statement;GR2;PH1 statement;PH2','EU1;GR1;PH1','EU1;GR1 mixed language;GR2;PH1;PH2 '+G,'EU1;GR1 '+C+';GR2;PH1;PH2',
 'GR1 '+C+';GR2 '+R+';PH1;PH2 '+R,'EU1 '+R+';GR1 '+G+';GR2 '+G+';PH1;PH2','EU1;EU2 near copy plus translation;GR1 '+G,'EU1;EU2;GR2 '+G+';PH1;PH2',
 'EU1;EU2;GR2 '+G+';PH1;PH2 '+C,'EU1 '+C+';EU2;GR1;GR2 '+G+';PH1;PH2','EU1;GR1 opposite;PH1','GR1 '+G+';PH1','EU1;EU2;GR1;GR2;PH1 '+C+';PH2',
 'EU1;GR1;PH1','EU1;EU2;GR1;GR2 '+G+';PH1 '+C+';PH2','EU1;EU2;GR1;GR2 '+G+';PH1;PH2 '+C,'EU1;GR1;GR2;PH1 '+C+';PH2 '+G,
 'EU1;EU2;GR1 '+G+';GR2 meaning changed (later);PH1;PH2','EU2;GR1 '+G+';GR2 '+C+';PH1','GR1;GR2;PH1;PH2','EU1;GR1;GR2;PH1;PH2',
 'EU1;GR1 roles changed (she);PH1 '+C,'EU1;GR2;PH1 '+C+';PH2 '+C,'EU1;EU2;GR1;GR2 '+G+';PH1;PH2','EU1;EU2;GR1 '+C+';GR2;PH1;PH2',
 'EU1;GR1 '+C+';PH1 '+C,'EU1;GR1;GR2;PH1;PH2 '+G,'EU1;EU2;GR1;GR2 '+C+';PH1;PH2 '+C,'EU1;GR1 '+G+';PH1 '+C+';PH2 '+C,'EU1;GR1;GR2;PH1;PH2',
 'EU1;GR1;GR2;PH1;PH2','EU1;GR1 '+C+';GR2 '+C+';PH1;PH2 '+G,'EU1;GR1 '+C+';GR2 '+C,'EU1;EU2 question;GR1;GR2;PH1;PH2',
 'GR1 '+C+';GR2 near copy plus translation;PH2 '+C,'EU1 object changed;GR1 '+G+';GR2;PH1 '+C+';PH2 question','EU1;EU2;GR1 '+C+';GR2;PH1;PH2 '+G,
 'EU1 '+C+';GR1;GR2 '+C+';PH1 '+C+';PH2','EU1;EU2;GR1;GR2 '+G+';PH1;PH2'])})
DE=re.compile(r"[äöüß]|\b(?:ich|du|dir|dich|mir|mich|nicht|nichts|bitte|meine?n?|die|der|das|und|kein\w*|nie|niemals|ist|zu|sie|ihr|mach\w*|lass\w*|vergiss|wenn|bevor|ohne|frag\w*|sag\w*|zeig\w*|vielleicht|sollst|darfst|kannst|keine|heute|jetzt|wieder|nur|mit)\b",re.I)
def lang(s):return 'de' if len(DE.findall(s))>=1 else 'en'
def n(t):return ' '.join(re.findall(r"[a-zäöüß0-9']+",t.lower()))
def main():
    audit=[];prim=[];sec=[];seen=set();todo=[]
    for r in raw['rows']:
        h=SRC[r['source']][r['index']];key=r['model'][:2]+r['prompt'][1];s=(r['sentence'] or '').strip()
        sim=difflib.SequenceMatcher(None,n(s),n(h['text'])).ratio()
        if not s or sim>=0.85 or set(n(s).split())==set(n(h['text']).split()):dec,why='0','copy or near copy (automatic)'
        elif key in D.get((r['source'],r['index']),{}):dec,why=D[(r['source'],r['index'])][key]
        else:todo.append((r['source'],r['index'],key,s));continue
        if dec=='S' and n(s) in seen:dec,why='0','duplicate of an accepted sentence'
        if dec=='S':dec='1' if lang(s)==h['lang'] else 'L'
        audit.append({'source':r['source'],'index':r['index'],'model':r['model'],'prompt':r['prompt'],'original':h['text'],'sentence':s,'decision':dec,'reason':why})
        if dec in ('1','L'):
            seen.add(n(s));it={k:h[k] for k in ('kind','deny','ask')};it.update(text=s,lang=h['lang'],source=r['model']+'/'+r['prompt'],original=h['text'])
            (prim if dec=='1' else sec).append(it)
    if todo:raise SystemExit('undecided rows: '+repr(todo))
    (HERE/'audit_round4.json').write_text(json.dumps({'schema':'USER_RULES_AUDIT_ROUND4_V1','rows':audit},ensure_ascii=False,indent=1)+'\n')
    (HERE/'cohort_round4.json').write_text(json.dumps({'schema':'USER_RULES_COHORT_ROUND4_V1','cohort':'primary (same meaning, same language)','items':prim},ensure_ascii=False,indent=1)+'\n')
    (HERE/'cohort_round4_langswitch.json').write_text(json.dumps({'schema':'USER_RULES_COHORT_ROUND4_V1','cohort':'secondary (same meaning, language switched; not for the verdict)','items':sec},ensure_ascii=False,indent=1)+'\n')
    from collections import Counter
    print('primary',len(prim),Counter(x['kind'] for x in prim),Counter(x['lang'] for x in prim),'secondary',len(sec),'excluded',sum(a['decision']=='0' for a in audit))
main()
