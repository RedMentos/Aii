"""WP-N11 two distinct body halves, wired end to end (user decision 2026-10-09: many distinct models).

B1_DETAIL (LFM2.5-1.2B, fine/detail) and B2_GIST (Qwen3.5-0.8B, gist) are two different weight files.
This module joins three pieces that existed separately:
- AG0 slots (agi/slots.py): every installed model becomes a slot; ``ModelManager.path_for`` asks
  ``route(slot, turn key)`` which revision serves this turn, so a RAMP candidate really gets its share
  of turns (before, route() was bookkeeping only).
- AG13 residency (agi/residency.py): the bodies are the "experts" of a two-half mixture. A body is
  loaded only when the wake plan calls it (none|detail|gist|both), stays resident while it fits the RAM
  budget and is evicted by value (recency-weighted use) or at once under memory pressure.
  C3 (the speaker) is pinned like a shared/router path.
- RunnerPool: holds several llama-server processes at once under that budget instead of exactly one.

``body_residency_mb`` = 0 keeps the old one-process-at-a-time pool (fallback, no residency).
Sizes come from measured profiles per model file (``body_sizes``: non-reclaimable Anon + hot file pages; cloud
lower bound shipped, a Termux run imported with ``:resources bodies import``); unmeasured files fall back to
the old file-size estimate. Redmi RSS/PSS remains a phone measurement (WP-R).
Claim limit: neither body is a sparse MoE network; the "experts" are whole distinct bodies.
"""
from pathlib import Path
from .agi.slots import ModelSlots
from .agi.residency import ExpertResidency

from .resource_modes import mode_of
PRESSURE_MODE={'NORMAL':'GREEN','RECOVERY':'GREEN','PRESSURE':'ORANGE','CRITICAL':'RED'}  # legacy view; live code reads mode_of(guard) (§97.2)
PINNED={'C3_LANGUAGE'}            # speaker path: always resident (like router/shared layers)
BODY_ROLES=('B1_DETAIL','B2_GIST')
STATE_KEY='WP_N11_BODY_RESIDENCY'  # own state: the generic AG13 expert table stays free for a real MoE body
from .body_sizes import KV_OVERHEAD_MB,WEIGHT_FACTOR  # old estimate, kept for unmeasured files

def size_mb(models,role,store=None):
    """Residency size of the runner serving ``role`` (WP-N21: measured profile per file, else estimate)."""
    from . import body_sizes
    return body_sizes.size(models,role,store)[0]

def distinct_bodies(models):
    """True only when B1 and B2 resolve to different installed weight files (recorded sha256)."""
    from .models import model_key
    keys=[model_key(r,models.b2_control) for r in BODY_ROLES]
    if keys[0]==keys[1]:return False
    sha=[]
    for k in keys:
        e=models.installed.get(k)
        if not e or not e.get('download_complete'):return False
        sha.append(e['files'][e['main_file']]['sha256'])
    return sha[0]!=sha[1]

