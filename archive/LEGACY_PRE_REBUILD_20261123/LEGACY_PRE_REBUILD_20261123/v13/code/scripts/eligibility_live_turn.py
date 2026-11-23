"""Whole live chat turns with the eligibility tool (STEP2 follow-up 2026-10-21).

Per episode one new session with three real runtime turns: the earlier project rule, an unrelated distractor, then the
option A/B question (same templates as tests/integration_step2_utility.py, new seeded numbers). Two arms on the same
installed models, both with the B2 offer switches (b2_offer_body_state=False, offer_quote_min_chars=90,
offer_quote_context_chars=200), observer_sample_rate 1.0, everything else the runtime default:
  c3_alone     eligibility not enabled (ToolStep never reads values, no extra model call)
  tool_active  eligibility enabled by the user AND the SYSTEM-origin Age verdict replaced for this tool only
               (scripts/r4_listarith_live.approve_measurement pattern); schema, enable, guard, C5, TOOL_RESULT unchanged
Score: the decision the answer text commits to (decision_of, fixed rule) against the oracle action.
  capture   eligibility_live_turn.py capture <installed_home> <seed> <n> <out.json>
  evaluate  eligibility_live_turn.py evaluate <prereg.json> <fresh.json> <report.json>
Claim limit: generated English episodes, cloud CPU, Age right replaced for the measurement; not a Redmi number.
"""
import hashlib
import json
import math
import random
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from v13.common import atomic_write

ARMS=('c3_alone','tool_active')
SWITCHES={'b2_offer_body_state':False,'offer_quote_min_chars':90,'offer_quote_context_chars':200,'observer_sample_rate':1.0}
NAMES='Altair Bellatrix Capella Deneb Electra Fomalhaut Gacrux Hadar Izar Jabbah Kochab Lesath Mirach Nashira Okul Phact Rasalas Sabik Tarazed Unuk Vega Wezen Xamidimura Yildun Zaurak Acamar Botein Chara Diphda Errai'.split()
DISTRACTOR='Project Zenith. The unrelated maintenance meeting is scheduled for tomorrow. No budget or decision is requested.'

def episodes(seed,n):
    """Seeded episodes: ~50 % keep the earlier rules, ~40 % override them in the question, ~10 % budget never given."""
    rnd=random.Random(seed);out=[]
    for i in range(n):
        name=NAMES[(seed*7+i)%len(NAMES)]+('' if i<len(NAMES) else str(i));kind=['retain','retain','retain','retain','retain','override','override','override','override','missing'][i%10]
        budget=rnd.randrange(50,130,5);deadline=rnd.randint(3,7);local=rnd.random()<.7
        opts=[(rnd.randrange(max(20,budget-45),budget+20,5),rnd.randint(max(1,deadline-3),deadline+2),rnd.random()<.75) for _ in 'AB']
        prior_budget,prior_deadline,prior_local=(budget+rnd.choice([30,40,50]),deadline+rnd.choice([4,5]),not local) if kind=='override' else (budget,deadline,local)
        prior=f'Project {name}. '+(f'Budget {prior_budget} euros. ' if kind!='missing' else 'Budget has not been provided. ')+f'Deadline {prior_deadline} days. Local-only requirement: {str(prior_local).lower()}.'
        a,b=opts
        current=(f'Project {name}. Decide from the earlier project rules. Option A: cost {a[0]} euros, duration {a[1]} days, local {str(a[2]).lower()}. '
                 f'Option B: cost {b[0]} euros, duration {b[1]} days, local {str(b[2]).lower()}. Compute each remaining budget and eligibility; choose cheapest eligible.')
        if kind=='override':current+=f' Updated rules, overriding the earlier rules: budget {budget} euros, deadline {deadline} days, local-only requirement {str(local).lower()}.'
        if kind=='missing':action='UNKNOWN'
        else:
            ok=[(c,e) for e,(c,d,l) in zip('AB',opts) if c<=budget and d<=deadline and (l or not local)]
            action=min(ok)[1] if ok else 'NONE'
        out.append({'id':name,'kind':kind,'prior':prior,'current':current,'action':action})
    return out

_NEG=re.compile(r"\bnot\b|n't\b|\bexceed|\btoo\b|\bover\b|\bfails?\b|\bineligible\b|\bcannot\b|\bno longer\b",re.I)
_UNK=re.compile(r'\bunknown\b|\bnot (?:stated|provided|given|available)\b|\bmissing\b|\bcannot (?:be )?determine',re.I)
_NONE=re.compile(r'\bno option\b|\bneither\b|\bnone\b',re.I)

