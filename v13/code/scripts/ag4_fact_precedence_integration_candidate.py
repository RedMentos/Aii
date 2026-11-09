"""Build the event/source-checked AG4 precedence candidate in a copy only."""
from .skill_parity_shadow_integration_candidate import build_sources as build_parity


LIVE_ROUTE_OLD = b'''                binding=g.skills.human_binding(n)
                meta['skill']={'name':n,'route':routes[0],'prior_route':route};_save(r.store,e['event_id'],skill=n,skill_binding=binding);return routes[0]
'''
LIVE_FILTER_OLD = b'        g=hub(r);names=g.skills.select(text)\n'
LIVE_FILTER_NEW = b'''        g=hub(r);names=g.skills.select(text)
        from ..ag4_fact_precedence_candidate import routed_eligible
        if any(not routed_eligible(r.store,n) for n in names):return route
'''
LIVE_ROUTE_NEW = b'''                binding=g.skills.human_binding(n)
                from ..ag4_fact_precedence_candidate import routed_receipt
                receipt=routed_receipt(r.store,n,routes[0],binding)
                meta['skill']={'name':n,'route':routes[0],'prior_route':route}|receipt;_save(r.store,e['event_id'],skill=n,skill_binding=binding);return routes[0]
'''
AUTO_OLD = b'''        sk=live[0];route=next(iter(routes));binding=hub(r).skills.human_binding(sk['name'])
        meta['skill']={'name':sk['name'],'route':route,'prior_route':scaffold_route(text),'automatic':True};_save(r.store,e['event_id'],skill=sk['name'],skill_binding=binding)
'''
AUTO_NEW = b'''        sk=live[0];route=next(iter(routes));binding=hub(r).skills.human_binding(sk['name'])
        from .ag4_fact_precedence_candidate import routed_receipt
        receipt=routed_receipt(r.store,sk['name'],route,binding)
        meta['skill']={'name':sk['name'],'route':route,'prior_route':scaffold_route(text),'automatic':True}|receipt;_save(r.store,e['event_id'],skill=sk['name'],skill_binding=binding)
'''
AUTO_FILTER_OLD = b'        live=matches(hub(r).skills,text,LIVE)\n'
AUTO_FILTER_NEW = b'''        live=matches(hub(r).skills,text,LIVE)
        from .ag4_fact_precedence_candidate import routed_eligible
        if any(not routed_eligible(r.store,sk['name']) for sk in live):return None
'''
OUTCOME_OLD = b'''def _human_skill_outcome(store,event_id,success,source):
    """Apply explicit human AG4 outcome via the transactional event ledger.

    The ledger is authoritative; the per-event live marker is diagnostic only.
    Re-delivery after a crash is idempotent even if that marker was not saved.
    """
    st=_load(store,event_id)
    name=st.get('skill')
    if not name:return False
    from .skills import SkillLibrary
    result=SkillLibrary(store).record_human(name,event_id,bool(success),st.get('skill_binding'))
    _save(store,event_id,skill_human_credit=bool(success),
          skill_outcome='HUMAN_CORRECTED' if result=='CORRECTED' else 'HUMAN_RATED',
          skill_rating_source=source,skill_disputed=result=='CORRECTED')
    return result!='UNCHANGED'
'''
OUTCOME_NEW = b'''def _human_skill_outcome(store,event_id,success,source):
    """Apply only current source-bound human outcomes, in one Store transaction."""
    from ..ag4_fact_precedence_candidate import reconcile
    result=reconcile(store,event_id,success,source)
    return result['status'] in {'RECORDED','CORRECTED','RETRACTED'}
'''
NEUTRAL_OLD = b'    if RATING_BAD<score<RATING_GOOD:return None\n'
NEUTRAL_NEW = b'''    if RATING_BAD<score<RATING_GOOD:
        if origin=='EXPLICIT_NOTE':
            try:_human_skill_outcome(store,event_id,None,'rating:'+event_id)
            except (KeyError,ValueError,PermissionError) as exc:
                store.log('agi_live_unavailable',event_id,{'stage':'skill_human_outcome','error':type(exc).__name__})
        return None
'''


def build_sources(source_dir):
    data = build_parity(source_dir)
    for name, old, new in (('agi/live.py', LIVE_FILTER_OLD, LIVE_FILTER_NEW),
                           ('agi/live.py', LIVE_ROUTE_OLD, LIVE_ROUTE_NEW),
                           ('agi/live.py', OUTCOME_OLD, OUTCOME_NEW),
                           ('agi/live.py', NEUTRAL_OLD, NEUTRAL_NEW),
                           ('skilllive.py', AUTO_FILTER_OLD, AUTO_FILTER_NEW),
                           ('skilllive.py', AUTO_OLD, AUTO_NEW)):
        source = data[name]
        if source.count(old) != 1:
            raise ValueError('ambiguous AG4 outcome anchor: ' + name)
        data[name] = source.replace(old, new, 1)
    return data