class BodyFabric:
    def __init__(self,runtime):
        self.r=runtime;self.models=runtime.models;self.cfg=runtime.cfg
        self.slots=ModelSlots(runtime.store)
        self.residency=ExpertResidency(runtime.store,budget_mb=max(1,self.cfg.get('body_residency_mb',0)),key=STATE_KEY)
        self.route_key=None;self.enabled=self.cfg.get('body_residency_mb',0)>0
        self.sync()
    def sync(self):
        """Mirror installed models into AG0 slots and AG13 experts. Never overwrites a slot mid-swap."""
        from .models import ROLES,model_key
        from . import body_sizes
        st=self.slots.box.load()[0]['slots']
        for role in ROLES:
            e=self.models.installed.get(model_key(role,self.models.b2_control))
            if not e or not e.get('download_complete'):continue
            if role not in st:self.slots.install(role,ModelSlots.from_installed(e))
        def f(s):
            s['budget_mb']=float(max(1,self.cfg.get('body_residency_mb',0)))
            for role in ROLES:
                mb,src=body_sizes.size(self.models,role,self.r.store)
                if mb is None:continue
                old=s['experts'].get(role,{})
                s['experts'][role]={'size_mb':mb,'size_source':src,'body':role,'pinned':role in PINNED,'shared':role in PINNED,'score':old.get('score',0.),'last':old.get('last',0.)}
            s['resident']=[x for x in s['resident'] if x in PINNED and x in s['experts']]  # processes never survive a restart
            for x in PINNED:
                if x in s['experts'] and x not in s['resident']:s['resident'].append(x)
        self.residency.box.mutate(f)
    # -- AG0 routing -------------------------------------------------------------------------------
    def _installed_revision(self,role):
        from .models import model_key
        return (self.models.installed.get(model_key(role,self.models.b2_control)) or {}).get('exact_revision')
    def _committed(self,role,sl):
        """WP-T13: a finished swap (slot ACTIVE on a file other than the installed one) serves every turn."""
        a=sl.get('active') if sl else None
        if not a or not a.get('path') or a.get('revision')==self._installed_revision(role):return None
        p=Path(a['path']);p=p if p.is_absolute() else self.models.home/p
        return p if p.is_file() else None
    def revision_override(self,role):
        """ModelManager.revision after a committed swap (otherwise None = installed revision)."""
        sl=self.slots.box.load()[0]['slots'].get(role)
        return sl['active']['revision'] if self._committed(role,sl) else None
    def path_override(self,role):
        """Called by ModelManager.path_for. Returns the RAMP candidate's file for its share of turns, the swapped-in
        file after a committed swap (WP-T13), else None."""
        sl=self.slots.box.load()[0]['slots'].get(role)
        done=self._committed(role,sl) if sl and sl['stage']!='RAMP' else None
        if done:return done
        if self.route_key is None:return None
        if not sl or sl['stage']!='RAMP' or not sl.get('candidate'):return None
        rev=self.slots.route(role,str(self.route_key)+':'+role)
        if rev!=sl['candidate']['revision'] or not sl['candidate'].get('path'):return None
        p=Path(sl['candidate']['path']);p=p if p.is_absolute() else self.models.home/p
        return p if p.is_file() else None
    def begin_turn(self,key):self.route_key=key
    # -- AG13 residency ----------------------------------------------------------------------------
    def admit(self,role,resident):
        """Decide before a runner for ``role`` is (re)used. Returns roles to unload first.
        resident: roles whose processes are alive right now (the pool's truth wins over stored state)."""
        if not self.enabled:return [r for r in resident if r!=role]
        mode=mode_of(getattr(self.r,'guard',None))
        def f(st):
            st['resident']=[x for x in st['resident'] if x in resident or x in PINNED]
            for x in resident:
                if x not in st['resident'] and x in st['experts']:st['resident'].append(x)
        self.residency.box.mutate(f)
        evict=list(self.residency.set_mode(mode))
        if role not in self.residency.box.load()[0]['experts']:return [r for r in resident if r!=role]
        d=self.residency.request(role);evict+=d['evict']
        if d['status']=='REFUSED':evict=[r for r in resident if r!=role]  # dense fallback: one process at a time
        if mode=='RED':evict=[r for r in resident if r!=role]           # critical: never hold two bodies
        elif mode=='ORANGE':evict+=[r for r in resident if r in BODY_ROLES and r!=role]  # §97.2: single-body observer
        return sorted(set(r for r in evict if r in resident and r!=role))
    def released(self,role):
        def f(st):
            if role in st['resident'] and role not in PINNED:st['resident'].remove(role)
        self.residency.box.mutate(f)
    def report(self):
        res=self.residency.report()
        return {'distinct_bodies':distinct_bodies(self.models),'b2_control':self.models.b2_control,'enabled':self.enabled,
                'bodies':{r:{'model':self.models.installed.get(k,{}).get('model_id'),'revision':self.models.revision(r)[:12]} for r,k in (('B1_DETAIL','body'),('B2_GIST','gist' if self.models.b2_control=='two_body' else 'body'))},
                'slots':self.slots.report()['slots'],'residency':res,'live_processes':sorted(self.r.pool.resident_roles()) if hasattr(self.r.pool,'resident_roles') else None}

def attach(runtime):
    fabric=BodyFabric(runtime);runtime.bodies=fabric
    from .bodyport import Ports
    fabric.ports=Ports(runtime)  # WP-T13 IH-H8 lifecycle + IH-H21 live bridge-key check
    runtime.models.router=fabric.path_override;runtime.models.revision_router=fabric.revision_override;runtime.pool.fabric=fabric
    return fabric
