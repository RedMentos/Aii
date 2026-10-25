"""Redmi resource modes GREEN / YELLOW / ORANGE / RED (Canon §97.2, §97.1, §22.2.4).

One place decides the resource mode and what each mode permits; runtime, effort, bodies,
late watch, sleep, scheduler and the shadow learners read it from here instead of keeping
their own (formerly contradictory) PRESSURE->YELLOW / PRESSURE->RED tables.

  GREEN   normal observer coverage
  YELLOW  reduce observer depth / context / replay
  ORANGE  single-body observer + JEF, pause shadow learning (no replay, Sleep C only)
  RED     JEF safe path only, no replay / no learning;
          response governor, rules, provenance and cancel are preserved

Thresholds (§97.2: "measured on device, not hardcoded from desktop numbers"):
- BOOT profile: derived from the existing knobs ``minimum_free_mb`` / ``thermal_limit_c`` so that
  RED and ORANGE reproduce the old CRITICAL / PRESSURE boundaries exactly; YELLOW is new
  (3x floor, limit-6 C). Status ``UNCALIBRATED`` -- these are not measurements.
- ``calibrate``: memory thresholds from measured RSS of the observer bodies on this device
  (ORANGE = floor + one body, YELLOW = floor + both bodies, each with a safety margin).
  Status ``DEVICE_MEASURED`` only on Android/Termux; elsewhere ``HOST_MEASURED_NOT_REDMI``
  (usable for tests, never a Redmi claim). Thermal thresholds stay BOOT until a device
  throttle measurement exists.

The legacy guard states (NORMAL/RECOVERY/PRESSURE/CRITICAL) stay the wire format for older
call sites: GREEN/YELLOW -> NORMAL (RECOVERY right after ORANGE/RED), ORANGE -> PRESSURE,
RED -> CRITICAL. A CRITICAL turn is still refused after the OOM/heat reflex (hard floor: a C3
forward below the floor risks the OOM it is meant to avoid); governor snapshot, rules,
provenance log and cancel are untouched by every mode.
"""
import math
import time

MODES=('GREEN','YELLOW','ORANGE','RED')
RANK={m:i for i,m in enumerate(MODES)}
LEGACY_MODE={'NORMAL':'GREEN','RECOVERY':'YELLOW','UNKNOWN':'YELLOW','PRESSURE':'ORANGE','CRITICAL':'RED'}
MODE_LEGACY={'GREEN':'NORMAL','YELLOW':'NORMAL','ORANGE':'PRESSURE','RED':'CRITICAL'}
PRESERVED=('response_governor','rules','provenance','cancel')
# BOOT policy values (structure from §97.2; numbers are not Redmi measurements).
POLICY={
    'GREEN': {'max_observer_bodies':2,'background_observers':2,'observer_depth':1.,'focal_cycles_max':None,'context_scale':1.,
              'replay_scale':1.,'replay':True,'dream':True,'shadow_learning':True,'learned_wake':True,'focal_pressure':0.},
    'YELLOW':{'max_observer_bodies':2,'background_observers':1,'observer_depth':.6,'focal_cycles_max':2,'context_scale':.5,
              'replay_scale':.5,'replay':True,'dream':True,'shadow_learning':True,'learned_wake':True,'focal_pressure':.5},
    'ORANGE':{'max_observer_bodies':1,'background_observers':0,'observer_depth':.5,'focal_cycles_max':1,'context_scale':.5,
              'replay_scale':0.,'replay':False,'dream':False,'shadow_learning':False,'learned_wake':False,'focal_pressure':1.},
    'RED':   {'max_observer_bodies':0,'background_observers':0,'observer_depth':0.,'focal_cycles_max':0,'context_scale':.25,
              'replay_scale':0.,'replay':False,'dream':False,'shadow_learning':False,'learned_wake':False,'focal_pressure':1.},
}
STATE_KEY='RESOURCE_MODE_PROFILE'
REVISION='resource-modes-v1'
CALIBRATION_MARGIN=1.15   # BOOT safety factor on measured body RSS
MEM_HYSTERESIS=.05        # BOOT: leave a stricter mode only after clearing its threshold by 5 %
TEMP_HYSTERESIS_C=1.      # BOOT
RSS_BOOT_MB={'YELLOW':3000.,'ORANGE':3800.}  # §73 total_RSS_soft_budget (lower bound) / total_RSS_hard_backoff

