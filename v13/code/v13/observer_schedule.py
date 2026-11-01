"""Observer scheduling as a deployment knob (Canon §22.2.4, §73, §97.1).

"Observer Scheduling ist ein Deployment-Regler, keine Architekturänderung": the cognitive design still
offers both bodies an observer pass per event; this module only decides *when/physically how* the passes
run. Offers keep their logical role, provenance and validity; JEF (focal loop) still decides whether an
offer is needed in focus.

  A_THEN_B_SEQUENTIAL  pre-answer passes B1 then B2 (the behaviour before this knob; default)
  B_THEN_A_SEQUENTIAL  pre-answer passes B2 then B1
  ALWAYS_BOTH_ASYNC    both pre-answer passes at once; only when both bodies can stay resident
                       (AG13 residency on, resource mode allows two bodies), else sequential with a reason
  JEF_FIRST_THEN_BOTH  JEF answers without pre-answer passes; the planned bodies run post-commit
  SAMPLED_OBSERVER     pre-answer passes only on a deterministic sample of events (``observer_sample_rate``)
  ON_DEMAND_REENTRY    no initial pass; a body runs only when the focal loop asks for a re-entry

Claim limit: physical parallelism is a CPU/RAM question measured on the Redmi (WP-R); the cloud only
checks semantics. §73 says B1/B2 physical scheduling is sequential first, hence the default.
"""
import hashlib
from concurrent.futures import ThreadPoolExecutor
import time

SCHEDULES=('A_THEN_B_SEQUENTIAL','B_THEN_A_SEQUENTIAL','ALWAYS_BOTH_ASYNC','JEF_FIRST_THEN_BOTH','SAMPLED_OBSERVER','ON_DEMAND_REENTRY')
DEFAULT='A_THEN_B_SEQUENTIAL'
ORDER=('B1_DETAIL','B2_GIST')

def sampled(event_id,rate):
    """Deterministic per event (replayable), independent of call order."""
    if rate>=1:return True
    if rate<=0:return False
    return int(hashlib.sha256(str(event_id).encode()).hexdigest()[:8],16)/2**32<rate

def plan(schedule,roles,event_id,rate=.5,parallel_ok=False):
    """Which bodies run before the answer, in which order, in parallel or not, and which run post-commit.

    roles: bodies the effort/wake policy already allows this turn (resource caps applied before).
    """
    if schedule not in SCHEDULES:raise ValueError('observer_schedule: '+'|'.join(SCHEDULES))
    roles=[r for r in ORDER if r in roles]
    out={'schedule':schedule,'pre':roles,'parallel':False,'post':None,'reentry':True,'reason':None}
    if schedule=='B_THEN_A_SEQUENTIAL':out['pre']=roles[::-1]
    elif schedule=='ALWAYS_BOTH_ASYNC':
        if len(roles)>1 and parallel_ok:out['parallel']=True
        elif len(roles)>1:out['reason']='ASYNC_NEEDS_TWO_RESIDENT_BODIES'
    elif schedule=='JEF_FIRST_THEN_BOTH':out.update(pre=[],post=roles)
    elif schedule=='SAMPLED_OBSERVER':
        hit=sampled(event_id,rate);out.update(sampled=hit,sample_rate=rate)
        if not hit:out.update(pre=[],post=[],reason='SAMPLED_OUT')
    elif schedule=='ON_DEMAND_REENTRY':out.update(pre=[],post=[],reason='ON_DEMAND_ONLY')
    return out

def run(p,ask,end,on_error,clock=time.monotonic,cancelled=()):
    """Run the pre-answer passes of plan ``p``. ``ask(role, use_peer)`` returns an offer.

    Sequential passes see the peer message of the earlier body (as before); parallel passes start
    without one, both peer messages exist afterwards for re-entry. Cancellation propagates.
    """
    offers=[];roles=list(p['pre'])
    if not p['parallel']:
        for role in roles:
            if clock()+1>=end:break
            try:offers.append(ask(role,True))
            except cancelled:raise
            except Exception as exc:on_error(role,exc)
        return offers
    if clock()+1>=end:return offers
    with ThreadPoolExecutor(max_workers=len(roles),thread_name_prefix='v13-observer') as pool:
        futures=[(role,pool.submit(ask,role,False)) for role in roles]
        first=None
        for role,f in futures:
            try:offers.append(f.result())
            except cancelled as exc:first=first or exc
            except Exception as exc:on_error(role,exc)
        if first is not None:raise first
    return offers

def background(schedule,event_id,rate,roles,planned_post=None):
    """Post-commit observer roles under the schedule (the pass never changes the committed answer)."""
    if schedule=='ON_DEMAND_REENTRY':return []
    if schedule=='SAMPLED_OBSERVER' and not sampled(event_id,rate):return []
    if schedule=='JEF_FIRST_THEN_BOTH' and planned_post is not None:return [r for r in ORDER if r in planned_post]
    return list(roles)
