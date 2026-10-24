"""V13 Context OS §8.3 fail-closed pin invariant for ACTIVE plan candidates.

Isolated guard; does not compress, alter sources, run models or enable ACTIVE.
A plan that cannot fit pinned bytes is NOT silently allowed to drop pins.
"""

SCHEMA='V13_CONTEXT_PIN_GUARD_V1'


def validate(plan):
    """Check closed ContextPlan subset before any future ACTIVE application."""
    if type(plan) is not dict or type(plan.get('items')) is not list or type(plan.get('budget')) is not dict:
        raise ValueError('ContextPlan items and budget required')
    violations=[];ids=set();pins=0
    for item in plan['items']:
        if type(item) is not dict or type(item.get('item_id')) is not str or type(item.get('layer')) is not str:
            raise ValueError('invalid ContextPlan item')
        if item['item_id'] in ids:
            violations.append('DUPLICATE_ITEM')
        ids.add(item['item_id'])
        if item.get('pinned') is True:
            pins+=1
            if item.get('form')!='RAW' or item.get('layer')!='RAW_HISTORY':
                violations.append('PIN_NOT_RAW:'+item['item_id'])
        if item.get('restored') is True and item.get('form')!='RAW':
            violations.append('RESTORED_NOT_RAW:'+item['item_id'])
    budget=plan['budget'];planned=budget.get('planned_chars');limit=budget.get('chars')
    if type(planned) is not int or type(limit) is not int or planned<0 or limit<=0:
        raise ValueError('invalid budget')
    if planned>limit:violations.append('OVER_BUDGET')
    return {'schema':SCHEMA,'status':'REJECT_ACTIVE' if violations else 'PASS_INVARIANTS',
            'violations':violations,'pinned_items':pins,
            'authority':'SHADOW_GUARD_NO_RUNTIME_ACTION',
            'source_restoration_proven':False,'canonical_gate_pass':False}


def choose_budget_forms(turns,budget,stable_chars,query_chars,compressed_size):
    """Reference safe budget strategy; unpinned turns only are disposable.

    Turns: (id, raw_chars, pinned, restored). Never compress restored.
    Returns NO_PLAN if the pinned minimum cannot fit. This is not the full
    ContextOS planner; it is an isolated invariant proof/reference strategy.
    """
    if type(budget) is not int or budget<=0 or any(type(v) is not int or v<0 for v in (stable_chars,query_chars)):
        raise ValueError('invalid budget')
    if type(turns) is not list or len(turns)>10000:
        raise ValueError('bounded turns required')
    forms={};size=stable_chars+query_chars
    for ident,chars,pinned,restored in turns:
        if type(ident) is not str or type(chars) is not int or chars<0 or type(pinned) is not bool or type(restored) is not bool:
            raise ValueError('invalid turn')
        if ident in forms:raise ValueError('duplicate turn')
        forms[ident]='RAW';size+=chars
    for ident,chars,pinned,restored in turns:
        if size<=budget:break
        if pinned or restored:continue
        smaller=compressed_size.get(ident)
        if type(smaller) is int and 0<=smaller<chars:
            forms[ident]='COMPRESSED';size-=chars-smaller
    for ident,chars,pinned,restored in turns:
        if size<=budget:break
        if pinned or restored:continue
        if forms[ident]=='RAW':size-=chars
        else:size-=compressed_size[ident]
        forms[ident]='POINTER'
    return {'status':'READY' if size<=budget else 'NO_PLAN_PINNED_BUDGET',
            'forms':forms,'planned_chars':size,'budget':budget,
            'source_mutated':False,'canonical_gate_pass':False}
