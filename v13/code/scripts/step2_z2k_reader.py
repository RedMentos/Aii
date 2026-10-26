"""WP-Z2k: read rule values deterministically as the newest quoted value (eligibility rule_reader='newest_quoted').

WP-Z2j (scripts/step2_z2j_sources.py): with whole earlier sources as B2 choices the rules reach C3 (B2 rule rate .71),
but on changed rules C3 (LFM2.5-350M) took the superseded value in 10/10 rows; the recency guard made them UNKNOWN.
An exploratory reader on recorded data (scripts/step2_rule_reader_explore.py, seen data) lifted S4 exact 22 -> 48/210
with 0 wrong. Here the confirmation on fresh episodes, new seeds 38-40:
  REVISED 6, TWICE 2, CONFIRM 2 (all never run before)
Arms A4 (pointer, all sentences, 4 slots) and S4 (pointer, whole earlier sources), b2_context_chars=1536. Every recorded
extraction is re-decided three times: guard off (consistency), guard on, guard on + newest_quoted reader.
Preregistration: docs/proofs/continuation-20261026/step2-z2k-reader/PREREG.md. Diagnosis only (Linux cloud, no Redmi).
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
from v13.agi import eligibility as E

def _private(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

i=_private('step2_z2i_for_z2k','scripts/step2_z2i_choices.py')
h,g,z=i.h,i.g,i.z
SEEDS=(38,39,40)
CHOICES={'A4':'all','S4':'sources'}
ARMS={a:('C','pointer') for a in CHOICES}
PRIMARY='S4'
TYPES=('REVISED','TWICE','CONFIRM')

EPISODES=[
 ('Kaus','REVISED',(70,5,True),(75,3,True),(65,6,True),[('budget',80)]),
 ('Lucida','REVISED',(95,6,True),(55,4,True),(85,5,True),[('budget',50)]),
 ('Maia','REVISED',(80,3,False),(50,5,False),(70,3,True),[('deadline',5)]),
 ('Nekkar','REVISED',(100,7,True),(60,7,True),(90,4,True),[('deadline',5)]),
 ('Peacock','REVISED',(90,5,False),(45,4,False),(80,4,True),[('local_only',True)]),
 ('Rukbat','REVISED',(85,6,True),(40,5,False),(75,5,True),[('local_only',False)]),
 ('Sargas','TWICE',(100,5,True),(50,7,True),(80,4,True),[('deadline',8),('deadline',3)]),
 ('Thuban','TWICE',(90,4,True),(60,6,True),(75,4,True),[('deadline',6),('deadline',2)]),
 ('Vindemiatrix','CONFIRM',(80,5,True),(75,4,True),(60,5,True),[('budget',80)]),
 ('Zosma','CONFIRM',(95,4,False),(85,4,False),(90,3,True),[('deadline',4)]),
]

FIXTURES=[h.episode(*x) for x in EPISODES]
FIX={f['id']:f for f in FIXTURES}
for m in (i,h,g):m.FIX=FIX;m.FIXTURES=FIXTURES
z.FIXTURES=FIXTURES;z.z2.FIXTURES=FIXTURES;z.FIX=FIX;z.HARD=[f['id'] for f in FIXTURES];z.HARD_TYPES=TYPES;g.HARD_TYPES=TYPES;i.TYPES=TYPES
z.ARMS.clear();z.ARMS.update(ARMS);z.z2b.ARMS.clear()
for _arm,(_base,_) in ARMS.items():z.z2b.ARMS[_arm]={'base':_base,'query':True}
z.SEEDS=SEEDS;z.z2b.SEEDS=SEEDS;g.SEEDS=SEEDS;h.SEEDS=SEEDS;i.SEEDS=SEEDS
h.ARMS=ARMS;h.SLOTS={a:4 for a in ARMS};i.ARMS=ARMS;i.CHOICES=CHOICES

def reader_pairs(report,tool):
    """Guard-on and guard-on + newest_quoted actions for every recorded row (same rows, deterministic)."""
    import step2_tool_replay as replay
    rows={(r['fixture'],r['variant']):r for r in report['rows']};out=[]
    for x in tool['rows']:
        f=FIX[x['fixture']];ex=(x.get('tool') or {}).get('extracted');hist=g.history_of(f)
        if ex:
            cur,q=replay.evidence(rows[(x['fixture'],x['variant'])]['consumer_messages']);rules={k:ex[k] for k in g.KEYS}
            on=E.decide(rules,ex['options'],cur,q,history=hist);rd=E.decide(rules,ex['options'],cur,q,history=hist,rule_reader='newest_quoted')
            on_a,rd_a,read=on['action'],rd['action'],rd['read_newest']
        else:on_a=rd_a=replay.action_of(x);read=[]
        out.append({'fixture':x['fixture'],'variant':x['variant'],'type':f['type'],'oracle':f['oracle']['action'],'on':on_a,'reader':rd_a,'read_newest':read})
    return out

def run(installed,work,arm,seed):
    from v13.common import atomic_write,file_hash
    summary=i.run(installed,work,arm,seed);rid=z.z2b.run_id(arm,seed)
    report=json.loads((Path(work)/('step2_'+rid+'.json')).read_text());tool=json.loads((Path(work)/('tool_'+rid+'.json')).read_text())
    pairs=reader_pairs(report,tool)
    summary['z2k']={'pairs':pairs,'on':g.tally(pairs,'on'),'reader':g.tally(pairs,'reader'),
                    'source_sha256':{str(p.relative_to(ROOT)):file_hash(p) for p in (Path(__file__).resolve(),ROOT/'v13/agi/eligibility.py')}}
    atomic_write(Path(work)/('summary_'+rid+'.json'),json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

def ep_exact(runs,arm,key,fid):return sum(p[key]==p['oracle'] for s in SEEDS for p in runs[(arm,s)]['z2k']['pairs'] if p['fixture']==fid)/len(SEEDS)

def gate(runs):
    """Preregistered decision (PREREG.md)."""
    need=[(a,s) for a in ARMS for s in SEEDS]
    if any(k not in runs for k in need):return {'status':'INCOMPLETE','missing':[z.z2b.run_id(*k) for k in need if k not in runs]}
    ids=[f['id'] for f in FIXTURES]
    pairs={a:[p for s in SEEDS for p in runs[(a,s)]['z2k']['pairs']] for a in ARMS}
    structural=all(r['tool_status']!='STRUCTURAL_FAIL' and r['step2_status']!='DIAGNOSTIC_INCOMPLETE' for r in runs.values())
    consistent=all(runs[k]['z2g']['consistent'] for k in need)
    share={a:sum(runs[(a,s)]['z2g']['validity']['kickoff_in_context'] for s in SEEDS)/max(1,sum(runs[(a,s)]['z2g']['validity']['offers'] for s in SEEDS)) for a in ARMS}
    wrong={a:{k:g.tally(pairs[a],k)['wrong'] for k in ('on','reader')} for a in ARMS}
    lost={a:[p for p in pairs[a] if p['on']==p['oracle'] and p['reader']!=p['oracle']] for a in ARMS}
    ci=z.z2b.cluster_ci([[ep_exact(runs,PRIMARY,'reader',f)-ep_exact(runs,PRIMARY,'on',f)] for f in ids])
    exact={a:{k:g.tally(pairs[a],k)['exact'] for k in ('on','reader')} for a in ARMS}
    if not (structural and consistent):status='Z2K_INVALID'
    elif min(share.values())<g.VALID_SHARE:status='Z2K_NOT_TESTABLE'
    elif any(w['reader'] for w in wrong.values()):status='Z2K_UNSAFE'
    elif ci['ci95'][0]>0 and not lost[PRIMARY]:status='Z2K_READER_CONFIRMED'
    elif exact[PRIMARY]['reader']>exact[PRIMARY]['on']:status='Z2K_READER_PARTIAL'
    else:status='Z2K_READER_NO_GAIN'
    def by(a,key,t):return g.tally([p for p in pairs[a] if p['type']==t],key)
    return {'status':status,'structural':structural,'consistent':consistent,'validity':{'kickoff_in_context_share':share,'required':g.VALID_SHARE},
            'wrong':wrong,'exact':exact,'reader_minus_guard_primary':ci,'lost_exact':{a:len(v) for a,v in lost.items()},
            'by_type':{a:{t:{'on':by(a,'on',t),'reader':by(a,'reader',t)} for t in TYPES} for a in ARMS},
            'both_exact':{a:{k:sum(p[k]==p['oracle'] for p in pairs[a] if p['variant']=='both_exact') for k in ('on','reader')} for a in ARMS},
            'wrong_guard_off':{a:sum(runs[(a,s)]['z2g']['off']['wrong'] for s in SEEDS) for a in ARMS},
            'b2_rule_rate':{a:sum(h.rule_rate(runs[(a,s)],f) for s in SEEDS for f in ids)/(len(SEEDS)*len(ids)) for a in ARMS},
            'read_newest_rows':{a:sum(bool(p['read_newest']) for p in pairs[a]) for a in ARMS},
            'utility':{a:{v:z.z2b.mean_u(runs,a,v) for v in ('b1_only','b2_only','both_exact')} for a in ARMS},'canonical_gate_pass':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home',required=True);p.add_argument('--work',required=True)
    a=p.parse_args()
    from v13.common import atomic_write
    work=Path(a.work);work.mkdir(parents=True,exist_ok=True);runs={}
    for s in SEEDS:
        for arm in ARMS:
            f=work/('summary_'+z.z2b.run_id(arm,s)+'.json')
            if f.exists() and 'z2k' in json.loads(f.read_text()):runs[(arm,s)]=json.loads(f.read_text());continue
            print(json.dumps({'run_start':z.z2b.run_id(arm,s)}),flush=True);runs[(arm,s)]=run(a.installed_home,work,arm,s)
    result={'gate':gate(runs),'runs':{z.z2b.run_id(*k):{'on':v['z2k']['on'],'reader':v['z2k']['reader']} for k,v in sorted(runs.items())}}
    atomic_write(work/'z2k_result.json',json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result['gate'],indent=1)[:4000])
if __name__=='__main__':main()
