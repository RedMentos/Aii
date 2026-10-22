#!/usr/bin/env python3
"""Round-6 hand audit as data. Decisions written by hand after freeze_v6.json and before any reader saw these sentences.
S = same meaning (primary if German like the source, secondary if the model switched language); 0 = excluded (reason).
Copies, near copies and duplicates are excluded automatically. Labels are inherited from holdout_de3.json."""
import difflib,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
raw=json.loads((HERE/'round6_raw.json').read_text());H=json.loads((HERE/'holdout_de3.json').read_text())['items']
def d(spec):
    out={}
    for part in spec.split(';'):
        k,_,v=part.strip().partition(' ');v=v.strip()
        if k:out[k]=('S','same') if v in ('','S') else ('0',v)
    return out
D={i:d(s) for i,s in enumerate([
 'QW1;QW2 garbled;EX1;EX2 meaning changed;GL1 question (C);GL2 owner changed (R)',
 'QW1;QW2;EX1 garbled;EX2 weaker question (C);GL1;GL2',
 'QW1;QW2;EX1 garbled;EX2 meaning changed;GL1 garbled;GL2 garbled',
 'QW1;QW2 roles changed;EX1 meaning changed;EX2;GL1 roles changed;GL2',
 'QW2;EX1;EX2;GL1;GL2',
 'QW1;QW2 roles changed;EX1 garbled;EX2;GL1 garbled;GL2',
 'QW1 meaning changed;QW2 meaning changed;EX1;EX2 meaning changed;GL1 meaning changed;GL2 meaning changed',
 'QW1;QW2 meaning changed;EX1 meaning changed;EX2 meaning changed;GL1 meaning changed;GL2 meaning changed',
 'QW1;QW2;EX1 meaning changed;EX2 meaning changed;GL1;GL2',
 'QW1;QW2;EX1 opposite;EX2;GL1;GL2',
 'QW1 meaning changed;QW2 meaning changed;EX1 meaning changed;EX2 meaning changed;GL1 meaning changed;GL2',
 'QW1 meaning changed;QW2 meaning changed;EX1 meaning changed;EX2 garbled;GL1 meaning changed;GL2 weaker (C)',
 'QW1;QW2 weaker (lieber);EX1;EX2 meaning changed;GL1;GL2 meaning changed',
 'QW1 garbled;QW2 meaning changed;EX1 opposite;EX2 opposite;GL1 meaning changed;GL2 meaning changed',
 'QW1 meaning changed;QW2;EX1 garbled;EX2 garbled;GL1;GL2 garbled',
 'QW1;QW2;EX1;EX2 meaning changed;GL1;GL2',
 'QW1 roles changed;QW2 meaning changed;EX1 garbled;EX2 meaning changed;GL1;GL2 roles changed',
 'QW1;QW2;EX1;EX2 meaning changed;GL1;GL2',
 'QW1 garbled;QW2;EX1 garbled;EX2 meaning changed;GL1;GL2 garbled',
 'QW1;QW2 garbled;EX1;EX2;GL1 meaning changed;GL2 owner changed (R)',
 'QW1;QW2;EX1;EX2 garbled;GL1;GL2',
 'QW1;EX1 meaning changed;EX2 meaning changed;GL1;GL2',
 'QW2 garbled;EX1 garbled;EX2 garbled;GL1 garbled;GL2',
 'QW1;QW2 meaning changed;EX1 garbled;EX2 meaning changed;GL1 weaker (C);GL2',
 'QW1;QW2;EX1 meaning changed;EX2 meaning changed;GL1;GL2 garbled',
 'QW1 object changed (C);QW2;EX1 object changed (C);EX2;GL1;GL2',
 'QW1;QW2;EX1;EX2;GL1;GL2',
 'QW1;QW2;EX1 garbled;EX2 meaning changed;GL1 garbled;GL2',
 'QW1 roles changed;QW2;EX1 garbled;EX2;GL1;GL2',
 'QW1;EX1 roles changed;EX2;GL1;GL2',
 'QW1 garbled;QW2;EX1 garbled;EX2;GL1 garbled',
 'QW1 garbled;QW2 roles changed;EX1 garbled;EX2 meaning changed;GL1 garbled;GL2',
 'QW1;QW2 garbled;EX1;EX2 meaning changed;GL1;GL2',
 'QW1;EX1 garbled;EX2 garbled;GL1;GL2',
 'QW1;QW2 meaning changed;EX1 meaning changed;EX2 meaning changed;GL1;GL2 meaning changed',
 'QW1;QW2;EX1;EX2 garbled;GL2',
 'QW2 garbled;EX1;EX2 garbled;GL1 opposite;GL2 garbled',
 'QW1;QW2 stronger (C);EX1;EX2 stronger (C);GL1;GL2 garbled',
 'QW1;EX1 meaning changed;EX2 meaning changed;GL1;GL2',
 'QW1;QW2;EX1;EX2 meaning changed;GL1',
 'QW1;EX1 garbled;EX2;GL1;GL2',
 'QW1 garbled;QW2 meaning changed;EX1 garbled;EX2 garbled;GL1;GL2',
 'QW1;QW2;EX1 meaning changed;EX2;GL1;GL2',
 'QW1;QW2;EX1;EX2 garbled;GL1;GL2',
 'QW1;QW2;EX1;EX2 garbled;GL1;GL2',
 'QW1;QW2;EX1;EX2 garbled;GL1;GL2',
 'QW1;QW2;EX1;EX2 garbled;GL1;GL2',
 'QW1;QW2 meaning changed;EX1 garbled;EX2 garbled;GL1;GL2',
 'QW2;EX1;EX2;GL1;GL2',
 'QW1;QW2 meaning changed;EX1 garbled;EX2;GL1;GL2 other language',
 'QW1;QW2;EX1 garbled;EX2 meaning changed;GL1;GL2',
 'QW1;QW2;EX1 meaning changed;EX2;GL1;GL2 additions (C)',
 'QW1;QW2 meaning changed;EX1;EX2 meaning changed;GL1 meaning changed;GL2',
 'QW1 garbled;QW2 meaning changed;EX1 meaning changed;EX2 meaning changed;GL1 roles changed;GL2 opposite',
 'QW1;QW2 question (C);EX1;EX2 question (C);GL1;GL2',
 'QW1;QW2 meaning changed;EX1;EX2;GL1 garbled;GL2',
 'QW1;QW2 garbled;EX1;EX2 meaning changed;GL1;GL2 meaning changed',
 'QW1 meaning changed;QW2 meaning changed;EX1 meaning changed;EX2 meaning changed;GL1 meaning changed;GL2',
 'QW1;QW2 meaning changed;EX1;EX2 roles changed;GL1',
 'QW1;QW2 meaning changed;EX1;EX2;GL1;GL2 meaning changed'])}
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
    (HERE/'audit_round6.json').write_text(json.dumps({'schema':'USER_RULES_AUDIT_ROUND6_V1','rows':audit},ensure_ascii=False,indent=1)+'\n')
    (HERE/'cohort_round6.json').write_text(json.dumps({'schema':'USER_RULES_COHORT_ROUND6_V1','cohort':'primary (same meaning, German)','items':prim},ensure_ascii=False,indent=1)+'\n')
    (HERE/'cohort_round6_langswitch.json').write_text(json.dumps({'schema':'USER_RULES_COHORT_ROUND6_V1','cohort':'secondary (same meaning, switched to English; not for the verdict)','items':sec},ensure_ascii=False,indent=1)+'\n')
    from collections import Counter
    print('primary',len(prim),Counter(x['kind'] for x in prim),'secondary',len(sec),'excluded',sum(a['decision']=='0' for a in audit))
main()