def decision_of(text):
    """First sentence that commits: UNKNOWN / NONE wording, else an option letter in a sentence without negation."""
    for s in re.split(r'(?<=[.!?;])\s+|\n+',str(text)):
        if _UNK.search(s):return 'UNKNOWN'
        if _NONE.search(s):return 'NONE'
        m=re.findall(r'\boption\s+([AB])\b',s,re.I)
        if m and not _NEG.search(s) and len({x.upper() for x in m})==1:return m[0].upper()
    return None

def approve_measurement(reg,on):
    if not hasattr(reg,'_policy_orig'):reg._policy_orig=reg._policy
    orig=reg._policy_orig
    def policy(spec,origin,args,confirmed=False):
        status,why,steps=orig(spec,origin,args,confirmed)
        if not (on and spec.name=='eligibility' and origin=='SYSTEM' and spec.name in reg.box.load()[0]['enabled']):return status,why,steps
        if any(not ok for name,ok in steps if name!='c5'):return status,why,steps
        return 'APPROVED','AGE_RIGHT_MEASUREMENT',[s for s in steps if s[0]!='c5']+[['c5',True],['age_right_measurement',True]]
    reg._policy=policy

def wait(r,end):
    while not r.idle():
        if time.monotonic()>end:r.cancel();return False
        time.sleep(.2)
    return True

def episode_turns(r,ep):
    from v13.proofs import audit_event
    r.session=r.store.new_session();rows=[]
    for text in (ep['prior'],DISTRACTOR,ep['current']):
        t0=time.monotonic();eid=r.submit(text);done=wait(r,t0+900);a=audit_event(r.store,eid);meta=a.get('output_metadata') or {}
        rows.append({'eid':eid,'done':done,'status':a.get('status'),'turn_s':round(time.monotonic()-t0,2),'output':(a.get('output') or '')[:600],
                     'tool_call':meta.get('tool_call'),'tool_shadow':meta.get('tool_shadow')})
    last=rows[-1];prop=r.store.one("SELECT payload FROM packets WHERE event_id=? AND kind='ToolProposal' ORDER BY rowid DESC LIMIT 1",(last['eid'],))
    prop=json.loads(prop['payload']) if prop else None
    value=None
    if prop and prop.get('tool')=='eligibility':
        from v13.agi import eligibility
        try:value=eligibility.tool(**prop['args'])['action']
        except Exception:value=None
    return {'turns':rows,'decision':decision_of(last['output']),'proposal':None if prop is None else {'policy':prop.get('policy_status'),'reason':prop.get('policy_reason')},'tool_value':value}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def code_sha():
    return {p:sha(ROOT/'v13'/p) for p in ('toolstep.py','agi/eligibility.py','agi/tools.py','cognition.py','runtime.py','transaction.py')}

