"""WP-Z2k exploratory: re-decide recorded STEP2 tool replays with the recency guard and rule_reader='newest_quoted'.

Deterministic, on already recorded extractions (seen data, so only a candidate check, not a confirmation).
Usage: step2_rule_reader_explore.py <report folder with step2_*.json> <tool folder with tool_*.json> [...]
"""
import collections
import glob
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from v13.agi import eligibility as E
import step2_tool_replay as R

def evaluate(reports,tools,excerpt=240):
    c=collections.Counter()
    for tf in sorted(glob.glob(tools+'/tool_*_s*.json')):
        if 'preregistration' in tf:continue
        rep=json.load(open(reports+'/'+Path(tf).name.replace('tool_','step2_')));fx={f['id']:f for f in rep['fixtures']}
        rows={(r['fixture'],r['variant']):r for r in rep['rows']};arm=Path(tf).name.split('tool_')[1].split('_s')[0]
        for x in json.load(open(tf))['rows']:
            f=fx[x['fixture']];ora=f['oracle']['action'];ex=(x.get('tool') or {}).get('extracted');h=[s[:excerpt] for s in f['history']]
            if ex:
                cur,q=R.evidence(rows[(x['fixture'],x['variant'])]['consumer_messages']);rules={k:ex[k] for k in ('budget','deadline','local_only')}
                acts={'guard':E.decide(rules,ex['options'],cur,q,history=h)['action'],'reader':E.decide(rules,ex['options'],cur,q,history=h,rule_reader='newest_quoted')['action']}
            else:acts={'guard':R.action_of(x),'reader':R.action_of(x)}
            for k,a in acts.items():
                c[(arm,k,'exact')]+=a==ora;c[(arm,k,'wrong')]+=a in ('A','B','NONE') and a!=ora
                if f.get('type') in ('REVISED','TWICE'):c[(arm,k,'changed_exact')]+=a==ora
    return {f'{k[0]}:{k[1]}:{k[2]}':v for k,v in sorted(c.items())}

if __name__=='__main__':
    a=sys.argv[1:]
    for reports,tools in zip(a[::2],a[1::2]):print(Path(tools).name,json.dumps(evaluate(reports,tools)))
