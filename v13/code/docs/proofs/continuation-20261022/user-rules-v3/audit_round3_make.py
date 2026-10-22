#!/usr/bin/env python3
"""Round-3 hand audit as data. Decisions written by hand after freeze_v3.json and before reader v3 (or v2) saw any of
these sentences. 1 = same meaning, same language -> primary cohort (decides the verdict). L = same meaning, but the model
switched the language (PREREG excludes these; reported only as a secondary cohort). 0 = excluded (reason given).
Copies/near copies are excluded automatically. Labels are inherited from the holdout sentence."""
import difflib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
raw=json.loads((HERE/'round3_raw.json').read_text());H=json.loads((HERE.parents[1]/'continuation-20261021/user-rules/holdout_author.json').read_text())['items']
A=1;L='L'
D={
0:{'GE1':(A,'same (records = notes)'),'GE2':(A,'same, broader'),'LL1':(A,'same'),'LL2':(A,'same, request form'),'SM1':(0,'weaker: only a hope'),'SM2':(A,'same')},
1:{'GE1':(L,'same'),'GE2':(L,'same'),'LL1':(L,'same'),'LL2':(0,'opposite / garbled'),'SM1':(L,'same'),'SM2':(L,'same')},
2:{'GE1':(L,'same'),'GE2':(L,'same'),'LL1':(L,'same'),'LL2':(L,'same, broader'),'SM2':(0,'near copy plus added question')},
3:{'GE1':(A,'same'),'GE2':(A,'same'),'LL1':(A,'same'),'LL2':(A,'same (tell me before)'),'SM1':(A,'same (typo)')},
4:{'GE1':(L,'same'),'GE2':(A,'same, polite'),'LL1':(L,'same'),'LL2':(L,'same'),'SM1':(L,'same')},
5:{'GE1':(A,'same'),'GE2':(A,'same, broader'),'LL1':(0,'roles changed (admin)'),'LL2':(A,'same'),'SM1':(0,'question, meaning changed'),'SM2':(A,'same')},
6:{'GE1':(A,'same'),'GE2':(A,'same, polite'),'LL1':(A,'same'),'LL2':(A,'same'),'SM1':(A,'same'),'SM2':(A,'same, request form')},
7:{'GE1':(L,'same'),'GE2':(L,'same'),'LL1':(L,'same'),'LL2':(L,'same'),'SM1':(L,'same')},
8:{'GE1':(0,'meaning changed (log in)'),'GE2':(A,'same'),'LL1':(A,'same'),'LL2':(0,'roles swapped'),'SM2':(A,'same')},
9:{'GE1':(L,'same'),'GE2':(L,'same'),'LL1':(L,'same'),'LL2':(L,'same'),'SM1':(L,'same'),'SM2':(A,'same')},
10:{'GE1':(A,'same'),'GE2':(0,'roles changed (remind me)'),'LL2':(A,'same'),'SM1':(A,'same'),'SM2':(A,'same')},
11:{'GE1':(L,'same'),'GE2':(L,'same'),'LL1':(L,'same'),'LL2':(L,'same'),'SM1':(L,'same'),'SM2':(L,'same')},
12:{'GE1':(A,'same'),'GE2':(A,'same'),'LL1':(A,'same'),'LL2':(A,'same'),'SM1':(A,'same')},
13:{'GE1':(A,'same'),'GE2':(A,'same'),'LL1':(A,'same')},
14:{'GE1':(L,'same'),'GE2':(L,'same'),'SM1':(L,'same')},
15:{'GE1':(A,'same'),'GE2':(A,'same'),'LL1':(0,'garbled'),'SM1':(A,'same')},
16:{'GE1':(0,'numbers changed'),'GE2':(A,'same'),'LL1':(A,'same'),'LL2':(A,'same')},
17:{'GE1':(A,'same'),'GE2':(A,'same'),'LL1':(A,'same'),'LL2':(A,'same'),'SM1':(A,'same')},
18:{'GE1':(L,'same'),'GE2':(L,'same'),'LL1':(L,'same'),'SM1':(L,'same'),'SM2':(L,'same')},
19:{'GE1':(A,'same'),'GE2':(A,'same'),'LL1':(0,'roles changed (owner of the files)'),'LL2':(A,'same'),'SM1':(A,'same'),'SM2':(A,'same')},
20:{'GE1':(L,'same'),'GE2':(L,'same'),'LL1':(0,'question about the past'),'LL2':(A,'same, request form'),'SM1':(0,'garbled roles')},
21:{'GE1':(A,'same'),'GE2':(0,'before dropped'),'LL1':(A,'same'),'LL2':(A,'same'),'SM1':(A,'same'),'SM2':(A,'same')},
22:{'GE1':(L,'same'),'GE2':(0,'always/beforehand dropped'),'LL1':(L,'same'),'LL2':(L,'same'),'SM1':(L,'same')},
23:{'GE1':(L,'same'),'GE2':(L,'same'),'LL1':(L,'same'),'LL2':(0,'literal, garbled'),'SM1':(0,'meaning changed'),'SM2':(L,'same')},
24:{'GE1':(A,'same'),'GE2':(0,'meaning changed (look)'),'LL1':(A,'same'),'LL2':(A,'same'),'SM1':(A,'same'),'SM2':(A,'same')},
25:{'GE1':(A,'same'),'GE2':(0,'garbled, roles swapped'),'LL1':(A,'same'),'LL2':(A,'same'),'SM1':(0,'opposite'),'SM2':(A,'same')},
26:{'GE1':(L,'same'),'GE2':(L,'same'),'LL1':(0,'opposite'),'LL2':(0,'garbled'),'SM1':(L,'same'),'SM2':(L,'same')},
27:{'GE1':(A,'same'),'GE2':(A,'same'),'LL1':(A,'same'),'LL2':(A,'same'),'SM1':(A,'same'),'SM2':(A,'same')},
28:{'GE1':(A,'same'),'GE2':(A,'same'),'LL1':(A,'same'),'LL2':(0,'wrong language'),'SM1':(A,'same'),'SM2':(0,'stronger: hedge dropped')},
29:{'GE1':(L,'same'),'GE2':(L,'same'),'LL1':(L,'same'),'LL2':(0,'object lost'),'SM1':(L,'same'),'SM2':(L,'same')},
30:{'GE1':(0,'roles changed (tells me)'),'GE2':(A,'same'),'LL1':(A,'same'),'LL2':(0,'meaning changed'),'SM1':(A,'same'),'SM2':(0,'no instruction')},
31:{'GE1':(L,'same'),'GE2':(L,'same'),'LL1':(L,'same'),'LL2':(L,'same'),'SM1':(L,'same')},
32:{'GE1':(A,'same'),'GE2':(A,'same'),'LL1':(0,'owner changed'),'LL2':(0,'roles swapped'),'SM1':(A,'same'),'SM2':(A,'same')},
33:{'GE1':(L,'same'),'GE2':(0,'question/request'),'LL1':(L,'same'),'LL2':(L,'same'),'SM1':(L,'same'),'SM2':(0,'garbled')},
34:{'GE1':(0,'install lost'),'GE2':(0,'install lost'),'LL1':(0,'meaning changed'),'LL2':(A,'same'),'SM1':(0,'meaning changed'),'SM2':(A,'same')},
35:{'GE1':(A,'same, broader'),'GE2':(0,'mixed language'),'LL2':(0,'wrong language'),'SM1':(A,'same'),'SM2':(A,'same')},
36:{'GE1':(L,'same'),'GE2':(L,'same'),'LL1':(L,'same'),'LL2':(L,'same'),'SM1':(L,'same'),'SM2':(L,'same')},
37:{'GE1':(A,'same'),'GE2':(0,'meaning changed (read)'),'LL1':(A,'broader'),'LL2':(0,'garbled'),'SM1':(A,'same')},
38:{'GE1':(0,'meaning changed'),'GE2':(0,'meaning changed'),'LL1':(0,'meaning changed'),'LL2':(0,'meaning changed'),'SM1':(0,'meaning changed'),'SM2':(0,'meaning changed')},
39:{'GE1':(A,'same'),'GE2':(A,'same'),'LL1':(A,'same'),'LL2':(0,'meaning changed'),'SM1':(A,'same, polite'),'SM2':(A,'same')},
40:{'GE1':(L,'same'),'GE2':(A,'same'),'LL1':(L,'same'),'LL2':(L,'same'),'SM1':(L,'same'),'SM2':(0,'roles swapped')},
41:{'GE1':(A,'same'),'GE2':(A,'same'),'LL1':(A,'same'),'LL2':(A,'same'),'SM1':(A,'same')},
42:{'GE1':(0,'meaning changed'),'GE2':(A,'same'),'LL1':(0,'garbled'),'LL2':(A,'same'),'SM1':(A,'same'),'SM2':(A,'same')},
43:{'GE1':(L,'same'),'GE2':(L,'same'),'LL1':(L,'same'),'LL2':(L,'same'),'SM1':(L,'same')},
44:{'GE1':(A,'same'),'GE2':(A,'same'),'LL1':(A,'same'),'LL2':(A,'same'),'SM1':(A,'same'),'SM2':(A,'same')},
45:{'GE1':(L,'same'),'GE2':(L,'same'),'LL1':(L,'same'),'LL2':(L,'same'),'SM1':(L,'same'),'SM2':(L,'same')},
46:{'GE1':(A,'same'),'GE2':(A,'same'),'LL1':(A,'same'),'LL2':(A,'same, request form'),'SM1':(A,'same'),'SM2':(0,'weaker: preference')},
47:{'GE1':(L,'same'),'GE2':(L,'same'),'LL1':(L,'same'),'LL2':(L,'same'),'SM1':(L,'same'),'SM2':(L,'same')},
48:{'GE1':(A,'same'),'GE2':(A,'same'),'LL1':(A,'same'),'LL2':(A,'same'),'SM1':(A,'same'),'SM2':(A,'same')},
49:{'GE1':(L,'same'),'GE2':(L,'same'),'SM1':(L,'same')},
50:{'GE1':(A,'same (label case)'),'GE2':(A,'same'),'LL1':(A,'same'),'LL2':(0,'wrong language'),'SM1':(A,'same'),'SM2':(A,'same')},
51:{'GE1':(A,'same'),'GE2':(0,'mixed language'),'LL1':(A,'same'),'LL2':(A,'same'),'SM1':(A,'same'),'SM2':(A,'same')},
52:{'GE1':(L,'same'),'GE2':(A,'same'),'LL1':(L,'same'),'SM1':(L,'same')},
53:{'GE1':(A,'same'),'GE2':(0,'roles changed'),'LL1':(0,'roles changed'),'LL2':(0,'roles changed'),'SM1':(A,'same')},
54:{'GE1':(L,'same'),'GE2':(L,'same'),'LL1':(0,'garbled'),'LL2':(0,'garbled'),'SM1':(L,'same')},
55:{'GE1':(A,'same'),'GE2':(A,'same'),'LL1':(A,'same'),'LL2':(A,'same'),'SM1':(A,'same'),'SM2':(A,'same')},
56:{'GE1':(L,'same'),'GE2':(L,'same'),'LL1':(A,'same'),'SM1':(L,'same'),'SM2':(L,'same')},
57:{'GE1':(A,'same'),'GE2':(A,'same'),'LL1':(A,'same'),'LL2':(0,'wrong language'),'SM1':(0,'question'),'SM2':(A,'same')},
58:{'GE1':(L,'same'),'GE2':(L,'same'),'LL1':(L,'same'),'LL2':(L,'same'),'SM1':(L,'same'),'SM2':(A,'same')},
}
def n(t):return ' '.join(re.findall(r"[a-zäöüß0-9']+",t.lower()))
def main():
    audit=[];prim=[];sec=[];seen=set();todo=[]
    for r in raw['rows']:
        i=r['index'];key=r['model'][:2]+r['prompt'][1];h=H[i];s=r['sentence'] or ''
        sim=difflib.SequenceMatcher(None,n(s),n(h['text'])).ratio()
        if not s or sim>=0.85 or set(n(s).split())==set(n(h['text']).split()):dec,why='0','copy or near copy (automatic)'
        elif key in D.get(i,{}):dec,why=D[i][key];dec=str(dec)
        else:todo.append((i,key,s));continue
        dup=n(s) in seen and dec!='0'
        if dup:dec,why='0','duplicate of an accepted sentence'
        audit.append({'index':i,'model':r['model'],'prompt':r['prompt'],'original':h['text'],'sentence':s,'decision':dec,'reason':why})
        if dec in ('1','L'):
            seen.add(n(s));it={k:h[k] for k in ('kind','deny','ask')};it.update(text=s,lang=h['lang'],source=r['model']+'/'+r['prompt'],original=h['text'])
            (prim if dec=='1' else sec).append(it)
    if todo:raise SystemExit('undecided rows: '+repr(todo))
    (HERE/'audit_round3.json').write_text(json.dumps({'schema':'USER_RULES_AUDIT_ROUND3_V1','rows':audit},ensure_ascii=False,indent=1)+'\n')
    (HERE/'cohort_round3.json').write_text(json.dumps({'schema':'USER_RULES_COHORT_ROUND3_V1','cohort':'primary (same meaning, same language)','items':prim},ensure_ascii=False,indent=1)+'\n')
    (HERE/'cohort_round3_langswitch.json').write_text(json.dumps({'schema':'USER_RULES_COHORT_ROUND3_V1','cohort':'secondary (same meaning, model switched the language; not for the verdict)','items':sec},ensure_ascii=False,indent=1)+'\n')
    from collections import Counter
    print('primary',len(prim),Counter(x['kind'] for x in prim),'secondary',len(sec),'excluded',sum(a['decision']=='0' for a in audit))
main()
