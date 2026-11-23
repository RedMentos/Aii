"""WP-T11 §16.2 / §15.7 homeostasis measurement with a gate (Sleep C).

Each Sleep C snapshots the learned control parameters of every head that has them and compares them with the
previous snapshot:
  drift       relative L2 change per component, ||θ_now - θ_prev|| / max(||θ_prev||, DRIFT_FLOOR)
  saturation  share of bounded parameters sitting on a bound (attention gains, replay gains, C5 modulators)
  dead        share of slow neuromod paths without any activation since the previous snapshot
Gate (BOOT values): PASS when every component's drift <= MAX_DRIFT and saturation <= MAX_SATURATION; otherwise
FAIL naming the components. A FAIL holds slow consolidation (authority.learn_slow) until a later Sleep C passes.
Homeostasis does not force equal use (specialisation stays allowed, §16.2). No native body weights are read: A/B/C
base weights are not trainable here, so their drift is reported as UNAVAILABLE, not 0.

WP-U2 regulation (§16.2 "darf langsam ...", §68 HOME.* BOOT knobs) per N10 learning path, between two Sleep C:
  activation frequency  LearningTrace activations since the previous snapshot (share of all paths)
  update frequency      PlasticityState packets (measured shadow updates) per path since the previous Sleep C
  dominant path         share above fair + (1-fair) x HOME.dominant_path_inhibition -> target gain < 1
  dead useful path      no activation, but tagged/stable/confirmed before -> target 1 + HOME.dead_path_reopen
  update budget         more updates than the mean -> target x (mean/updates)^HOME.update_budget_normalization
The path gain moves HOME.activation_balance of the way to its target per night, bounded to [GAIN_MIN, GAIN_MAX].
It scales the N10 plasticity gate factor only in ACTIVE (`:homeostasis active`, explicit human); SHADOW records the
proposal. Route dominance (C5 route share >= HOME.router_collision_monitor) is monitored, never corrected.
"""
import json
import math
from .common import now

KEY='T11_HOMEOSTASIS';REVISION='t11-homeostasis-v1'
MAX_DRIFT=.5        # BOOT: relative L2 change per night
MAX_SATURATION=.5   # BOOT: share of bounded parameters on a bound
DRIFT_FLOOR=.05     # BOOT: denominators below this are treated as this (fresh, near-zero heads)
EPS=1e-6
HISTORY=16
HOME={'activation_balance':.30,'dead_path_reopen':.30,'dominant_path_inhibition':.40,
      'router_collision_monitor':.70,'update_budget_normalization':.60}  # §68 BOOT values, not measured (HOME.shared_representation_drift has no shared trainable representation here)
GAIN_MIN=.5;GAIN_MAX=1.5   # BOOT: same bounds as the replay-type gains (sleep._homeostasis)
MIN_PATHS=3                # BOOT: below this many active paths there is no "dominant" path
MIN_ROUTES=8               # BOOT: route samples before route dominance is reported

def _try(fn):
    try:return fn()
    except Exception:return None

def snapshot(r,replay_gains=None):
    """{component: {'theta':{name:value}, 'bounds':{name:(lo,hi)}}} for every head that has learned parameters."""
    out={}
    def ctl(mod):
        import importlib
        return importlib.import_module('.'+mod,__package__).controller(r)._load()[0]
    att=_try(lambda:ctl('attention'))
    if att:
        from .attention import GAIN_MIN,GAIN_MAX
        out['attention_gains']={'theta':dict(att['gains']),'bounds':{k:(GAIN_MIN,GAIN_MAX) for k in att['gains']}}
    jef=_try(lambda:ctl('jefbridge'))
    if jef:out['jef_bridge']={'theta':{str(i):w for i,w in enumerate(jef['w'])},'bounds':{}}
    ff=_try(lambda:ctl('fastforward'))
    if ff:out['fast_forward']={'theta':{t+':'+str(i):w for t,ws in ff['w'].items() for i,w in enumerate(ws)},'bounds':{}}
    c5=_try(lambda:ctl('actionlearn'))
    if c5:out['c5_action']={'theta':{a+':'+k:v for a,q in c5['q'].items() for k,v in q['mods'].items()},'bounds':{a+':'+k:(0.,1.) for a,q in c5['q'].items() for k in q['mods']}}
    dl=_try(lambda:ctl('deliberation'))
    if dl:out['deliberation']={'theta':{k:q['v'] for k,q in dl['modes'].items()},'bounds':{}}
    from .neuromod import controller as _nmc
    _try(lambda:_nmc(r).sync())  # fold pending LearningTrace/ModulatorPacket rows in before reading activations
    nm=_try(lambda:ctl('neuromod'))
    if nm:
        th={'slow:'+k:p['slow'] for k,p in nm['paths'].items()}
        h=nm.get('meta_head')
        if h:th.update({'meta:'+str(i):w for i,w in enumerate(h['w'])}|{'meta:b':h['b']})
        out['neuromod']={'theta':th,'bounds':{},'activations':{k:p['activations'] for k,p in nm['paths'].items()},
                         'useful':sorted(k for k,p in nm['paths'].items() if p.get('tag') or p.get('stable') or p.get('confirmations'))}
    if replay_gains:
        from .sleep import BASE_GAIN
        out['replay_gains']={'theta':dict(replay_gains),'bounds':{t:(.5*BASE_GAIN[t],1.5*BASE_GAIN[t]) for t in replay_gains if t in BASE_GAIN}}
    return out

