#!/usr/bin/env python3
"""Round-8 hand audit as data. Decisions written by hand after freeze_v8.json and before any reader saw these sentences.
S = same meaning (primary if German like the source, secondary if the model switched language); 0 = excluded (reason).
Copies, near copies and duplicates are excluded automatically. Labels are inherited from holdout_de5.json."""
import difflib,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
raw=json.loads((HERE/'round8_raw.json').read_text());H=json.loads((HERE/'holdout_de5.json').read_text())['items']
def d(spec):
    out={}
    for part in spec.split(';'):
        k,_,v=part.strip().partition(' ');v=v.strip()
        if k:out[k]=('S','same') if v in ('','S') else ('0',v)
    return out
D={i:d(s) for i,s in enumerate([
 'AF1 garbled;LF1 meaning changed;LF2 garbled;TR1 garbled',
 'AF1 garbled;LF1 weaker (C);LF2 opposite;TR1 garbled',
 'AF1;LF1;LF2 garbled;TR2',
 'AF2;LF1 garbled;LF2 garbled',
 'AF1 meaning changed;AF2 garbled;LF1 garbled;LF2 garbled;TR1 garbled;TR2',
 'AF1;AF2;LF1 roles changed;LF2 garbled;TR1 meaning changed',
 'LF1 meaning changed;LF2 garbled',
 'AF1;LF1;LF2;TR1 garbled',
 'AF1 meaning changed;AF2 meaning changed;LF1;LF2 garbled;TR1;TR2 meaning changed',
 'AF1;LF1 weaker (C);LF2 meaning changed;TR1',
 'AF1 meaning changed;AF2;LF1 meaning changed;LF2 garbled;TR1;TR2',
 'AF1 garbled;AF2 other language;LF1 garbled;LF2 garbled;TR1 garbled;TR2 garbled',
 'AF1 garbled;AF2 other language;LF1;LF2',
 'AF1 garbled;LF1;LF2 garbled;TR1 meaning changed;TR2 meaning changed',
 'AF1 garbled;AF2 garbled;LF1 garbled;LF2 garbled;TR1 garbled',
 'AF1 garbled;LF1;LF2 weaker (C);TR1;TR2 garbled',
 'AF1;AF2 other language;LF1 meaning changed;LF2;TR1 garbled',
 'AF1 garbled;AF2 meaning changed;LF1 garbled;LF2 meaning changed;TR1 garbled',
 'AF1;AF2 meaning changed;LF1 opposite;LF2 garbled;TR2',
 'AF1 meaning changed;AF2;LF1;LF2 garbled;TR1 opposite;TR2',
 'AF1 roles changed;LF1 roles changed;LF2 garbled;TR1 meaning changed',
 'AF1 meaning changed;AF2 other language;LF1;LF2 garbled',
 'AF1 roles changed;AF2 roles changed;LF1 roles changed;LF2 garbled;TR2',
 'AF1;LF1 roles changed;LF2;TR1 meaning changed',
 'AF1 garbled;AF2 garbled;LF1;LF2 garbled;TR1 garbled',
 'AF1;LF1 object changed (C);LF2;TR1 other language',
 'AF1 garbled;AF2 other language;LF1 roles changed;LF2 roles changed;TR1 object changed (C);TR2 other language',
 'AF1 meaning changed;AF2 garbled;LF1 roles changed;LF2 garbled;TR1;TR2',
 'AF1;AF2 garbled;LF1 owner changed (R);LF2 garbled;TR1;TR2',
 'AF1;AF2 roles changed;LF1 roles changed;LF2 garbled;TR1',
 'AF1 garbled;LF1 roles changed;LF2 roles changed;TR1 garbled;TR2',
 'AF1 garbled;AF2 garbled;LF1;LF2;TR1 garbled',
 'LF1 garbled;LF2 roles changed;TR1 roles changed',
 'AF1 meaning changed;LF1;LF2 meaning changed;TR1',
 'AF1;LF1;LF2 garbled;TR1',
 'LF1 meaning changed;LF2 garbled',
 'AF2;LF1;LF2 meaning changed;TR2 meaning changed',
 'AF1;AF2 meaning changed;LF1;LF2 garbled;TR1 garbled',
 'AF1;AF2;LF1;LF2;TR1;TR2',
 'AF1;AF2;LF1;LF2;TR1 garbled',
 'AF1 meaning changed;AF2 other language;LF1;LF2 garbled;TR1',
 'AF1 garbled;AF2 garbled;LF1;LF2 meaning changed;TR1 garbled;TR2',
 'AF1 garbled;LF1;LF2 garbled',
 'AF1;LF1;LF2;TR1 garbled;TR2',
 'AF1 garbled;LF1;LF2 meaning changed;TR1 garbled',
 'AF1;AF2;LF1;LF2 meaning changed;TR1',
 'LF1;LF2 garbled',
 'LF1;LF2 meaning changed',
 'AF1;AF2 garbled;LF1 garbled;LF2 garbled',
 'AF2;LF1;LF2',
 'AF1;AF2 other language;LF1;LF2',
 'AF2;LF2 meaning changed',
 'AF1;AF2 garbled;LF1;LF2',
 'AF1;AF2;LF1;LF2 garbled',
 'AF1;LF1;LF2;TR1',
 'AF1 garbled;LF1;LF2;TR1;TR2',
 'AF1 meaning changed;AF2;LF1;LF2 garbled;TR1;TR2 garbled',
 'AF1 garbled;AF2;LF1;LF2;TR1;TR2',
 'AF1;AF2;LF1;LF2 garbled;TR1',
 'AF1;AF2;LF1;LF2 garbled;TR1'])}
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
    (HERE/'audit_round8.json').write_text(json.dumps({'schema':'USER_RULES_AUDIT_ROUND8_V1','rows':audit},ensure_ascii=False,indent=1)+'\n')
    (HERE/'cohort_round8.json').write_text(json.dumps({'schema':'USER_RULES_COHORT_ROUND8_V1','cohort':'primary (same meaning, German)','items':prim},ensure_ascii=False,indent=1)+'\n')
    (HERE/'cohort_round8_langswitch.json').write_text(json.dumps({'schema':'USER_RULES_COHORT_ROUND8_V1','cohort':'secondary (same meaning, switched to English; not for the verdict)','items':sec},ensure_ascii=False,indent=1)+'\n')
    from collections import Counter
    print('primary',len(prim),Counter(x['kind'] for x in prim),'secondary',len(sec),'excluded',sum(a['decision']=='0' for a in audit))
main()
