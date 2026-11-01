"""WP-U5 §69 / §48.10 representation anchor as a stability regulator (not a rigid "stay as before").

Per weight-training batch (AG6) the KL-to-base anchor strength is set from two measured signals:
  novelty    how new the batch's domain is: 1 - mean best relevance (memory.relevance) of each item prompt to the
             active memories outside the batch (no other memories -> 1.0, a completely new domain)
  stability  how settled the old skill is: N10 metaplasticity feature `stability` of the learning path `weights`
multiplier m = 1 + ANCHOR.protected_old_skill_weight x stability - ANCHOR.new_domain_relaxation x novelty x (1 - stability)
  floor  ANCHOR.pretrained_geometry_weight (pretrained geometry always keeps a share of the anchor)
  shared ANCHOR.shared_layer_priority as a further floor when the trained layers are shared by all inputs (dense
         FFN/attention LoRA; the measured live targets w1-w3 are shared)
  cap    MAX_MULT
SHADOW (default): the policy is recorded in the batch, training uses the measured anchor unchanged. ACTIVE (only by
`:anchor active`, explicit human): the trainer's anchor_weight is scaled by m for that batch. Drift caps
(WP-S5, guards.stability_envelope) are never relaxed by this module: a lower anchor must still pass the same gate.
"""
from .common import dumps

KEY='U5_ANCHOR';REVISION='u5-anchor-v1'
ANCHOR={'pretrained_geometry_weight':.25,'protected_old_skill_weight':.60,'new_domain_relaxation':.55,'shared_layer_priority':.75}  # §69 BOOT, not measured
MAX_MULT=2.  # BOOT
SHARED_TARGETS=frozenset({'w1','w2','w3','q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj','in_proj','out_proj'})

def novelty(store,items):
    from .memory import relevance
    ids={i.get('memory_id') for i in items}
    old=[r['key_text']+' '+r['value'] for r in store.rows('SELECT id,key_text,value FROM memories WHERE active=1') if r['id'] not in ids]
    if not items:return 0.
    if not old:return 1.
    best=[max(relevance(i['prompt'],o) for o in old) for i in items]
    return round(1-sum(best)/len(best),4)

def stability(store,path='weights'):
    try:
        from .neuromod import Neuromod
        return float(Neuromod(store).gate(path)['meta']['features']['stability'])
    except Exception:return 0.

def policy(nov,stab,shared=True):
    m=1+ANCHOR['protected_old_skill_weight']*stab-ANCHOR['new_domain_relaxation']*nov*(1-stab)
    floor=max(ANCHOR['pretrained_geometry_weight'],ANCHOR['shared_layer_priority'] if shared else 0.)
    reason='OLD_SKILL_PROTECTED' if m>1 else ('NEW_DOMAIN_RELAXED' if m<1 else 'NEUTRAL')
    m=min(MAX_MULT,max(floor,m))
    return {'novelty':round(nov,4),'stability':round(stab,4),'shared_layers':shared,'floor':floor,'multiplier':round(m,4),'reason':reason}

def mode(store):return (store.state(KEY,None)[0] or {}).get('mode','SHADOW')

def set_mode(store,m,authority='SYSTEM'):
    if m not in {'SHADOW','ACTIVE'}:raise ValueError('SHADOW|ACTIVE')
    if m=='ACTIVE' and authority!='EXPLICIT_HUMAN':raise PermissionError('ACTIVE nur per expliziter Nutzerfreigabe (Age 0)')
    st,v=store.state(KEY,None);st=st or {'revision':REVISION};st['mode']=m;store.set_state(KEY,st,expected=v)
    store.log('anchor_mode',None,{'mode':m,'authority':authority});return m

def for_batch(store,items,trainer):
    """Policy for one batch. Returns (policy row, cfg override or None). The override is only set in ACTIVE."""
    cfg=getattr(trainer,'cfg',None)
    targets=set((cfg or {}).get('targets') or ())
    shared=bool(targets & SHARED_TARGETS) if targets else True
    p=policy(novelty(store,items),stability(store),shared);p['mode']=mode(store)
    base=(cfg or {}).get('anchor_weight')
    p['base_anchor_weight']=base
    if isinstance(base,(int,float)) and not isinstance(base,bool):
        p['proposed_anchor_weight']=round(base*p['multiplier'],4)
        if p['mode']=='ACTIVE':p['applied']=True;return p,{'anchor_weight':p['proposed_anchor_weight']}
    p['applied']=False;return p,None

def report(store):
    st=store.state(KEY,None)[0] or {}
    return {'revision':REVISION,'mode':st.get('mode','SHADOW'),'knobs':ANCHOR,'max_multiplier':MAX_MULT,
            'claim_limit':'Scales the KL-to-base anchor of weight training only; drift gates stay unchanged; BOOT knobs not measured'}

def operator_command(r,args):
    """:anchor [status|shadow|active]"""
    if not args or args==['status']:return dumps(report(r.store))
    if args==['shadow']:return dumps({'mode':set_mode(r.store,'SHADOW')})
    if args==['active']:return dumps({'mode':set_mode(r.store,'ACTIVE','EXPLICIT_HUMAN')})
    raise ValueError(':anchor [status|shadow|active]')