def _norm(v):return math.sqrt(sum(x*x for x in v))

def measure(prev,cur):
    comps={}
    for name,c in cur.items():
        th=c['theta'];p=(prev or {}).get(name)
        bounded=[k for k in th if k in c['bounds']]
        sat=sum(1 for k in bounded if min(abs(th[k]-c['bounds'][k][0]),abs(th[k]-c['bounds'][k][1]))<=EPS)/len(bounded) if bounded else None
        row={'parameters':len(th),'saturation':round(sat,4) if sat is not None else None}
        if p:
            keys=sorted(set(th)|set(p['theta']))
            diff=[th.get(k,0.)-p['theta'].get(k,0.) for k in keys];base=_norm([p['theta'].get(k,0.) for k in keys])
            row['drift']=round(_norm(diff)/max(base,DRIFT_FLOOR),4)
            if 'activations' in c:
                pa=p.get('activations') or {};paths=c['activations']
                row['dead']=round(sum(1 for k,v in paths.items() if v==pa.get(k,0))/len(paths),4) if paths else None
        else:row['drift']=None
        comps[name]=row
    return comps

def gate(comps):
    fails=[]
    for name,row in comps.items():
        if row.get('drift') is not None and row['drift']>MAX_DRIFT:fails.append(name+':drift')
        if row.get('saturation') is not None and row['saturation']>MAX_SATURATION:fails.append(name+':saturation')
    return {'status':'FAIL' if fails else 'PASS','failures':fails,'max_drift':MAX_DRIFT,'max_saturation':MAX_SATURATION}

def _counts(store,kind,field,cursor):
    from .neuromod import path_of
    out={};top=cursor
    for row in store.rows("SELECT rowid AS rid,payload FROM packets WHERE kind=? AND rowid>?",(kind,cursor)):
        top=max(top,row['rid']);v=json.loads(row['payload']).get(field)
        if isinstance(v,str):k=path_of(v) if kind!='ActionSelection' else v;out[k]=out.get(k,0)+1
    return out,top

def regulate(prev,cur,gains,updates,routes):
    """One night of §16.2 regulation. prev/cur: neuromod snapshot parts; gains: current path gains. Pure function."""
    acts_now=cur.get('activations') or {};acts_prev=(prev or {}).get('activations') or {}
    acts={k:max(0,v-acts_prev.get(k,0)) for k,v in acts_now.items()}
    total=sum(acts.values());active=[k for k,v in acts.items() if v>0];n=len(active)
    fair=1/n if n else 1.;thr=fair+(1-fair)*HOME['dominant_path_inhibition']
    up=[updates.get(k,0) for k in acts];mean_u=sum(up)/len(up) if up else 0.
    rows={}
    for k,a in acts.items():
        share=a/total if total else 0.;target=1.;why=[]
        if prev is not None and n>=MIN_PATHS and share>thr:
            target-=HOME['dominant_path_inhibition']*(share-thr)/max(1-thr,EPS);why.append('DOMINANT')
        if prev is not None and a==0 and k in (cur.get('useful') or []):target=1+HOME['dead_path_reopen'];why.append('DEAD_USEFUL_REOPEN')
        u=updates.get(k,0)
        if mean_u>0 and u>mean_u:target*=(mean_u/u)**HOME['update_budget_normalization'];why.append('UPDATE_BUDGET')
        g=gains.get(k,1.);new=round(min(GAIN_MAX,max(GAIN_MIN,g+HOME['activation_balance']*(target-g))),6)
        rows[k]={'activations':a,'share':round(share,4),'updates':u,'target':round(target,4),'gain':new,'reasons':why}
    rn=sum(routes.values());top=max(routes,key=routes.get) if routes else None
    route={'counts':routes,'n':rn,'dominant':top if rn>=MIN_ROUTES and routes[top]/rn>=HOME['router_collision_monitor'] else None,
           'action':'MONITOR_ONLY'}
    return {'paths':rows,'dominant_threshold':round(thr,4),'routes':route}

