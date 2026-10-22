"""WP-HX2: same-task probe without gold answers on the STEP2 B2 rule quote (Harness² Propose-Probe-Compose).

Question: can an allow-listed harness edit (text around frozen weights, here the B2 earlier-context instruction,
target prompt.b2_earlier_context) found by a gold-free probe raise STEP2 utility on held-out episodes and fresh seeds,
better than an unguided edit of similar size? Path: the pre-2026-10-21 quote path (b2_quote_select off, config
LEGACY_QUOTE_PATH, Z2c arm CQ settings: two bodies, Z2b targeted question). There B2 quoted the full rule in only
~17 % of rows (Z2c). Live now uses the pointer switch (.97); this probe checks the method where there is room to gain,
and the result is reported against that, never as a live improvement.

Stages (all fixed in docs/proofs/continuation-20261022/hx2-same-task-probe/PREREG.md before any run):
  probe    seed 20, arms REF V1 V2 V3; selection only on probe episodes P, gold-free score = share of B2 emitted quotes
           that pass the exact source check (agi/harness_probe.compose, gain >= .05 over REF, else NO_CANDIDATE)
  holdout  seeds 21 22 23, arms REF, chosen, U (unguided); gate on held-out episodes H (agi/harness_probe.holdout_gate)
Everything else is the Z2b runner (step2_z2b_seeds.run_one, private module copy). Diagnosis only (Linux cloud, no Redmi).
"""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
import importlib.util
import step2_z2_timescale as z2

