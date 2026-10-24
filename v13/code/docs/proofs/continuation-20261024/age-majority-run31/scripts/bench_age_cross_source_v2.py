#!/usr/bin/env python3
"""Fresh Run31 seeds 100..199, prereg SHA fixed before cohort."""
import json
import random
import age_cross_source_signal as V1
import age_cross_source_signal_v2 as V2

PREREG_SHA='ed420b65893ff7b1e03a6edb30019415ab5f7537e872a8b33ba9aff2220b67d5'

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
    for seed in range(100,200):
        for shift in (False,True):
            b,c=make(seed,shift)
            rows.append({'seed':seed,'actual_shift':shift,'v1':V1.assess(b,c)['status'],
                         'v2':V2.assess(b,c)['status']})
    def count(arm,shift):return sum(r[arm]=='SHIFT_CANDIDATE' for r in rows if r['actual_shift']==shift)
    detected=count('v2',True);false=count('v2',False)
    return {'schema':'V13_RUN31_AGE_SOURCE_COHORT_V2','prereg_sha256':PREREG_SHA,
            'seed_range':[100,199],'v2_shift_detected':detected,'v2_false_shift':false,
            'v1_shift_detected':count('v1',True),'v1_false_shift':count('v1',False),
            'criteria':{'shift_at_least_90':detected>=90,'false_shift_at_most_5':false<=5},
            'verdict':'PASS_SYNTHETIC_ONLY' if detected>=90 and false<=5 else 'FAIL',
            'claim':'NO_AGE_INTEGRATION_NO_REAL_SOURCE_PROOF','rows':rows}

if __name__=='__main__':print(json.dumps(run(),indent=2))
