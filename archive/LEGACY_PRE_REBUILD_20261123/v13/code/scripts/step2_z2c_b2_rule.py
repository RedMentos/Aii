"""WP-Z2c: make B2 deliver the earlier rule as a verified quote (STEP2 bottleneck after WP-Z2b).

Diagnosis on the recorded Z2b offers (scripts/step2_z2c_b2_rule.py --diagnose, 12 runs, seeds 14-16): of 384 current-turn
B2 offers on RULE/SPLIT episodes (the old rule lives only in B2's earlier context) 115 carried all three rules. B2 mostly
*knew* the rule but did not quote it: the commonest miss is a paraphrase or broken copy of the right sentence
('Project Kestrel has a budget of 100 euros', '... Local-only requirement:.') that the exact check drops, next a
quote of the current task text. The targeted question of Z2b did not change this (Qwen B2: 22/96 with and without).

Two fixable variants, both a live switch cfg b2_quote_select (off = previous behaviour, byte-identical path):
  anchor   a B2 quote that matches no source points at the 1-3 consecutive source sentences holding every number of the
           quote and >= 60 % of its content words (cognition.anchor_span); tie across sources -> dropped
  pointer  B2 gets its sources as numbered exact sentences (quote_choices) and answers with ids (schema enum); the ids
           are mapped back to exact sentence text
Both then run through the unchanged quote verification (offer_quote_context_chars widening), so only exact source
text ever reaches C3. The anchor rule was designed after looking at the Z2b offers; therefore every arm runs on new
seeds 17-19 and the primary arm comparison is against a fresh CQ control on the same seeds.

Arms (all two_body Qwen B2 + Z2b targeted question, Z2 arm C settings): CQ (control), CQA (anchor), CQP (pointer).
Everything else is the Z2b runner (step2_z2b_seeds.run_one): same harness copy, fixtures, seed patch, tool replay.
Preregistration: docs/proofs/continuation-20261021/step2-z2c-b2-rule/PREREG.md. Diagnosis only (Linux cloud, no Redmi);
the canonical gate is never promoted by this script.
"""
import argparse
import json
import re
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
import importlib.util
import step2_z2_timescale as z2

