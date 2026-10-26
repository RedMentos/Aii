#!/usr/bin/env python3
"""Run487 independent stdlib audit of original Run479 no-model ZIP.

Recomputes 378 row utilities directly from nine original tool files; does not
import Run468/469/470, run inference, or promote any V13 acceptance gate.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile

EXPECTED_SAFE = 'a87acfa38688e66e603fe9c07cbc0762b231a6eb74527a8010c595e487e46afe'
ARMS = ('O','P','S')
SEEDS = (20,21,22)
FIXTURES = ('Alder','Beacon','Cypress','Delta','Ember','Fable')
VARIANTS = ('b1_only','b2_only','both_control','both_exact','both_none',
            'prompt_only_dual','same_policy_dual')


def require(ok, reason):
    if not ok: raise ValueError(reason)


def sha(data): return hashlib.sha256(data).hexdigest()


def audit(path):
    path=Path(path)
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    require(h.hexdigest()==EXPECTED_SAFE,'ORIGINAL_SAFE_ZIP_SHA_MISMATCH')
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        require(len(names)==len(set(names)),'DUPLICATE_ARCHIVE_MEMBER')
        p=json.loads(z.read('RUN397_PROGRESS.json'))
        require(p['status']=='ALL_ARMS_STRUCTURALLY_RECORDED' and
                p['canonical_gate_pass'] is False and p['step2_exit']=='UTILITY_FAIL',
                'PROGRESS_GATE_OR_STATUS')
        expected={f'{a}_s{s}' for a in ARMS for s in SEEDS}
        require(set(p['completed'])==expected,'NINE_ARMS_MISSING_OR_EXTRA')
        values={};tool_shas={}
        for arm in ARMS:
            for seed in SEEDS:
                rid=f'{arm}_s{seed}'
                record=p['completed'][rid]
                prefix=record['attempt']+'/'
                raw=z.read(prefix+'tool_'+rid+'.json')
                summary_raw=z.read(prefix+'summary_'+rid+'.json')
                require(sha(raw)==record['validated']['sha256']['tool'] and
                        sha(summary_raw)==record['validated']['sha256']['summary'],
                        'PROGRESS_PINNED_ROW_SOURCE_DRIFT')
                tool_shas[rid]=sha(raw)
                data=json.loads(raw)
                summary=json.loads(summary_raw)
                require(len(data['rows'])==42 and record['validated']['rows']==42 and
                        data['canonical_gate_pass'] is False,
                        'ROW_COUNT_OR_GATE_DRIFT')
                seen=set()
                for row in data['rows']:
                    key=(row['fixture'],row['variant'])
                    require(key not in seen and key[0] in FIXTURES and key[1] in VARIANTS,
                            'ROW_IDENTITY_INVALID')
                    seen.add(key)
                    score=row['score']['utility']
                    require(type(score) in (int,float) and math.isfinite(score) and 0<=score<=1,
                            'UTILITY_NOT_FINITE_UNIT')
                    values[(arm,seed,*key)]=score
                require(seen=={(f,v) for f in FIXTURES for v in VARIANTS},
                        'ROW_COHORT_INCOMPLETE')
                for v in VARIANTS:
                    actual=sum(values[(arm,seed,f,v)] for f in FIXTURES)/len(FIXTURES)
                    reported=summary['paired_tool']['mean_utility'][v]
                    require(abs(actual-reported)<1e-12,'SUMMARY_MEAN_MISMATCH')
        require(len(values)==378,'COHORT_TOTAL_NOT_378')
        means={a:{v:sum(values[(a,s,f,v)] for s in SEEDS for f in FIXTURES)/18
                  for v in VARIANTS} for a in ARMS}
        def paired(a,b,v):
            ds=[values[(a,s,f,v)]-values[(b,s,f,v)] for s in SEEDS for f in FIXTURES]
            return {'mean':sum(ds)/len(ds),'wins':sum(d>1e-12 for d in ds),
                    'ties':sum(abs(d)<=1e-12 for d in ds),
                    'losses':sum(d< -1e-12 for d in ds),'pairs':len(ds)}
        p_vs_off=paired('P','O','both_exact')
        p_vs_shared=paired('P','S','both_exact')
        within_p={v:means['P']['both_exact']-means['P'][v]
                  for v in ('b1_only','same_policy_dual')}
        strict={a:means[a]['both_exact']>max(means[a]['b1_only'],
                     means[a]['same_policy_dual']) for a in ARMS}
        return {'schema':'V13_RUN487_INDEPENDENT_ORIGINAL_NATIVE378_RAW_AUDIT_V1',
                'status':'RAW_NATIVE378_RECOMPUTED_NO_GATE_PROMOTION',
                'safe_zip_sha256':EXPECTED_SAFE,'rows':len(values),
                'original_tool_sha256':tool_shas,'arm_mean_utility':means,
                'pointer_minus_off_both_exact':p_vs_off,
                'pointer_minus_shared_both_exact':p_vs_shared,
                'pointer_both_exact_minus_controls':within_p,
                'strict_dominance':strict,'canonical_gate_pass':False,
                'step2_exit':'UTILITY_FAIL','b3_l1':'FAIL',
                'body_jepa':'UNAVAILABLE','jepa_weight':0,'redmi_measured':False,
                'claim_limit':'Independent raw replay of exploratory Linux-native378; not ten-episode STEP2 acceptance or B3/Body-JEPA proof.'}


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: run487_native378_independent_raw_audit.py <original-safe-zip>')
    print(json.dumps(audit(sys.argv[1]),indent=2,sort_keys=True))
