#!/usr/bin/env python3
"""Fixed Run30 100-seed cohort; see PREREG_RUN30.md before interpreting."""
import json
import random
from age_cross_source_signal import assess

def make(seed,shift):
    rng=random.Random(seed)
    base={f'case{i}':i%2 for i in range(5)}
    rows=[]
    for phase in ('baseline','current'):
        for case,label in base.items():
            if phase=='current' and shift:label=1-label
            for j in range(4):
                observed=label^(rng.random()<.1)
                rows.append((phase,{'case_id':case,'source_id':f'source{j}',
                                    'label':int(observed),'source_quality':1.}))
    return [r for p,r in rows if p=='baseline'],[r for p,r in rows if p=='current']

def run():
    rows=[]
    for seed in range(100):
        for shift in (False,True):
            b,c=make(seed,shift)
            result=assess(b,c)
            rows.append({'seed':seed,'actual_shift':shift,'status':result['status'],
                         'qualified_cases':result['qualified_cases'],'changed_cases':result['changed_cases']})
    detected=sum(r['status']=='SHIFT_CANDIDATE' for r in rows if r['actual_shift'])
    false=sum(r['status']=='SHIFT_CANDIDATE' for r in rows if not r['actual_shift'])
    return {'schema':'V13_RUN30_AGE_SOURCE_COHORT_V1','seed_range':[0,99],
            'prereg_sha256':'5083cd0966e978a200381ba41c7a69b9594090f62c197f14b1db50000debf1ea',
            'shift_detected':detected,'false_shift':false,
            'criteria':{'shift_at_least_90':detected>=90,'false_shift_at_most_5':false<=5},
            'verdict':'PASS' if detected>=90 and false<=5 else 'FAIL',
            'claim':'SYNTHETIC_ONLY_NO_AGE_INTEGRATION','rows':rows}

if __name__=='__main__':
    r=run();print(json.dumps(r,indent=2))