def as_mode(x):
    """Mode name from a mode or a legacy guard state (unknown -> YELLOW, conservative)."""
    if x in RANK:return x
    return LEGACY_MODE.get(x,'YELLOW')
def mode_of(guard):
    """Mode of a guard-like object; tolerates objects that only carry a legacy ``state``."""
    if guard is None:return 'GREEN'
    m=getattr(guard,'mode',None)
    return m if m in RANK else as_mode(getattr(guard,'state','NORMAL'))
def policy(mode):return dict(POLICY[as_mode(mode)],mode=as_mode(mode),preserved=list(PRESERVED))
def allows(state_or_mode,what):
    """``what`` is a boolean POLICY key (replay, dream, shadow_learning, learned_wake)."""
    return bool(POLICY[as_mode(state_or_mode)][what])
def scaled(n,state_or_mode,key,floor=1):
    """Scale a positive integer budget by a policy factor (half up, at least ``floor``); 0 when the factor is 0; 0/None pass through."""
    f=POLICY[as_mode(state_or_mode)][key]
    if n is None or n<=0:return n
    if f<=0:return 0
    return max(floor,int(n*f+.5))
def cap_roles(roles,state_or_mode,key='max_observer_bodies'):return list(roles)[:POLICY[as_mode(state_or_mode)][key]]

def boot_profile(cfg,device_info=None):
    floor=float(cfg['minimum_free_mb']);limit=float(cfg['thermal_limit_c'])
    if device_info is None:
        from .resources import device
        device_info=device()
    android=bool(device_info.get('android'))
    return {'revision':REVISION,'status':'UNCALIBRATED','source':'BOOT minimum_free_mb/thermal_limit_c',
            'mem_mb':{'RED':floor,'ORANGE':2*floor,'YELLOW':3*floor},'temp_c':{'RED':limit,'ORANGE':limit-3,'YELLOW':limit-6},
            # §73 Redmi lab targets (total_RSS_soft_budget 3.0-3.4 GB -> lower bound, hard_backoff 3.8 GB); not an OS guarantee.
            # Off on other hosts: desktop cloud runs of big bodies must not be throttled by phone targets.
            'rss_mb':dict(RSS_BOOT_MB) if android else None,'rss_status':'BOOT_REDMI_TARGET' if android else 'OFF_NOT_ANDROID',
            'thermal_status':'BOOT_UNMEASURED','hysteresis':{'mem_fraction':MEM_HYSTERESIS,'temp_c':TEMP_HYSTERESIS_C}}

def _finite_number(value, minimum=None):
    """Only real, finite telemetry numbers; bool is not a measurement."""
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value) and (minimum is None or value >= minimum)
    except (OverflowError, ValueError, TypeError):
        return False


def validate(p):
    """Reject corrupted persisted thresholds rather than silently disabling backoff."""
    if not isinstance(p, dict):
        raise ValueError('resource profile must be a mapping')
    for key in ('mem_mb', 'temp_c'):
        values = p.get(key)
        if not isinstance(values, dict) or any(
            not _finite_number(values.get(m), 0 if key == 'mem_mb' else None)
            for m in ('RED', 'ORANGE', 'YELLOW')
        ):
            raise ValueError('resource profile ' + key + ' must be finite')
    if not p['mem_mb']['RED'] <= p['mem_mb']['ORANGE'] <= p['mem_mb']['YELLOW']:
        raise ValueError('mem thresholds must rise RED<=ORANGE<=YELLOW')
    if not p['temp_c']['RED'] >= p['temp_c']['ORANGE'] >= p['temp_c']['YELLOW']:
        raise ValueError('temp thresholds must fall RED>=ORANGE>=YELLOW')
    r = p.get('rss_mb')
    if r is not None:
        if not isinstance(r, dict) or any(not _finite_number(r.get(m), 0) or r[m] == 0 for m in ('YELLOW', 'ORANGE')):
            raise ValueError('rss budget must be finite positive')
        if r['YELLOW'] > r['ORANGE']:
            raise ValueError('rss budget must rise 0<YELLOW<=ORANGE')
    h = p.get('hysteresis')
    if not isinstance(h, dict) or not _finite_number(h.get('mem_fraction'), 0) or not _finite_number(h.get('temp_c'), 0):
        raise ValueError('resource hysteresis must be finite nonnegative')
    if h['mem_fraction'] >= 1:
        raise ValueError('resource memory hysteresis must be below 1')
    return p

