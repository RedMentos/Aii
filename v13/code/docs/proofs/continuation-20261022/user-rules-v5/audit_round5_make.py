#!/usr/bin/env python3
"""Round-5 hand audit as data. Decisions written by hand after freeze_v5.json and before any reader saw these sentences.
S = same meaning (primary if German like the source, secondary if the model switched language); 0 = excluded (reason).
Copies, near copies and duplicates are excluded automatically. Labels are inherited from holdout_de2.json."""
import difflib,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
raw=json.loads((HERE/'round5_raw.json').read_text());H=json.loads((HERE/'holdout_de2.json').read_text())['items']
G='garbled';C='meaning changed';R='roles changed'
def d(spec):
    out={}
    for part in spec.split(';'):
        k,_,v=part.strip().partition(' ');v=v.strip()
        if k:out[k]=('S','same') if v in ('','S') else ('0',v)
    return out
D={i:d(s) for i,s in enumerate([
 'FA1;FA2 '+C+';MI1;MI2 weaker (try);OL1 opposite;OL2 '+G,'FA1;FA2 statement;MI1 '+G+';MI2;OL1 '+C+';OL2 additions','FA1 '+G+';FA2 '+C+';MI1;MI2 '+G+';OL1 '+G+';OL2',
 'FA1 '+G+';FA2;MI1;MI2 '+G+';OL1;OL2 '+G,'FA1 '+G+';FA2 '+C+';MI1;MI2 '+C+';OL1 narrower (search)','FA1 '+G+';FA2 '+G+';MI1;MI2 '+G+';OL1 object lost;OL2',
 'FA1;FA2;MI1 statement;MI2;OL2 '+G,'FA1 '+C+';FA2 '+C+';MI1 '+C+';MI2;OL1 '+C+';OL2','FA1 '+R+';FA2 '+C+';MI1 '+C+';MI2;OL1 owner changed;OL2',
 'FA1 '+G+';FA2 '+C+';MI1 '+G+';MI2;OL1 '+G+';OL2','FA1;FA2 '+R+';MI1;MI2 '+G+';OL1 owner changed;OL2 owner changed','FA1;FA2;MI1;MI2 '+C,
 'FA1 '+G+';FA2;MI1;MI2;OL2','FA1 '+G+';FA2;MI1 unclear fragment;MI2 '+G+';OL1 unclear fragment;OL2 '+C,'FA1 '+G+';FA2 '+G+';MI1;MI2 '+C+';OL1 '+C+';OL2 '+G,
 'FA1;FA2;MI1;MI2 '+G+';OL1;OL2','FA1 '+G+';FA2 '+G+';MI1;MI2;OL1 '+G+';OL2 '+G,'FA1;FA2;MI1;MI2 '+G+';OL1 opposite;OL2 '+G,'FA1 '+G+';FA2 '+G+';MI1;MI2 roles changed (we);OL1',
 'FA1;FA2 '+C+';MI1;MI2 '+G+';OL1','FA1 '+G+';FA2;MI1;MI2 '+G+';OL2','FA1 '+G+';FA2 '+C+';MI1 '+C+';MI2 '+R+';OL1;OL2','FA1;MI1 opposite;MI2 '+G+';OL1',
 'FA1;FA2;MI1;MI2 '+G+';OL1;OL2 '+G,'FA1 '+G+';FA2 '+C+';MI1;MI2;OL1;OL2','FA1;FA2;MI1 near copy plus addition;MI2 '+C+';OL2 '+C,'FA1 '+G+';FA2;MI1;MI2 '+C+';OL1',
 'FA1 '+G+';FA2;MI1;MI2 '+G+';OL1','FA1 '+G+';FA2 '+G+';MI1 '+C+';MI2 '+G+';OL1;OL2','FA1;FA2 '+R+';MI1 owner changed;MI2;OL1 '+G+';OL2','FA1;FA2;MI1;MI2 '+G+';OL1;OL2 stronger',
 'FA1;FA2;MI1 '+C+';MI2;OL1;OL2','FA1 '+G+';FA2 '+G+';MI1 '+C+';MI2 '+G+';OL1 '+R+';OL2 '+C,'FA1 '+G+';FA2 '+C+';MI1 '+G+';MI2;OL1 '+C+';OL2 '+C,
 'FA1 '+G+';MI1 '+G+';MI2 near copy plus addition;OL2','FA1 '+C+';FA2;MI1;MI2;OL1;OL2 '+G,'FA1;FA2;MI1;MI2;OL1;OL2','FA1;FA2 '+C+';MI1 '+G+';MI2;OL1 '+C+';OL2 '+C,
 'FA1;FA2;MI1 owner changed;MI2 '+G+';OL1;OL2 '+G,'FA1 '+G+';MI1;MI2;OL1','MI1;MI2 '+G+';OL1','FA1 '+G+';FA2 '+G+';MI1;MI2 '+G+';OL1 '+C+';OL2 '+C,
 'FA1;FA2 '+C+';MI1;MI2 '+G+';OL1','FA1;FA2;MI1 '+C+';MI2 '+G+';OL1 '+G+';OL2 '+G,'FA1 '+G+';MI1;MI2;OL1 '+C+';OL2','FA1 '+G+';FA2;MI1;MI2;OL2 additions'])}
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
    (HERE/'audit_round5.json').write_text(json.dumps({'schema':'USER_RULES_AUDIT_ROUND5_V1','rows':audit},ensure_ascii=False,indent=1)+'\n')
    (HERE/'cohort_round5.json').write_text(json.dumps({'schema':'USER_RULES_COHORT_ROUND5_V1','cohort':'primary (same meaning, German)','items':prim},ensure_ascii=False,indent=1)+'\n')
    (HERE/'cohort_round5_langswitch.json').write_text(json.dumps({'schema':'USER_RULES_COHORT_ROUND5_V1','cohort':'secondary (same meaning, switched to English; not for the verdict)','items':sec},ensure_ascii=False,indent=1)+'\n')
    from collections import Counter
    print('primary',len(prim),Counter(x['kind'] for x in prim),'secondary',len(sec),'excluded',sum(a['decision']=='0' for a in audit))
main()
