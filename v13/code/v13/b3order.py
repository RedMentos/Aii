"""B3-H8 training order, enforced from evidence (WP-N22).

Canon B3-H8 [LOCKED]:

   1. freeze B1 body                         FREEZE_B1        sender/receiver revision now == the one pinned in the bridge manifest
   2. freeze B2 body                         FREEZE_B2
   3. collect paired grounded experiences    PAIRED           manifest train.samples >= MIN_PAIRED
   4. train sender selector/projector + receiver adapter
                                             TRAIN_BRIDGE     manifest sha256 + train record
   5. calibrate receiver distribution        CALIBRATE        valid B3-H4 ReceiverCalibration (b3calibration.validity)
   6. evaluate L1 utility                    L1_UTILITY       l1_gate verdict PASS
   7. if passed -> L2 prefix shadow test     L2_SHADOW        l2_gate PASS
   8. if passed -> tiny L3 residual shadow   L3_SHADOW        l3_gate PASS
   9. only then receiver-side/body co-adaptation
                                             CO_ADAPTATION    co_adaptation_gate PASS
  10. router learning remains separate and later
                                             ROUTER_LEARNING  router_gate PASS

A step counts as done only when its own evidence is present AND every earlier step is done; a later
record on top of a missing earlier one is an ORDER_VIOLATION (reported, never silently accepted).
``require`` refuses to start a step whose predecessors are missing.

``check_job`` enforces "do not jointly move sender bridge, receiver backbone, receiver MoE router":
a training job names the parameter groups it updates; more than one of those three is refused, a
receiver backbone/router update is refused before step 9/10, and the router never moves with anything else.

Today (WP-J): no bridge passes L1, so the next allowed step is at most L1 and L2-L4 stay locked by canon.
"""
from pathlib import Path
from . import b3calibration
from .b3degrade import manifest,RECEIVER,SENDER

STEPS=('FREEZE_B1','FREEZE_B2','PAIRED','TRAIN_BRIDGE','CALIBRATE','L1_UTILITY','L2_SHADOW','L3_SHADOW','CO_ADAPTATION','ROUTER_LEARNING')
GATES={'L1_UTILITY':'l1_gate','L2_SHADOW':'l2_gate','L3_SHADOW':'l3_gate','CO_ADAPTATION':'co_adaptation_gate','ROUTER_LEARNING':'router_gate'}
MIN_PAIRED=64                 # BOOT: fewer paired experiences are not a training set
GROUPS=('sender_bridge','receiver_adapter','receiver_backbone','receiver_router','sender_backbone')
NEVER_JOINT=('sender_bridge','receiver_backbone','receiver_router')

def _rev(revs,role):
    v=(revs or {}).get(role);return None if v in (None,'unavailable') else v

def evidence(home,direction,revisions):
    """{step: True|False} from the bridge manifest and the current body revisions."""
    man=manifest(home,direction) or {};snd,rcv=SENDER[direction],RECEIVER[direction]
    b1=_rev(revisions,'B1_DETAIL');b2=_rev(revisions,'B2_GIST')
    pinned={'B1_DETAIL':man.get('sender_revision') if snd=='B1_DETAIL' else man.get('receiver_revision'),
            'B2_GIST':man.get('sender_revision') if snd=='B2_GIST' else man.get('receiver_revision')}
    train=man.get('train') or {}
    cal_ok=b3calibration.validity(man.get('receiver_calibration'),_rev(revisions,rcv),_rev(revisions,snd))[0]
    ev={'FREEZE_B1':b1 is not None and pinned['B1_DETAIL']==b1,'FREEZE_B2':b2 is not None and pinned['B2_GIST']==b2,
        'PAIRED':(train.get('samples') or 0)>=MIN_PAIRED,'TRAIN_BRIDGE':bool(man.get('sha256')) and bool(train),'CALIBRATE':cal_ok}
    for step,key in GATES.items():ev[step]=((man.get(key) or {}).get('verdict')=='PASS')
    return ev

def status(home,direction,revisions):
    ev=evidence(home,direction,revisions);done=[];violations=[];ok=True
    for s in STEPS:
        if ev[s] and ok:done.append(s)
        elif ev[s]:violations.append(s)  # evidence for a later step on top of a missing earlier one
        else:ok=False
    nxt=next((s for s in STEPS if s not in done),None)
    return {'done':done,'next':nxt,'violations':violations,'status':'ORDER_VIOLATION' if violations else 'IN_ORDER',
            'evidence':ev,'locked_by_canon':[s for s in ('L2_SHADOW','L3_SHADOW','CO_ADAPTATION','ROUTER_LEARNING') if s not in done and s!=nxt]}

def require(home,direction,revisions,step):
    """Raise unless ``step`` is the next allowed step (or already done)."""
    if step not in STEPS:raise ValueError('B3-H8: unbekannter Schritt '+str(step))
    st=status(home,direction,revisions)
    if step in st['done']:return st
    if step!=st['next']:raise PermissionError('B3-H8: %s erst nach %s'%(step,st['next']))
    return st

def check_job(groups,st):
    """Training-job guard: ``groups`` = parameter groups the job updates; ``st`` = status() of that direction."""
    g=set(groups);bad=g-set(GROUPS)
    if bad:raise ValueError('unbekannte Parametergruppen: '+', '.join(sorted(bad)))
    joint=sorted(g&set(NEVER_JOINT))
    if len(joint)>1:raise PermissionError('B3-H8: nicht gemeinsam bewegen: '+', '.join(joint))
    if 'receiver_router' in g and len(g)>1:raise PermissionError('B3-H8: Router-Lernen bleibt getrennt')
    if 'receiver_router' in g and st['next'] not in ('ROUTER_LEARNING',None):raise PermissionError('B3-H8: Router-Lernen erst nach der Ko-Adaption')
    if g&{'receiver_backbone','sender_backbone'} and STEPS.index(st['next'] or 'ROUTER_LEARNING')<STEPS.index('CO_ADAPTATION'):
        raise PermissionError('B3-H8: Körper-Gewichte bleiben eingefroren bis nach L3 (Schritt 9)')
    return True

def report(r):
    revs=r.revisions() if hasattr(r,'revisions') else {}
    return {d:status(Path(r.home),d,revs) for d in RECEIVER}