def calibrate(cfg,body_rss_mb,device_info,clock=time.time,thermal=None):
    """Device-measured memory thresholds from observer-body RSS (MB per role, both bodies required).

    ORANGE = floor + largest body (room to (re)load one observer), YELLOW = floor + both bodies
    (room for full coverage); RED stays the user's floor. ``thermal`` may carry measured
    {'RED','ORANGE','YELLOW'} temperatures; otherwise the BOOT thermal thresholds remain.
    """
    need={'B1_DETAIL','B2_GIST'}
    rss={k:float(v) for k,v in (body_rss_mb or {}).items() if k in need and v is not None and float(v)>0}
    if set(rss)!=need:raise ValueError('Kalibrierung braucht gemessene RSS beider Beobachter-Körper (B1_DETAIL, B2_GIST); fehlt: '+','.join(sorted(need-set(rss))))
    p=boot_profile(cfg,device_info);floor=p['mem_mb']['RED']
    p['mem_mb']={'RED':floor,'ORANGE':round(floor+max(rss.values())*CALIBRATION_MARGIN,1),'YELLOW':round(floor+sum(rss.values())*CALIBRATION_MARGIN,1)}
    if thermal:
        p['temp_c']={m:float(thermal[m]) for m in ('RED','ORANGE','YELLOW')};p['thermal_status']='DEVICE_MEASURED' if device_info.get('android') else 'HOST_MEASURED_NOT_REDMI'
    p.update(status='DEVICE_MEASURED' if device_info.get('android') else 'HOST_MEASURED_NOT_REDMI',
             source='measured observer-body RSS',measured={'body_rss_mb':rss,'margin':CALIBRATION_MARGIN,'device':device_info,'at':clock()})
    return validate(p)

def measure_bodies(runtime):
    """RSS (MB) of resident observer-body processes right now; roles without a live process are absent."""
    from .resources import process_memory
    out={}
    pool=getattr(runtime,'pool',None)
    for key,runner in list(getattr(pool,'resident',{}).items()):
        role=key[0] if isinstance(key,tuple) else key
        if role not in ('B1_DETAIL','B2_GIST'):continue
        for pid in runner.pids():
            m=process_memory(pid)
            if m.get('rss_bytes'):out[role]=max(out.get(role,0.),m['rss_bytes']/1048576)
    return {k:round(v,1) for k,v in out.items()}

def _invalid_process_memory(snapshot):
    """Present invalid RSS/PSS is distinct from missing/unavailable metrics."""
    processes = snapshot.get('processes')
    if processes is None:
        return False
    if not isinstance(processes, (list, tuple)):
        return True
    for process in processes:
        if not isinstance(process, dict):
            return True
        for key in ('pss_bytes', 'rss_bytes'):
            value = process.get(key)
            if value is not None and not _finite_number(value, 0):
                return True
    return False


def total_rss_mb(snapshot):
    """Own measured PSS, else RSS; invalid/missing measurements never count as zero."""
    if not isinstance(snapshot, dict) or _invalid_process_memory(snapshot):
        return None
    vals = []
    for process in snapshot.get('processes') or ():
        pss = process.get('pss_bytes')
        rss = process.get('rss_bytes')
        value = pss if pss else rss
        if value:
            vals.append(value)
    if not vals:
        return None
    total = sum(vals)
    return total / 1048576 if _finite_number(total, 0) else None


