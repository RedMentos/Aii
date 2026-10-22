#!/usr/bin/env python3
"""WP-AGE0c (prereg docs/proofs/continuation-20261022/age0a-false-alarm/PREREG.md): how often does the late
self-correction detector (selfmodel.SelfSystem.late_offer, WP-AGE0a) fire on answers that are actually right?

  python3 scripts/age0c_false_alarm.py --out <dir>

Replays recorded real body offers (STEP2 runs, offer calibration) against (a) the correct answer and (b) the real C3
answer. The live detector is called through the real code (fresh Runtime, mode shadow); variants V1/V2 exist only here.
No model runs, nothing is switched on.
"""
import argparse,hashlib,json,math,re,sys,tempfile
from pathlib import Path
APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
V13=APP.parent

STEP2=['bench-results/step2-two-body-20261009/step2_utility.json','bench-results/kalibrierung2-20261009/step2-c3-350m.json',
       'bench-results/kalibrierung2-20261009/step2-c3-230m.json','code/docs/proofs/continuation-20261011/step2-webchat-70/report.json']
CALIB=['bench-results/kalibrierung-20261009/offers.json','bench-results/kalibrierung-20261009/offers_solve.json',
       'bench-results/kalibrierung2-20261009/offers.json','bench-results/kalibrierung2-20261009/offers_hypothesis.json']
VARIANTS=('V0','V1','V2')
K1_RATE,K1_UPPER,K2_MIN,K3_MIN=.10,.15,.50,.20  # fixed in PREREG.md


def nums(t):return {x.replace(',','.') for x in re.findall(r'\d+(?:[.,]\d+)?',t or '')}  # same rule as late_offer


def detect(variant,offer,output,source):
    """-> (alarm, cited missing numbers). V0 mirrors late_offer; V1 drops the needs_reentry trigger; V2 also drops echoes."""
    o=offer.get('offer',{});missing=nums(o.get('summary',''))-nums(output)
    if variant=='V2':missing-=nums(source)
    if variant=='V0':return bool(o.get('needs_reentry') or missing),missing
    return bool(missing),missing


def wilson(k,n,z=1.96):
    if not n:return [None,None]
    p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [round(max(0.,c-h),4),round(min(1.,c+h),4)]