def _private_z2b():
    """Own module copy of the Z2b runner, so its seeds/arms/settings can be set here without touching the shared module."""
    spec=importlib.util.spec_from_file_location('step2_z2b_for_z2c',ROOT/'scripts/step2_z2b_seeds.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
z2b=_private_z2b()

SEEDS=(17,18,19)
ARMS={'CQ':'off','CQA':'anchor','CQP':'pointer'}
CONTROL='CQ'
B2_VARIANTS=('b2_only','both_none','both_exact','both_control')  # B2 runs with its own context and its own policy
RULE_TYPES=('RULE','SPLIT')
TARGET_RATE=.60
BOOT=10000;BOOT_SEED=20261021

for _arm in ARMS:z2b.ARMS[_arm]={'base':'C','query':True}
z2b.SEEDS=SEEDS  # episode_diff/mean_u of the Z2b runner copy read its module seeds
_z2b_settings=z2b.settings
def settings(arm,seed):return _z2b_settings(arm,seed)|({'b2_quote_select':ARMS[arm]} if arm in ARMS and ARMS[arm]!='off' else {})
z2b.settings=settings  # run_one resolves settings through its module copy; CQ stays byte-identical to Z2b CQ

FIX={f['id']:f for f in z2.FIXTURES}
RULE_EPISODES=[f['id'] for f in z2.FIXTURES if f['type'] in RULE_TYPES]

def rule_values(text):
    """Rule values stated in an exact quote (budget, deadline, local-only), as found."""
    out=[]
    for k,pat,cast in (('budget',r'[Bb]udget (\d+) euros',int),('deadline',r'[Dd]eadline (\d+) days',int),('local_only',r'[Ll]ocal-only requirement: (true|false)',lambda s:s=='true')):
        out+=[(k,cast(m)) for m in re.findall(pat,text)]
    return out

def b2_rows(report):
    """Per (fixture, variant): did B2's verified quotes (as handed to C3) state all rules, and did they state a wrong one."""
    from v13.agi import eligibility as E
    out={}
    for row in report['rows']:
        f=FIX[row['fixture']]
        if f['type'] not in RULE_TYPES or row['variant'] not in B2_VARIANTS or not row.get('consumer_messages'):continue
        user=json.loads(next(x['content'] for x in row['consumer_messages'] if x['role']=='user'))
        quotes=[q for a in user.get('analysts',[]) if a['role']=='B2_GIST' for q in a['verified_quotes']]
        text=' '.join(quotes)
        out[(row['fixture'],row['variant'])]={'rules':all(E.stated(k,v,text) for k,v in f['rules'].items()),
                                               'wrong_rule':any(f['rules'][k]!=v for k,v in rule_values(text))}
    return out

def b2_offers(report):
    """Raw B2 offer bookkeeping of the current turn (selection mode, anchored/picked counts, rejected quotes)."""
    n=rej=anch=picked=0
    for row in report['rows']:
        if FIX[row['fixture']]['type'] not in RULE_TYPES or row['variant'] not in B2_VARIANTS:continue
        for o in row['offers']:
            if o['role']!='B2_GIST':continue
            n+=1;rej+=o.get('rejected_quotes',0);s=o.get('b2_quote_select') or {}
            anch+=s.get('anchored',0);picked+=len(s.get('picked') or [])
    return {'offers':n,'rejected_quotes':rej,'anchored_quotes':anch,'picked_ids':picked}

def run(installed,work,arm,seed):
    from v13.common import atomic_write,file_hash
    summary=z2b.run_one(installed,work,arm,seed)
    report=json.loads((Path(work)/('step2_'+z2b.run_id(arm,seed)+'.json')).read_text())
    rows=b2_rows(report)
    summary['z2c']={'b2_quote_select':ARMS[arm],'b2_rule_rows':{f'{k[0]}:{k[1]}':v for k,v in sorted(rows.items())},
                    'b2_rule_rate':sum(v['rules'] for v in rows.values())/len(rows),'b2_wrong_rule_rows':sum(v['wrong_rule'] for v in rows.values()),
                    'b2_offers':b2_offers(report),
                    'b2_prompt_tokens':[o['native_metrics'].get('prompt_tokens') for r in report['rows'] for o in r['offers'] if o['role']=='B2_GIST'],
                    'wrong_committed_tool':sum(s['wrong_committed'] for s in summary['tool_summary'].values()),
                    'source_sha256':{str(x.relative_to(ROOT)):file_hash(x) for x in (Path(__file__).resolve(),ROOT/'scripts/step2_z2b_seeds.py',ROOT/'v13/cognition.py',ROOT/'v13/config.py')}}
    atomic_write(Path(work)/('summary_'+z2b.run_id(arm,seed)+'.json'),json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

def episode_rate(runs,arm,fid):
    """Mean over seeds of the fraction of B2 variants of this episode whose quotes carried all rules."""
    vals=[]
    for s in SEEDS:
        rr=runs[(arm,s)]['z2c']['b2_rule_rows'];vals.append(sum(rr[f'{fid}:{v}']['rules'] for v in B2_VARIANTS)/len(B2_VARIANTS))
    return sum(vals)/len(vals)

def gate(runs):
    """Preregistered decision (PREREG.md)."""
    need=[(a,s) for a in ARMS for s in SEEDS]
    if any(k not in runs for k in need):return {'status':'INCOMPLETE','missing':[z2b.run_id(*k) for k in need if k not in runs]}
    rate={a:sum(runs[(a,s)]['z2c']['b2_rule_rate'] for s in SEEDS)/len(SEEDS) for a in ARMS}
    wrong_rule={a:sum(runs[(a,s)]['z2c']['b2_wrong_rule_rows'] for s in SEEDS) for a in ARMS}
    wrong_tool={a:sum(runs[(a,s)]['z2c']['wrong_committed_tool'] for s in SEEDS) for a in ARMS}
    structural=all(r['tool_status']!='STRUCTURAL_FAIL' and r['step2_status']!='DIAGNOSTIC_INCOMPLETE' for r in runs.values())
    queried=all(runs[k]['queried_offers']['with_question']==runs[k]['queried_offers']['offers']>0 for k in need)
    out={'rates':rate,'wrong_rule_rows':wrong_rule,'wrong_committed_tool':wrong_tool,'structural':structural,'arms_did_what_they_say':queried,'variants':{}}
    for arm in ARMS:
        if arm==CONTROL:continue
        diffs=[[episode_rate(runs,arm,fid)-episode_rate(runs,CONTROL,fid)] for fid in RULE_EPISODES]
        ci=z2b.cluster_ci(diffs)
        util=z2b.cluster_ci(z2b.episode_diff(runs,(arm,'both_exact'),(CONTROL,'both_exact')))
        single=max(z2b.SINGLE,key=lambda v:z2b.mean_u(runs,arm,v))
        vs_single=z2b.cluster_ci(z2b.episode_diff(runs,(arm,'both_exact'),(arm,single)))
        per_seed=all(runs[(arm,s)]['paired_tool']['mean_utility'].get('both_exact',0.)>max(runs[(arm,s)]['paired_tool']['mean_utility'].get(v,0.) for v in z2b.SINGLE) for s in SEEDS)
        mode_used=all((runs[(arm,s)]['z2c']['b2_offers']['anchored_quotes' if ARMS[arm]=='anchor' else 'picked_ids'])>0 for s in SEEDS)
        safe=wrong_rule[arm]==0 and wrong_tool[arm]==0 and structural and queried and mode_used
        if ci['ci95'][0]>0 and rate[arm]>=TARGET_RATE and safe:status='B2_RULE_QUOTE_FIXED'
        elif ci['ci95'][0]>0 and safe:status='B2_RULE_QUOTE_IMPROVED_PARTIAL'
        elif not safe:status='B2_RULE_QUOTE_UNSAFE_OR_INVALID'
        else:status='B2_RULE_QUOTE_NOT_FIXED'
        out['variants'][arm]={'status':status,'mode':ARMS[arm],'rate':rate[arm],'rate_minus_control':ci,'safe':safe,'mode_used_every_seed':mode_used,
                              'secondary':{'both_exact_minus_control':util,'both_exact_mean':z2b.mean_u(runs,arm,'both_exact'),
                                           'best_single':single,'best_single_mean':z2b.mean_u(runs,arm,single),'both_exact_minus_best_single':vs_single,
                                           'z2b_criterion1_two_bodies_beat_best_single':z2b.mean_u(runs,arm,'both_exact')>z2b.mean_u(runs,arm,single) and vs_single['ci95'][0]>0 and per_seed,
                                           'split_exact_both_exact':sum(len(runs[(arm,s)]['split_exact_tool'].get('both_exact',[])) for s in SEEDS),
                                           'b2_prompt_tokens_mean':sum(t for s in SEEDS for t in runs[(arm,s)]['z2c']['b2_prompt_tokens'] if t)/max(1,sum(1 for s in SEEDS for t in runs[(arm,s)]['z2c']['b2_prompt_tokens'] if t))}}
    best=[a for a,v in out['variants'].items() if v['status']=='B2_RULE_QUOTE_FIXED']
    out['status']='Z2C_B2_RULE_QUOTE_FIXED' if best else ('Z2C_B2_RULE_QUOTE_IMPROVED_PARTIAL' if any(v['status']=='B2_RULE_QUOTE_IMPROVED_PARTIAL' for v in out['variants'].values()) else 'Z2C_B2_RULE_QUOTE_NOT_FIXED')
    out['canonical_gate_pass']=False
    return out

def diagnose(folder):
    """Classify recorded Z2b B2 offers (current turn, RULE/SPLIT, B2 variants): why the rule was not quoted."""
    import collections,glob
    from v13.cognition import quote_span
    from v13.agi import eligibility as E
    tot=collections.Counter();per=collections.defaultdict(collections.Counter)
    for fn in sorted(glob.glob(str(Path(folder)/'step2_*_s1[456].json'))):
        arm=Path(fn).name.split('step2_')[1].split('_s')[0];r=json.loads(Path(fn).read_text())
        for row in r['rows']:
            f=FIX[row['fixture']]
            if f['type'] not in RULE_TYPES or row['variant'] not in B2_VARIANTS:continue
            rule_src=f['history'][0][:z2.B2_EXCERPT_CHARS];others=[h[:z2.B2_EXCERPT_CHARS] for h in f['history'][1:]]
            for o in row['offers']:
                if o['role']!='B2_GIST':continue
                cats=set();ok=False
                for q in o['offer']['quotes']:
                    if (sp:=quote_span(q,rule_src,200)):
                        full=all(E.stated(k,v,rule_src[sp[0]:sp[1]]) for k,v in f['rules'].items());ok|=full;cats.add('RULE_SENTENCE_PART' if not full else 'RULE')
                    elif quote_span(q,f['current'],200):cats.add('QUOTED_CURRENT_TASK')
                    elif any(quote_span(q,s,200) for s in others):cats.add('QUOTED_OTHER_EARLIER')
                    elif any(w in q.lower() for w in ('budget','deadline','local')) or str(f['rules']['budget']) in q:cats.add('REJECTED_RULE_PARAPHRASE_OR_BROKEN_COPY')
                    else:cats.add('REJECTED_OTHER')
                key='OK_RULE_QUOTED' if ok else ('NO_QUOTE' if not o['offer']['quotes'] else '+'.join(sorted(cats)))
                tot[key]+=1;per[arm][key]+=1;tot['_offers']+=1;tot['_summary_names_budget']+=str(f['rules']['budget']) in o['offer']['summary']
    return {'total':dict(tot.most_common()),'per_arm':{a:dict(c.most_common()) for a,c in per.items()}}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home');p.add_argument('--work')
    p.add_argument('--runs',nargs='*');p.add_argument('--diagnose',help='folder with the Z2b step2_*.json reports')
    a=p.parse_args()
    if a.diagnose:print(json.dumps(diagnose(a.diagnose),indent=1));return
    from v13.common import atomic_write
    work=Path(a.work);work.mkdir(parents=True,exist_ok=True);runs={}
    order=[(arm,s) for s in SEEDS for arm in ARMS]
    if a.runs:order=[(r.split('_s')[0],int(r.split('_s')[1])) for r in a.runs]
    for arm,s in order:
        f=work/('summary_'+z2b.run_id(arm,s)+'.json')
        if f.exists() and 'z2c' in json.loads(f.read_text()):runs[(arm,s)]=json.loads(f.read_text());continue
        print(json.dumps({'run_start':z2b.run_id(arm,s)}),flush=True);runs[(arm,s)]=run(a.installed_home,work,arm,s)
    for f in work.glob('summary_*_s*.json'):
        x=json.loads(f.read_text())
        if 'z2c' in x:runs.setdefault((x['arm'],x['seed']),x)
    result={'gate':gate(runs),'runs':{z2b.run_id(*k):{'tool':v['paired_tool']['mean_utility'],'b2_rule_rate':v['z2c']['b2_rule_rate'],'b2_offers':v['z2c']['b2_offers']} for k,v in sorted(runs.items())}}
    atomic_write(work/'z2c_result.json',json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result['gate'],indent=1)[:4000])
if __name__=='__main__':main()