def _private(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
z2b=_private('step2_z2b_for_hx2','scripts/step2_z2b_seeds.py')
z2c=_private('step2_z2c_for_hx2','scripts/step2_z2c_b2_rule.py')  # b2_rows (gold-scored rule rate, gate only)

from v13.config import LEGACY_QUOTE_PATH
from v13.agi.harness import B2_CONTEXT_NOTE
from v13.agi import harness_probe as HP

TARGET='prompt.b2_earlier_context'
GENERAL=(' Copy every quote character for character from one source sentence: same words, capitals and punctuation;'
         ' never shorten, join or reword it.')
DOMAIN=(' When the current text does not restate a project rule such as budget, deadline or a local-only requirement,'
        ' quote the whole earlier source sentence that states it, word for word.')
UNGUIDED=(' Keep the summary in plain, friendly English, in complete sentences, and avoid repeating the same word'
          ' twice in a row.')
VARIANTS={'REF':None,'V1':{TARGET:B2_CONTEXT_NOTE+GENERAL},'V2':{TARGET:B2_CONTEXT_NOTE+DOMAIN},
          'V3':{TARGET:B2_CONTEXT_NOTE+GENERAL+DOMAIN},'U':{TARGET:B2_CONTEXT_NOTE+UNGUIDED}}
CLASS={'V1':'general','V2':'domain','V3':'general+domain','U':'unguided_control'}
PROBE_SEED=20;PROBE_ARMS=('REF','V1','V2','V3')
HOLDOUT_SEEDS=(21,22,23)
PROBE_EPISODES=('Kestrel','Lumen','Meridian','Quasar','Sirius')
HOLDOUT_EPISODES=('Nimbus','Orion','Perseus','Rigel','Tycho')
B2_VARIANTS=z2c.B2_VARIANTS
AXES=('both_exact','b2_only','b1_only','b2_rule_rate')

for _arm in VARIANTS:z2b.ARMS[_arm]={'base':'C','query':True}
def settings(arm,seed):return LEGACY_QUOTE_PATH|z2.ARMS['C']|{'seed':seed,'b2_quote_select':'off'}
z2b.settings=settings  # every arm: identical settings; arms differ only in the harness overlay

def b2_offers(report,episodes):
    """Gold-free per B2 current-turn offer: emitted quotes (<=3, as checked), rejected, verified."""
    rows=[]
    for row in report['rows']:
        if row['fixture'] not in episodes or row['variant'] not in B2_VARIANTS:continue
        for o in row['offers']:
            if o['role']!='B2_GIST':continue
            emitted=min(3,len(o['offer']['quotes']));rej=o.get('rejected_quotes',0)
            rows.append({'task':row['fixture']+':'+row['variant'],'emitted':emitted,'rejected':rej,'verified':max(0,emitted-rej),
                         'quotes':o['offer']['quotes'][:3],'summary':o['offer']['summary'],'prompt_tokens':(o.get('native_metrics') or {}).get('prompt_tokens')})
    return rows

def probe_score(offers):
    """Mean over B2 offers of verified/emitted (0 for an offer without quotes). Reads no oracle."""
    return sum((x['verified']/x['emitted']) if x['emitted'] else 0. for x in offers)/max(1,len(offers))

def behaviour(report,episodes):
    out={}
    for row in report['rows']:
        if row['fixture'] not in episodes:continue
        b2=[o for o in row['offers'] if o['role']=='B2_GIST']
        out[row['fixture']+':'+row['variant']]={'b2_quotes':[q for o in b2 for q in o['offer']['quotes'][:3]],'b2_rejected':sum(o.get('rejected_quotes',0) for o in b2),
                                               'b2_summary':[o['offer']['summary'] for o in b2],'raw_answer':row.get('raw_answer'),
                                               'b2_prompt_tokens':[(o.get('native_metrics') or {}).get('prompt_tokens') for o in b2]}
    return out

def run(installed,work,arm,seed):
    from v13.common import atomic_write,file_hash
    work=Path(work)
    with HP.overlay(VARIANTS[arm]) as applied:
        summary=z2b.run_one(installed,work,arm,seed)
        b2=applied['b2_note'];rewrite={'calls':b2.calls,'rewritten':b2.rewritten} if b2 else None
    report=json.loads((work/('step2_'+z2b.run_id(arm,seed)+'.json')).read_text())
    allep=tuple(f['id'] for f in z2.FIXTURES)
    rr=z2c.b2_rows(report)
    summary['hx2']={'arm':arm,'class':CLASS.get(arm,'reference'),'diff':applied['diff'],'b2_note_rewrite':rewrite,
                    'probe_offers':b2_offers(report,PROBE_EPISODES),'all_offers':b2_offers(report,allep),'behaviour':behaviour(report,allep),
                    'b2_rule_rows':{f'{k[0]}:{k[1]}':v for k,v in sorted(rr.items())},
                    'wrong_committed_tool':sum(s['wrong_committed'] for s in summary['tool_summary'].values()),
                    'source_sha256':{str(x.relative_to(ROOT)):file_hash(x) for x in (Path(__file__).resolve(),ROOT/'scripts/step2_z2b_seeds.py',ROOT/'scripts/step2_z2c_b2_rule.py',
                                                                                     ROOT/'v13/cognition.py',ROOT/'v13/config.py',ROOT/'v13/agi/harness.py',ROOT/'v13/agi/harness_probe.py')}}
    summary['hx2']['probe_score']=probe_score(summary['hx2']['probe_offers'])
    atomic_write(work/('summary_'+z2b.run_id(arm,seed)+'.json'),json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

def compose(runs):
    ref=runs[('REF',PROBE_SEED)]['hx2']
    bad=[a for a in PROBE_ARMS if a!='REF' and not (runs[(a,PROBE_SEED)]['hx2']['b2_note_rewrite'] or {}).get('rewritten')]
    if bad or ref['b2_note_rewrite'] is not None:return {'status':'INVALID','choice':None,'reason':'Overlay hat B2 nicht erreicht: '+','.join(bad)}
    scores={a:runs[(a,PROBE_SEED)]['hx2']['probe_score'] for a in PROBE_ARMS if a!='REF'}
    fields=('b2_quotes','b2_rejected','b2_summary','raw_answer','b2_prompt_tokens')
    pe=lambda b:{k:v for k,v in b.items() if k.split(':')[0] in PROBE_EPISODES}
    diffs={a:HP.behaviour_diff(pe(ref['behaviour']),pe(runs[(a,PROBE_SEED)]['hx2']['behaviour']),fields) for a in scores}
    return HP.compose(scores,ref['probe_score'])|{'scores':scores,'reference_score':ref['probe_score'],'class':{a:CLASS[a] for a in scores},'behaviour_diff':diffs}

def axis_values(runs,arm,episodes):
    """{axis: {episode: [value per holdout seed]}}"""
    out={ax:{} for ax in AXES}
    for fid in episodes:
        for s in HOLDOUT_SEEDS:
            r=runs[(arm,s)]
            for v in ('both_exact','b2_only','b1_only'):out[v].setdefault(fid,[]).append(r['episode_utility_tool'][fid+':'+v])
            if z2c.FIX[fid]['type'] in z2c.RULE_TYPES:
                rr=r['hx2']['b2_rule_rows'];out['b2_rule_rate'].setdefault(fid,[]).append(sum(rr[f'{fid}:{v}']['rules'] for v in B2_VARIANTS)/len(B2_VARIANTS))
    return out

def gate(runs,choice):
    need=[(a,s) for s in HOLDOUT_SEEDS for a in ('REF',choice,'U')]
    if any(k not in runs for k in need):return {'status':'INCOMPLETE','missing':[z2b.run_id(*k) for k in need if k not in runs]}
    structural=all(runs[k]['tool_status']!='STRUCTURAL_FAIL' and runs[k]['step2_status']!='DIAGNOSTIC_INCOMPLETE' for k in need) and \
               all(runs[k]['queried_offers']['with_question']==runs[k]['queried_offers']['offers']>0 for k in need) and \
               all((runs[k]['hx2']['b2_note_rewrite'] is None)==(k[0]=='REF') and (k[0]=='REF' or runs[k]['hx2']['b2_note_rewrite']['rewritten']>0) for k in need)
    wrong={n:sum(runs[(a,s)]['hx2']['wrong_committed_tool'] for s in HOLDOUT_SEEDS) for n,a in (('ref','REF'),('chosen',choice),('unguided','U'))}
    def axes(eps):
        v={n:axis_values(runs,a,eps) for n,a in (('ref','REF'),('chosen',choice),('unguided','U'))}
        return {ax:{n:v[n][ax] for n in v} for ax in AXES}
    out=HP.holdout_gate(axes(HOLDOUT_EPISODES),'both_exact',wrong,structural)
    allep=[f['id'] for f in z2.FIXTURES]
    out['secondary_all_episodes_fresh_seeds']=HP.holdout_gate(axes(allep),'both_exact',wrong,structural)
    tok=lambda a:[t for s in HOLDOUT_SEEDS for o in runs[(a,s)]['hx2']['all_offers'] if (t:=o['prompt_tokens'])]
    out['b2_prompt_tokens_mean']={n:sum(tok(a))/max(1,len(tok(a))) for n,a in (('ref','REF'),('chosen',choice),('unguided','U'))}
    out['choice']=choice;out['canonical_gate_pass']=False
    return out

def order(stage,choice=None):
    if stage=='probe':return [(a,PROBE_SEED) for a in PROBE_ARMS]
    return [(a,s) for s in HOLDOUT_SEEDS for a in ('REF',choice,'U')]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home',required=True);p.add_argument('--work',required=True)
    p.add_argument('--stage',choices=('probe','holdout','all'),default='all')
    a=p.parse_args()
    from v13.common import atomic_write
    work=Path(a.work);work.mkdir(parents=True,exist_ok=True);runs={}
    def load_or_run(arm,s):
        f=work/('summary_'+z2b.run_id(arm,s)+'.json')
        if f.exists() and 'hx2' in json.loads(f.read_text()):runs[(arm,s)]=json.loads(f.read_text());return
        print(json.dumps({'run_start':z2b.run_id(arm,s)}),flush=True);runs[(arm,s)]=run(a.installed_home,work,arm,s)
    for k in order('probe'):load_or_run(*k)
    comp=compose(runs);atomic_write(work/'hx2_compose.json',json.dumps(comp,ensure_ascii=False,indent=2))
    print(json.dumps({k:comp[k] for k in ('status','choice','scores','reference_score')}),flush=True)
    result={'compose':{k:v for k,v in comp.items() if k!='behaviour_diff'}}
    if comp['status']!='CHOSEN':result['gate']={'status':'HX2_NO_CANDIDATE','canonical_gate_pass':False}
    elif a.stage in ('holdout','all'):
        for k in order('holdout',comp['choice']):load_or_run(*k)
        result['gate']=gate(runs,comp['choice'])
    result['runs']={z2b.run_id(*k):{'tool':v['paired_tool']['mean_utility'],'probe_score':v['hx2']['probe_score'],'wrong':v['hx2']['wrong_committed_tool']} for k,v in sorted(runs.items())}
    atomic_write(work/'hx2_result.json',json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result.get('gate'),indent=1)[:4000])
if __name__=='__main__':main()