def capture(installed,seed,n,path):
    from v13.config import initialize,save_config
    from v13.runtime import Runtime
    from v13.agi import hub
    installed=Path(installed).resolve();rows=[];eps=episodes(seed,n)
    with tempfile.TemporaryDirectory(prefix='v13-elturn-') as tmp:
        home=Path(tmp);cfg=initialize(home)
        for d in ('models','bin'):shutil.rmtree(home/d);(home/d).symlink_to(installed/d,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',home/'config/models.json')
        save_config(home,cfg|{'learning_mode':'RECORD_ONLY','teacher_enabled':False}|SWITCHES)
        r=Runtime(home);reg=hub(r).tools
        try:
            for ep in eps:
                row={'episode':ep}
                for arm in ARMS:
                    on=arm=='tool_active';reg.enable('eligibility',on);approve_measurement(reg,on);row[arm]=episode_turns(r,ep)
                rows.append(row)
                print(json.dumps({'id':ep['id'],'kind':ep['kind'],'oracle':ep['action'],'c3':row['c3_alone']['decision'],'tool':row['tool_active']['decision'],
                                  'value':row['tool_active']['tool_value'],'call':(row['tool_active']['turns'][-1]['tool_call'] or {}).get('status')}),flush=True)
                atomic_write(Path(path),json.dumps({'kind':'V13_ELIGIBILITY_LIVE_TURN','seed':seed,'n':n,'switches':SWITCHES,'script_sha256':sha(__file__),'code_sha256':code_sha(),'rows':rows},indent=1))
        finally:r.close()

def sign_p(w,l):
    n=w+l
    return 1. if n==0 else min(1.,2*sum(math.comb(n,i) for i in range(min(w,l)+1))/2**n)

def summarize(rows):
    ok=lambda r,a:r[a]['decision']==r['episode']['action']
    wrong=lambda r,a:r[a]['decision'] in ('A','B','NONE') and r[a]['decision']!=r['episode']['action']
    w=sum(ok(r,'tool_active') and not ok(r,'c3_alone') for r in rows);l=sum(ok(r,'c3_alone') and not ok(r,'tool_active') for r in rows)
    kinds={}
    for r in rows:
        k=kinds.setdefault(r['episode']['kind'],{'n':0,'c3_alone':0,'tool_active':0});k['n']+=1;k['c3_alone']+=ok(r,'c3_alone');k['tool_active']+=ok(r,'tool_active')
    return {'n':len(rows),'correct':{a:sum(ok(r,a) for r in rows) for a in ARMS},'wrong_committed':{a:sum(wrong(r,a) for r in rows) for a in ARMS},
            'wins':w,'losses':l,'net':w-l,'sign_test_p':round(sign_p(w,l),4),'by_kind':kinds,
            'tool_executed':sum((r['tool_active']['turns'][-1]['tool_call'] or {}).get('status')=='EXECUTED' for r in rows),
            'tool_value_correct':sum(r['tool_active']['tool_value']==r['episode']['action'] for r in rows),
            'errors':{a:sum(t['status']!='FINAL' for r in rows for t in r[a]['turns']) for a in ARMS},
            'turn_s_median':{a:sorted(r[a]['turns'][-1]['turn_s'] for r in rows)[len(rows)//2] for a in ARMS}}

DECISION=('Fresh seed, 24 episodes: TOOL_TURN_SUPPORTED iff net wins (tool_active right, c3_alone wrong) >= +5 AND two-sided sign test p < .05 '
          'AND tool_active wrong_committed <= c3_alone wrong_committed AND no FINAL-status errors beyond c3_alone. Reported, not part of the verdict: by kind, tool value correctness, latency.')

def evaluate(reg_path,fresh,out):
    reg=json.loads(Path(reg_path).read_text());d=json.loads(Path(fresh).read_text())
    if reg['script_sha256']!=sha(__file__) or reg['code_sha256']!=code_sha() or d['script_sha256']!=sha(__file__) or d['code_sha256']!=code_sha():raise SystemExit('script or code changed since preregistration')
    if d['seed']!=reg['fresh_seed'] or d['n']!=reg['fresh_n']:raise SystemExit('not the registered fresh run')
    s=summarize(d['rows'])
    verdict=s['net']>=5 and s['sign_test_p']<.05 and s['wrong_committed']['tool_active']<=s['wrong_committed']['c3_alone'] and s['errors']['tool_active']<=s['errors']['c3_alone']
    rep={'verdict':'TOOL_TURN_SUPPORTED' if verdict else 'NOT_SUPPORTED','summary':s,'decision_rule':reg['decision_rule'],'fresh_sha256':sha(fresh),'prereg_sha256':sha(reg_path)}
    atomic_write(Path(out),json.dumps(rep,indent=1));print(json.dumps(rep,indent=1))

def prereg(dev,out,fresh_seed,fresh_n):
    d=json.loads(Path(dev).read_text())
    if d['seed']==fresh_seed or d['script_sha256']!=sha(__file__) or d['code_sha256']!=code_sha():raise SystemExit('dev run is the fresh seed or from other code')
    body={'schema':'v13-eligibility-live-turn-prereg-v1','created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'dev_seed':d['seed'],'dev_sha256':sha(dev),
          'dev':summarize(d['rows']),'fresh_seed':fresh_seed,'fresh_n':fresh_n,'arms':ARMS,'switches':SWITCHES,'decision_rule':DECISION,'script_sha256':sha(__file__),'code_sha256':code_sha()}
    atomic_write(Path(out),json.dumps(body,indent=1));print(json.dumps(body,indent=1))

if __name__=='__main__':
    c=sys.argv[1]
    if c=='capture':capture(sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),sys.argv[5])
    elif c=='prereg':prereg(sys.argv[2],sys.argv[3],int(sys.argv[4]),int(sys.argv[5]))
    elif c=='evaluate':evaluate(sys.argv[2],sys.argv[3],sys.argv[4])
    else:raise SystemExit(__doc__)
