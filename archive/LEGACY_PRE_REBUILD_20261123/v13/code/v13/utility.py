"""Exact field scoring for the preregistered STEP2 proof; no runtime decisions.

Oracles never enter native prompts. Numeric word presence earns no credit.
"""
import json
import math

OPTION_FIELDS=('cost','remaining','days','local','eligible')

def score_decision(raw,oracle):
    checks={};errors=[]
    def unique_object(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate JSON key')
            result[key]=value
        return result
    try:
        answer=json.loads(raw,object_pairs_hook=unique_object) if isinstance(raw,str) else raw
        if not isinstance(answer,dict) or set(answer)!={'project','action','options'}:raise ValueError('top-level schema')
        if not isinstance(answer['options'],list) or len(answer['options'])!=len(oracle['options']):raise ValueError('option count')
        by_entity={}
        for option in answer['options']:
            if not isinstance(option,dict) or set(option)!={'entity',*OPTION_FIELDS}:raise ValueError('option schema')
            if not isinstance(option['entity'],str) or option['entity'] in by_entity:raise ValueError('duplicate/invalid entity')
            by_entity[option['entity']]=option
        if set(by_entity)!={o['entity'] for o in oracle['options']}:raise ValueError('entity assignment')
        checks['project']=type(answer['project']) is str and answer['project']==oracle['project']
        checks['action']=type(answer['action']) is str and answer['action']==oracle['action']
        for expected in oracle['options']:
            actual=by_entity[expected['entity']]
            for field in OPTION_FIELDS:
                value=expected[field];got=actual[field]
                # bool is an int in Python; exact types keep false != 0.
                checks[expected['entity']+'.'+field]=type(got) is type(value) and got==value
        errors=[name for name,passed in checks.items() if not passed]
    except (ValueError,TypeError,json.JSONDecodeError) as exc:
        errors=['invalid:'+str(exc)];checks={}
    denominator=2+len(OPTION_FIELDS)*len(oracle['options'])
    return {'utility':sum(checks.values())/denominator,'exact':len(checks)==denominator and all(checks.values()),
            'field_checks':checks,'contradictions':errors,'contradiction_count':len(errors),'scored_fields':denominator}

def _row_utility(row):
    """Failed inference is zero; an explicit malformed score is not evidence."""
    score=row.get('score')
    if score is None:
        return 0.
    if not isinstance(score,dict):
        raise ValueError('invalid score object')
    if 'utility' not in score:
        return 0.
    value=score['utility']
    if type(value) not in (int,float) or not 0. <= value <= 1. or not math.isfinite(value):
        raise ValueError('utility must be a finite number in [0,1], not bool')
    return float(value)

def paired_utility(rows,fixture_ids):
    """Require every preregistered pair; failed inference scores zero, never dropped.

    Reject malformed numeric scores and duplicate cohort IDs without allowing
    an unmeasured, nonfinite or boolean value into a completion/gate decision.
    """
    variants=sorted({r['variant'] for r in rows});scores={};errors={}
    if not fixture_ids or len(fixture_ids)!=len(set(fixture_ids)):
        errors['_cohort']='empty or duplicate preregistered fixture ID'
    for variant in variants:
        vr=[r for r in rows if r['variant']==variant]
        ids=[r['fixture'] for r in vr]
        if len(ids)!=len(set(ids)) or set(ids)!=set(fixture_ids):
            errors[variant]='missing or duplicate preregistered episode'
            continue
        try:
            scores[variant]=sum(_row_utility(r) for r in vr)/len(fixture_ids)
        except ValueError:
            errors[variant]='invalid explicit utility score'
    required={'b1_only','b2_only','both_none','both_exact','both_control','same_policy_dual','prompt_only_dual'}
    complete=not errors and set(scores)==required
    best_solo=max((scores.get(v,0.) for v in ('b1_only','b2_only')),default=0.)
    gains={v:scores.get(v,0.)-best_solo for v in ('both_none','both_exact','both_control')}
    pairs={v:{r['fixture']:r for r in rows if r['variant']==v} for v in variants}
    distinct_errors=False
    if complete:
        b1_wins=b2_wins=0
        for fid in fixture_ids:
            a=_row_utility(pairs['b1_only'][fid]);b=_row_utility(pairs['b2_only'][fid])
            b1_wins+=a>b;b2_wins+=b>a
        distinct_errors=bool(b1_wins and b2_wins)
    candidate=scores.get('both_exact',0.)
    return {'complete':complete,'coverage_errors':errors,'mean_utility':scores,'best_solo':best_solo,'gain_over_best_solo':gains,
            'b1_b2_each_win_an_episode':distinct_errors,'preregistered_primary':'both_exact',
            'scoped_utility_gate_pass':complete and distinct_errors and candidate>best_solo and candidate>scores.get('same_policy_dual',0.) and candidate>scores.get('prompt_only_dual',0.)}