def classify(snapshot, profile, previous='GREEN'):
    """(mode, reasons) with finite telemetry checks before any safe-mode comparisons.

    Present invalid readings fail closed as RED; absent readings retain the
    existing unmeasured semantics. No missing sensor is fabricated as safe.
    """
    try:
        validate(profile)
    except (KeyError, TypeError, ValueError):
        return 'RED', ['INVALID_RESOURCE_PROFILE']
    if not isinstance(snapshot, dict):
        return 'RED', ['INVALID_RESOURCE_SNAPSHOT']
    mem = snapshot.get('mem_available_bytes')
    temp = snapshot.get('battery_temperature_c')
    invalid = []
    if mem is not None and not _finite_number(mem, 0):
        invalid.append('INVALID_MEM_AVAILABLE')
    if temp is not None and not _finite_number(temp):
        invalid.append('INVALID_BATTERY_TEMPERATURE')
    if profile.get('rss_mb') is not None and _invalid_process_memory(snapshot):
        invalid.append('INVALID_PROCESS_MEMORY')
    if invalid:
        return 'RED', invalid
    mem = None if mem is None else mem / 1048576
    rss = total_rss_mb(snapshot) if profile.get('rss_mb') else None
    hm = profile['hysteresis']['mem_fraction']
    ht = profile['hysteresis']['temp_c']
    prev = RANK.get(previous, 0)
    def hit(m):
        reasons = []
        held = RANK[m] <= prev
        lim = profile['mem_mb'][m] * (1 + hm if held else 1.)
        if mem is not None and mem < lim:
            reasons.append('MEM_BELOW_' + m)
        tl = profile['temp_c'][m] - (ht if held else 0.)
        if temp is not None and temp >= tl:
            reasons.append('TEMP_AT_' + m)
        if rss is not None and m in profile['rss_mb'] and rss > profile['rss_mb'][m] * (1 - hm if held else 1.):
            reasons.append('RSS_OVER_' + m)
        return reasons
    for mode in ('RED', 'ORANGE', 'YELLOW'):
        reasons = hit(mode)
        if reasons:
            return mode, reasons
    return 'GREEN', []

def load_profile(store,cfg):
    p,_=store.state(STATE_KEY,None)
    if not p:return boot_profile(cfg)
    try:return validate(p)
    except (KeyError,TypeError,ValueError):return boot_profile(cfg)

def report(runtime):
    g=runtime.guard;m=mode_of(g)
    return {'mode':m,'legacy_state':g.state,'reasons':list(getattr(g,'reasons',[])),'policy':policy(m),
            'profile':getattr(g,'profile',None),'canon':'§97.2','claim_limit':'thresholds are BOOT unless status DEVICE_MEASURED; policy factors are BOOT'}

def bodies_report(runtime):
    """WP-N21: residency size per role (measured profile or estimate) and which combinations fit the budget."""
    from . import body_sizes
    rows={};sizes={}
    for role in ('C3_LANGUAGE','B1_DETAIL','B2_GIST'):
        mb,src=body_sizes.size(runtime.models,role,runtime.store)
        rows[role]={'size_mb':mb,'source':src};sizes[role]=mb
    budget=runtime.cfg.get('body_residency_mb',0)
    return {'bodies':rows,'fits':body_sizes.fits(sizes,budget) if budget else None,'residency_enabled':budget>0,
            'size_rule':'Anon after work + %g MiB hot file pages (cgroup squeeze); ESTIMATE = file x 1.1 + 96'%body_sizes.HOT_FILE_MB}

def command(runtime,args):
    """:resources modes | calibrate | reset | bodies [import <ram_budget.json>|reset]"""
    sub=args[0] if args else 'modes'
    if sub=='bodies':
        from . import body_sizes
        if args[1:2]==['import'] and len(args)==3:
            from pathlib import Path
            import json
            path=Path(args[2]);path=path if path.is_absolute() else runtime.home/path
            entries=body_sizes.import_report(runtime.store,json.loads(path.read_text()))
            runtime.store.log('body_sizes',None,{'items':len(entries)})
        elif args[1:]==['reset']:body_sizes.reset(runtime.store)
        elif args[1:]:raise ValueError(':resources bodies [import <ram_budget.json>|reset]')
        if args[1:] and getattr(runtime,'bodies',None) is not None:runtime.bodies.sync()
        return bodies_report(runtime)
    if sub=='modes':return report(runtime)
    if sub=='calibrate':
        from .resources import device
        p=calibrate(runtime.cfg,measure_bodies(runtime),device())
        runtime.store.set_state(STATE_KEY,p);runtime.guard.profile=p
        runtime.store.log('resource_profile',None,{'status':p['status'],'orange_mb':p['mem_mb']['ORANGE'],'yellow_mb':p['mem_mb']['YELLOW']})
        return report(runtime)
    if sub=='reset':
        runtime.store.set_state(STATE_KEY,None);runtime.guard.profile=boot_profile(runtime.cfg)
        runtime.store.log('resource_profile',None,{'status':'UNCALIBRATED'})
        return report(runtime)
    raise ValueError(':resources [modes|calibrate|reset|bodies [import <json>|reset]]')