def run(r,replay_gains=None):
    """Sleep C hook: snapshot, compare with the previous Sleep C, gate, regulate, persist. Returns the report row."""
    st,v=r.store.state(KEY,None);st=st or {'revision':REVISION,'last':None,'history':[]}
    prev_snap=(st.get('last') or {}).get('snapshot')
    cur=snapshot(r,replay_gains);comps=measure(prev_snap,cur);g=gate(comps)
    cursor=st.get('cursor',0);updates,c1=_counts(r.store,'PlasticityState','component',cursor);routes,c2=_counts(r.store,'ActionSelection','route_hint',cursor)
    reg=regulate((prev_snap or {}).get('neuromod') if prev_snap else None,cur.get('neuromod') or {},st.get('path_gains') or {},updates,routes)
    st['path_gains']={k:x['gain'] for k,x in reg['paths'].items()}|{k:v for k,v in (st.get('path_gains') or {}).items() if k not in reg['paths']}
    st['cursor']=max(cursor,c1,c2);st.setdefault('mode','SHADOW')
    reg['mode']=st['mode']
    rep={'at':now(),'components':comps,'gate':g,'regulation':reg,'native_body_weights':'UNAVAILABLE'}
    st['last']={'snapshot':cur,'at':rep['at'],'gate':g,'regulation':reg};st['history']=(st['history']+[{'at':rep['at'],'gate':g['status'],'failures':g['failures']}])[-HISTORY:]
    r.store.set_state(KEY,st,expected=v)
    r.store.log('homeostasis_gate',None,{'status':g['status'],'failures':g['failures'][:8]})
    return rep

def path_gain(store,path):
    """(gain, mode) for one N10 path; gain 1.0 when homeostasis never ran or the path is unknown."""
    st=store.state(KEY,None)[0] or {}
    return float((st.get('path_gains') or {}).get(path,1.)),st.get('mode','SHADOW')

def set_mode(store,mode,authority='SYSTEM'):
    if mode not in {'SHADOW','ACTIVE'}:raise ValueError('SHADOW|ACTIVE')
    if mode=='ACTIVE' and authority!='EXPLICIT_HUMAN':raise PermissionError('ACTIVE nur per expliziter Nutzerfreigabe (Age 0)')
    st,v=store.state(KEY,None);st=st or {'revision':REVISION,'last':None,'history':[]};st['mode']=mode
    store.set_state(KEY,st,expected=v);store.log('homeostasis_mode',None,{'mode':mode,'authority':authority});return mode

def holding(store):
    """True while the last homeostasis gate failed (slow consolidation waits)."""
    st=store.state(KEY,None)[0]
    return bool(st and st.get('last') and st['last']['gate']['status']=='FAIL')

def report(store):
    st=store.state(KEY,None)[0] or {}
    last=st.get('last') or {}
    return {'revision':REVISION,'last_gate':last.get('gate'),'at':last.get('at'),'history':st.get('history',[]),
            'mode':st.get('mode','SHADOW'),'path_gains':st.get('path_gains',{}),'last_regulation':last.get('regulation'),
            'claim_limit':'Control-head parameters only; native A/B/C weights are not trainable here (UNAVAILABLE)'}

def operator_command(r,args):
    """:homeostasis [status|run|shadow|active]"""
    from .common import dumps
    if not args or args==['status']:return dumps(report(r.store))
    if args==['run']:return dumps(run(r))
    if args==['shadow']:return dumps({'mode':set_mode(r.store,'SHADOW')})
    if args==['active']:return dumps({'mode':set_mode(r.store,'ACTIVE','EXPLICIT_HUMAN')})
    raise ValueError(':homeostasis [status|run|shadow|active]')
