#!/usr/bin/env python3
"""Round-7 hand audit as data. Decisions written by hand after freeze_v7.json and before any reader saw these sentences.
S = same meaning (primary if German like the source, secondary if the model switched language); 0 = excluded (reason).
Copies, near copies and duplicates are excluded automatically. Labels are inherited from holdout_de4.json."""
import difflib,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
raw=json.loads((HERE/'round7_raw.json').read_text());H=json.loads((HERE/'holdout_de4.json').read_text())['items']
def d(spec):
    out={}
    for part in spec.split(';'):
        k,_,v=part.strip().partition(' ');v=v.strip()
        if k:out[k]=('S','same') if v in ('','S') else ('0',v)
    return out
D={i:d(s) for i,s in enumerate([
 'AP1;AP2 meaning changed;HU1 garbled;YI1 garbled;YI2 meaning changed',
 'AP1;AP2;HU1 meaning changed;HU2 garbled;YI1',
 'AP1;AP2 meaning changed;HU1 meaning changed;HU2 garbled;YI1 meaning changed;YI2 meaning changed',
 'AP1 roles changed;AP2 roles changed;HU1 garbled;YI1 roles changed',
 'AP1;AP2 weaker (C);HU1;HU2 meaning changed;YI1 meaning changed;YI2 meaning changed',
 'AP1 meaning changed;AP2 opposite;HU1 garbled;YI1',
 'AP1;HU1;HU2 meaning changed;YI1 garbled',
 'AP1;AP2;HU1 garbled;HU2 meaning changed;YI1 garbled;YI2',
 'AP1 roles changed;AP2;HU1 garbled;HU2 other language;YI1 meaning changed;YI2',
 'AP1;AP2 meaning changed;HU1 meaning changed;HU2 garbled;YI1 meaning changed',
 'AP1;AP2 meaning changed;HU1 opposite;HU2 opposite;YI1 garbled',
 'AP1;AP2;HU1 garbled;HU2 garbled;YI1 meaning changed',
 'AP1;AP2;HU1 meaning changed;YI1 meaning changed',
 'AP1;AP2 meaning changed;HU1;HU2 meaning changed;YI1',
 'AP1;AP2 additions;HU1 garbled;HU2 other language;YI1;YI2',
 'AP1 garbled;AP2 weaker (C);HU1 meaning changed;HU2 meaning changed;YI1 garbled',
 'AP1;AP2 meaning changed;HU1 garbled;HU2 meaning changed;YI1;YI2 garbled',
 'AP1;AP2;HU1 garbled;HU2 meaning changed;YI1 meaning changed;YI2 meaning changed',
 'AP1 meaning changed;HU1;HU2 garbled;YI1 question (C);YI2 garbled',
 'AP1 weaker (C);AP2 meaning changed;HU1 meaning changed;HU2 garbled;YI1',
 'AP1;AP2;HU1 meaning changed;YI1;YI2 roles changed',
 'AP1;HU1 meaning changed;HU2 meaning changed;YI1 meaning changed;YI2 meaning changed',
 'AP1;HU1;HU2 garbled;YI1 garbled',
 'AP1;AP2;HU1 meaning changed;YI1 meaning changed;YI2 meaning changed',
 'AP1;AP2;HU1 garbled;HU2 meaning changed;YI1 garbled;YI2 garbled',
 'AP1;AP2;HU1 roles changed;HU2 garbled;YI1',
 'AP1;AP2;HU1 roles changed;HU2 meaning changed;YI1 roles changed',
 'AP2 roles changed;HU1 garbled;HU2 garbled;YI1;YI2 roles changed',
 'AP1;HU1 garbled;HU2 meaning changed;YI1',
 'AP1;AP2 owner changed (R);HU1 garbled;YI1',
 'AP1 object changed (C);AP2;HU1 garbled;HU2 meaning changed;YI1;YI2 meaning changed',
 'AP1 roles changed;AP2;HU1 garbled;HU2 garbled;YI1;YI2 meaning changed',
 'AP1;HU1;YI1;YI2 garbled',
 'AP1 roles changed;AP2;HU1;YI2 garbled',
 'AP1 meaning changed;AP2 roles changed;HU1 meaning changed;HU2 meaning changed;YI1 meaning changed;YI2',
 'AP1 object changed (C);HU1 garbled;HU2 garbled;YI1;YI2 meaning changed',
 'AP1;AP2 meaning changed;HU1 garbled;HU2 meaning changed;YI1;YI2 meaning changed',
 'AP1;AP2 meaning changed;HU1 garbled;HU2 garbled;YI1 meaning changed;YI2 meaning changed',
 'AP1;AP2;HU1;HU2 other language;YI1;YI2 garbled',
 'AP1;AP2 meaning changed;HU1 garbled;HU2 garbled;YI1 garbled',
 'AP1 meaning changed;AP2;HU2 meaning changed;YI1',
 'AP1 meaning changed;AP2 meaning changed;HU2;YI1 meaning changed;YI2 meaning changed',
 'AP1;AP2;HU1;HU2 garbled;YI1 garbled;YI2 meaning changed',
 'AP1;AP2;HU1 garbled;YI1 garbled',
 'AP1;AP2;HU1 meaning changed;HU2 additions;YI1;YI2 meaning changed',
 'AP1;AP2 roles changed;HU1 meaning changed;HU2 meaning changed;YI1;YI2 garbled',
 'AP1 meaning changed;AP2;HU1;HU2 garbled;YI1 meaning changed;YI2 meaning changed',
 'AP1;AP2 roles changed;HU1;HU2;YI1 meaning changed',
 'AP1;AP2;HU1;HU2;YI1 roles changed',
 'AP1 meaning changed;AP2 meaning changed;HU1 meaning changed;HU2 meaning changed;YI1 garbled;YI2 meaning changed',
 'AP1;AP2;HU1;HU2 other language;YI1',
 'AP1;HU1;HU2 meaning changed;YI1',
 'AP1;AP2;HU1 garbled;HU2 meaning changed;YI1 garbled',
 'AP1;AP2;HU1;HU2 garbled;YI2 roles changed',
 'AP1;AP2 meaning changed;HU1 meaning changed;HU2 other language;YI1',
 'AP1;AP2 meaning changed;HU1;HU2 garbled;YI1',
 'AP1;AP2;HU1;HU2 other language;YI1',
 'AP1;AP2 roles changed;HU1 garbled;YI1',
 'AP1 meaning changed;AP2 meaning changed;HU1 meaning changed;HU2 meaning changed;YI1 meaning changed',
 'AP1;AP2 meaning changed;HU1 garbled;HU2 other language;YI1;YI2 garbled'])}