def key(*parts):return hashlib.sha256(json.dumps(parts,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def load_pairs():
    """Unique pairs per arm: {'role','offer','output','source','gold','file'}."""
    arms={'A_right':{},'A_real':{},'B_terse':{},'B_echo':{}}
    for f in STEP2:
        d=json.loads((V13/f).read_text());fx={x['id']:x for x in d['fixtures']}
        for r in d['rows']:
            x=fx.get(r.get('fixture'))
            if not x or 'oracle' not in x:continue
            src=' '.join(x.get(k,'') for k in ('prior','distractor','current'));gold=json.dumps(x['oracle'],sort_keys=True)
            for p in r.get('offers') or []:
                base={'role':p.get('role'),'offer':{'offer':p.get('offer',{})},'source':src,'gold':gold,'file':f,'fixture':x['id']}
                arms['A_right'].setdefault(key(p.get('offer'),gold),dict(base,output=gold))
                arms['A_real'].setdefault(key(p.get('offer'),gold,r.get('raw_answer')),dict(base,output=r.get('raw_answer') or ''))
    for f in CALIB:
        d=json.loads((V13/f).read_text())
        for r in d['rows']:
            for role in ('B1','B2'):
                p=r.get(role) or {}
                if 'offer' not in p:continue
                base={'role':role,'offer':{'offer':p['offer']},'source':r['text'],'gold':str(r['gold']),'file':f,'kind':r['kind']}
                arms['B_terse'].setdefault(key(p['offer'],r['gold']),dict(base,output=str(r['gold'])))
                arms['B_echo'].setdefault(key(p['offer'],r['text'],r['gold']),dict(base,output=r['text']+' Answer: '+str(r['gold'])))
    return {a:list(v.values()) for a,v in arms.items()}


def live_alarms(pairs):
    """Real code path: SelfSystem.late_offer in mode shadow on a fresh Runtime; returned row != None is an alarm."""
    from v13.runtime import Runtime
    from v13 import selfmodel as S,neuromod as N,age as agectl
    out=[]
    with tempfile.TemporaryDirectory() as tmp:
        r=Runtime(Path(tmp))
        try:
            t=[1000.];s=S.SelfSystem(r,agectl.controller(r),N.Neuromod(r.store),clock=lambda:t[0])
            assert s.correction_mode()=='shadow'
            for i,p in enumerate(pairs):
                t[0]+=1.;out.append(s.late_offer('age0c_%d'%i,dict(p['offer'],role=p['role']),p['output']) is not None)
        finally:r.close()
    return out


def rate(rows):
    k=sum(rows);n=len(rows);return {'alarms':k,'n':n,'rate':round(k/n,4) if n else None,'wilson95':wilson(k,n)}


def evaluate(arms,live):
    rep={'arms':{},'by_role':{},'by_trigger':{},'live_matches_V0':{}}
    for a,pairs in arms.items():
        v0=[detect('V0',p['offer'],p['output'],p['source'])[0] for p in pairs]
        rep['live_matches_V0'][a]=live[a]==v0
        rep['arms'][a]={v:rate([detect(v,p['offer'],p['output'],p['source'])[0] for p in pairs]) for v in VARIANTS}
        rep['by_role'][a]={role:{v:rate([detect(v,p['offer'],p['output'],p['source'])[0] for p in pairs if p['role'].startswith(role)]) for v in VARIANTS}
                           for role in ('B1','B2')}
        trig={'reentry_only':0,'numbers_only':0,'both':0,'none':0}
        for p in pairs:
            ne=bool(p['offer']['offer'].get('needs_reentry'));mi=bool(detect('V0',p['offer'],p['output'],p['source'])[1])
            trig['both' if ne and mi else 'reentry_only' if ne else 'numbers_only' if mi else 'none']+=1
        rep['by_trigger'][a]=trig
    # K2: reason hits on real (wrong) C3 answers
    k2={}
    for v in VARIANTS:
        fired=hit=0
        for p in arms['A_real']:
            alarm,cited=detect(v,p['offer'],p['output'],p['source'])
            if not alarm:continue
            fired+=1;hit+=bool(cited&(nums(p['gold'])-nums(p['output'])))
        k2[v]={'alarms':fired,'justified':hit,'share':round(hit/fired,4) if fired else None}
    rep['reason_hits_A_real']=k2
    # K3: paired, same offer + fixture, right vs real answer
    k3={}
    right={key(p['offer'],p['gold']):p for p in arms['A_right']}
    for v in VARIANTS:
        w=[];c=[]
        for p in arms['A_real']:
            q=right[key(p['offer'],p['gold'])]
            w.append(detect(v,p['offer'],p['output'],p['source'])[0]);c.append(detect(v,q['offer'],q['output'],q['source'])[0])
        k3[v]={'n_pairs':len(w),'alarm_wrong':round(sum(w)/len(w),4),'alarm_right':round(sum(c)/len(c),4),
               'difference_pp':round(100*(sum(w)-sum(c))/len(w),2),
               'fires_only_on_wrong':sum(a and not b for a,b in zip(w,c)),'fires_only_on_right':sum(b and not a for a,b in zip(w,c))}
    rep['discrimination_A']=k3
    verdict={}
    for v in VARIANTS:
        k1=all(rep['arms'][a][v]['rate']<=K1_RATE and rep['arms'][a][v]['wilson95'][1]<=K1_UPPER for a in ('A_right','B_terse','B_echo'))
        k2ok=k2[v]['share'] is not None and k2[v]['share']>=K2_MIN
        k3ok=k3[v]['difference_pp']>=100*K3_MIN
        verdict[v]={'K1':k1,'K2':k2ok,'K3':k3ok,'deliverable':k1 and k2ok and k3ok}
    rep['criteria']=verdict
    v0=verdict['V0']
    if not all(rep['live_matches_V0'].values()):rep['verdict']='AGE0C_INVALID_V0_MISMATCH'
    elif v0['deliverable']:rep['verdict']='AGE0C_DELIVER_OK'
    else:
        cand=[v for v in ('V1','V2') if verdict[v]['deliverable']]
        rep['verdict']='AGE0C_STAY_SHADOW'+('' if not cand else '+AGE0C_VARIANT_'+cand[0]+'_CANDIDATE')
        rep['missing_criteria_V0']=[k for k in ('K1','K2','K3') if not v0[k]]
    return rep


def examples(arms,n=4):
    """A few false alarms per arm (V0), only recorded synthetic task text, for the finding note."""
    ex={}
    for a in ('A_right','B_terse','B_echo'):
        rows=[]
        for p in arms[a]:
            alarm,cited=detect('V0',p['offer'],p['output'],p['source'])
            if alarm and len(rows)<n:
                rows.append({'role':p['role'],'summary':p['offer']['offer'].get('summary','')[:160],'needs_reentry':bool(p['offer']['offer'].get('needs_reentry')),
                             'output':p['output'][:120],'cited_missing':sorted(cited)})
        ex[a]=rows
    return ex


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    arms=load_pairs();live={k:live_alarms(v) for k,v in arms.items()}
    rep=evaluate(arms,live)
    from v13.common import file_hash
    rep.update(schema='age0c-false-alarm-v1',prereg='docs/proofs/continuation-20261022/age0a-false-alarm/PREREG.md',
               prereg_sha256=file_hash(APP/'docs/proofs/continuation-20261022/age0a-false-alarm/PREREG.md'),
               detector_sha256=file_hash(APP/'v13/selfmodel.py'),
               inputs={f:file_hash(V13/f) for f in STEP2+CALIB},pairs={k:len(v) for k,v in arms.items()},
               examples_V0=examples(arms),activated=False,phone_measured=False)
    (out/'report.json').write_text(json.dumps(rep,indent=1,ensure_ascii=False,sort_keys=True)+'\n')
    print(json.dumps({k:rep[k] for k in ('verdict','pairs','arms','reason_hits_A_real','discrimination_A','criteria','live_matches_V0')},indent=1))


if __name__=='__main__':main()
