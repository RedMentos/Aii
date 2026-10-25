"""AGE0d source-aware arithmetic checker on frozen real STEP2 C3 answer replay.

No oracle enters check_answer(); oracle is used only for offline scoring.
Never delivers corrections, grants rights, learns, or changes frozen STEP2.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

SOURCE_BUDGET=re.compile(r'\bbudget\s+(\d+)\s+euros\b',re.I)
SOURCE_COST=re.compile(r'\bOption\s+([AB]):\s+cost\s+(\d+)\s+euros\b',re.I)


def source_budget_and_costs(fixture):
    prior,current=fixture['prior'],fixture['current']
    old=list(SOURCE_BUDGET.finditer(prior));new=list(SOURCE_BUDGET.finditer(current))
    if len(new)==1 and 'Updated rules, overriding the earlier rules:' in current:
        b,field=new[0],'current'
    elif len(old)==1 and not new:b,field=old[0],'prior'
    else:return None
    opts=list(SOURCE_COST.finditer(current))
    if len(opts)!=2 or {x.group(1) for x in opts}!={'A','B'}:return None
    refs={'budget':{'field':field,'char_start':b.start(),'char_end':b.end(),
                    'quote':fixture[field][b.start():b.end()]},
          'options':{x.group(1):{'field':'current','char_start':x.start(),'char_end':x.end(),
                                'quote':current[x.start():x.end()]} for x in opts}}
    return int(b.group(1)),{x.group(1):int(x.group(2)) for x in opts},refs


def answer_rows(raw):
    try:answer=json.loads(raw)
    except (TypeError,ValueError):return None
    if not isinstance(answer,dict) or not isinstance(answer.get('options'),list):return None
    rows=answer['options']
    if len(rows)!=2 or {x.get('entity') for x in rows if isinstance(x,dict)}!={'A','B'}:return None
    if any(not isinstance(x,dict) or type(x.get('remaining')) is not int for x in rows):return None
    return {x['entity']:x['remaining'] for x in rows}


def check_answer(fixture,raw):
    base={'status':'ABSTAIN','shadow_only':True,'delivery_authorized':False,
          'learning_authorized':False,'age_reopen_authorized':False}
    source=source_budget_and_costs(fixture)
    if source is None:return base|{'reason':'SOURCE_UNAVAILABLE_OR_AMBIGUOUS'}
    actual=answer_rows(raw)
    if actual is None:return base|{'reason':'ANSWER_UNAVAILABLE_OR_AMBIGUOUS'}
    budget,costs,refs=source
    wrong={entity:{'expected':budget-costs[entity],'actual':actual[entity]}
           for entity in ('A','B') if actual[entity]!=budget-costs[entity]}
    if wrong:return base|{'status':'SHADOW_ARITHMETIC_MISMATCH',
                          'reason':'SOURCE_BOUND_REMAINING_BUDGET_CONTRADICTION',
                          'mismatches':wrong,'source_refs':refs}
    return base|{'status':'SHADOW_AGREES','reason':'AGREES_WITH_SOURCE_ARITHMETIC'}


def replay(dataset):
    fixtures={f['id']:f for f in dataset['fixtures']}
    out=[];tot={'tp':0,'fp':0,'fn':0,'tn':0,'abstain_wrong':0,'abstain_correct':0,'unscorable':0}
    for row in dataset['rows']:
        f=fixtures[row['fixture']];c=check_answer(f,row.get('raw_answer'))
        oracle=f['oracle']['options'];expected={x['entity']:x['remaining'] for x in oracle}
        source=source_budget_and_costs(f)
        if source is not None and all(v is not None for v in expected.values()):
            budget,costs,_=source
            if any(budget-costs[k]!=expected[k] for k in ('A','B')):
                raise ValueError('source-derived arithmetic disagrees with frozen oracle')
        actual=answer_rows(row.get('raw_answer'))
        truth=None if actual is None or any(v is None for v in expected.values()) else any(actual[k]!=expected[k] for k in ('A','B'))
        detected=c['status']=='SHADOW_ARITHMETIC_MISMATCH'
        if truth is None:key='unscorable'
        elif c['status']=='ABSTAIN':key='abstain_wrong' if truth else 'abstain_correct'
        elif detected:key='tp' if truth else 'fp'
        else:key='fn' if truth else 'tn'
        tot[key]+=1
        out.append({'fixture':f['id'],'variant':row['variant'],'status':c['status'],
                    'reason':c['reason'],'truth_wrong_remaining':truth,
                    'score_bucket':key,'mismatches':c.get('mismatches',{}),
                    'source_refs':c.get('source_refs',{}),
                    'delivery_authorized':False,'learning_authorized':False})
    scorable=len(out)-tot['unscorable']
    coverage=(tot['tp']+tot['fp']+tot['fn']+tot['tn'])/scorable if scorable else 0
    fp_denom=tot['fp']+tot['tn'];wrong_denom=tot['tp']+tot['fn']+tot['abstain_wrong']
    fpr=tot['fp']/fp_denom if fp_denom else None
    recall=tot['tp']/wrong_denom if wrong_denom else None
    criteria={'scorable_at_least_35':scorable>=35,'coverage_at_least_half':coverage>=.5,
              'false_positive_rate_at_most_10pct':fpr is not None and fpr<=.1,
              'wrong_remaining_recall_at_least_half':recall is not None and recall>=.5}
    return {'schema':'V13_RUN183_STEP2_AGE0D_SHADOW_REPLAY_V1',
            'evidence_class':'HISTORICAL_LINUX_NATIVE_C3_ANSWER_REPLAY',
            'rows':len(out),'scorable':scorable,'counts':tot,'coverage':coverage,
            'false_positive_rate':fpr,'wrong_remaining_recall':recall,
            'criteria':criteria,'verdict':'AGE0D_ARITHMETIC_REPLAY_SUPPORTED' if all(criteria.values()) else 'AGE0D_ARITHMETIC_REPLAY_FAIL',
            'cases':out,'delivery_authorized':False,'age_reopen_authorized':False,
            'step2_promoted':False,'b3_promoted':False,'v13_complete':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();data=Path(a.dataset).read_bytes();j=json.loads(data)
    if j.get('proof_kind')!='STEP2_PREREGISTERED_SEMANTIC_UTILITY' or j.get('status')!='UTILITY_FAIL' or len(j['rows'])!=70:
        raise ValueError('frozen STEP2 cohort mismatch')
    result=replay(j);result['dataset_sha256']=hashlib.sha256(data).hexdigest()
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},sort_keys=True))

if __name__=='__main__':main()