DE=re.compile(r"[äöüß]|\b(?:ich|du|dir|dich|mir|mich|nicht|nichts|bitte|meine?n?|die|der|das|und|kein\w*|nie|niemals|ist|zu|sie|ihr|mach\w*|lass\w*|vergiss|wenn|bevor|ohne|frag\w*|sag\w*|zeig\w*|vielleicht|sollst|darfst|kannst|keine|heute|jetzt|wieder|nur|mit|weg|dem|von)\b",re.I)
def n(t):return ' '.join(re.findall(r"[a-zäöüß0-9']+",t.lower()))
def main():
    audit=[];prim=[];sec=[];seen=set();todo=[]
    for r in raw['rows']:
        h=H[r['index']];key=r['model'][:2]+r['prompt'][1];s=(r['sentence'] or '').strip()
        sim=difflib.SequenceMatcher(None,n(s),n(h['text'])).ratio()
        if not s or sim>=0.85 or set(n(s).split())==set(n(h['text']).split()):dec,why='0','copy or near copy (automatic)'
        elif key in D.get(r['index'],{}):dec,why=D[r['index']][key]
        else:todo.append((r['index'],key,s));continue
        if dec=='S' and n(s) in seen:dec,why='0','duplicate of an accepted sentence'
        if dec=='S':dec='1' if DE.search(s) else 'L'
        audit.append({'index':r['index'],'model':r['model'],'prompt':r['prompt'],'original':h['text'],'sentence':s,'decision':dec,'reason':why})
        if dec in ('1','L'):
            seen.add(n(s));it={k:h[k] for k in ('kind','deny','ask')};it.update(text=s,lang='de',source=r['model']+'/'+r['prompt'],original=h['text'])
            (prim if dec=='1' else sec).append(it)
    if todo:raise SystemExit('undecided rows: '+repr(todo))
    (HERE/'audit_round7.json').write_text(json.dumps({'schema':'USER_RULES_AUDIT_ROUND7_V1','rows':audit},ensure_ascii=False,indent=1)+'\n')
    (HERE/'cohort_round7.json').write_text(json.dumps({'schema':'USER_RULES_COHORT_ROUND7_V1','cohort':'primary (same meaning, German)','items':prim},ensure_ascii=False,indent=1)+'\n')
    (HERE/'cohort_round7_langswitch.json').write_text(json.dumps({'schema':'USER_RULES_COHORT_ROUND7_V1','cohort':'secondary (same meaning, switched to English; not for the verdict)','items':sec},ensure_ascii=False,indent=1)+'\n')
    from collections import Counter
    print('primary',len(prim),Counter(x['kind'] for x in prim),'secondary',len(sec),'excluded',sum(a['decision']=='0' for a in audit))
main()
