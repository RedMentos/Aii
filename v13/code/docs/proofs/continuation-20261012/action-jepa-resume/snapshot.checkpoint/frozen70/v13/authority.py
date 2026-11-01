"""WP-T10 learning authority and shadow -> active promotion (§88.1, §17A, §14.1-14.6, IH-H25).

One promotion path for every learned head that today has its own SHADOW/ACTIVE switch:

  level 0 SHADOW     learned head runs beside the scaffold, logged, no effect (default, Age 0)
  level 1 CANDIDATE  its own shadow gate passed, its learning objective is IMPLEMENTED and its gate-graph node
                     has no failing measured verdict; the scaffold still acts (§88.1 Age 0: "L3 SHADOW -> approved")
  level 2 ACTIVE     only by an explicit human promotion of a CANDIDATE; the scaffold becomes the fallback (§17A)

review() re-checks every head (scheduled as the medium learning timescale, §14.3): a passing head becomes a
CANDIDATE, a CANDIDATE whose evidence lapsed falls back to 0, and an ACTIVE head with measured regression is
demoted to SHADOW automatically (the safe direction needs no human). Promotion to ACTIVE is never automatic:
Age 0 has no right to it (`safe_self_edit_without_dialog` is Age 3 and BUILD_CEILING is 0).

Evidence is what each head already measures (agreement with the scaffold, a held-out check, a procedure gate).
Heads without any shadow comparison report NO_COMPARISON and stay at 0; observe() is the generic ledger for
hooks that can report scaffold vs learned decisions and outcomes.
"""
from .common import now
from . import objectives as OBJ

KEY='T10_AUTHORITY';REVISION='t10-authority-v1'
LEVELS=('SHADOW','CANDIDATE','ACTIVE')
MIN_N=20          # BOOT: shadow decisions before a head may become a candidate
AGREE_MIN=.9      # BOOT: §17A first phase — the learned head reproduces the scaffold's decisions
REGRESS_MARGIN=.05  # BOOT: learned failure rate above scaffold failure rate that counts as regression
GATE_OK={'GREEN','PARTIAL','BLOCKED_BY_DEP'}  # a gate-graph node that is incomplete but has no failing measured verdict
HISTORY=32

def _st(c):return c._load()[0]
def _ctl(mod,r):
    import importlib
    return importlib.import_module('.'+mod,__package__).controller(r)

def _agree(n,same):return {'n':int(n),'agreement':round(same/n,4) if n else None}

def _ev_c5(r):
    a=_st(_ctl('actionlearn',r))['agree'];return _agree(a['n'],a['same'])
def _ev_jef(r):
    a=_st(_ctl('jefbridge',r))['scaffold_agree'];return _agree(a['n'],a['agree'])
def _ev_ff(r):
    st=_st(_ctl('fastforward',r));ready=[k for k,p in st['procs'].items() if p.get('stage')=='READY']
    return {'n':int(st['n']),'passed':bool(ready) or None,'detail':{'ready_procedures':ready[:8]}}
def _ev_ctx(r):
    c=_ctl('context_os',r);st=_st(c);rec=st['recall'][-64:]
    return {'n':len(rec),'passed':c._recall_stable(st) or None,'detail':{'exact_span_recall':round(sum(rec)/len(rec),4) if rec else None}}
def _ev_adm(r):
    from .admission import Admission
    chk=Admission(r.store,r.cfg).state().get('check') or {}
    s=chk.get('status');return {'n':int(chk.get('labels') or 0),'passed':True if s=='PASS' else None,'regression':s=='FAIL','detail':{'check':s}}
def _ev_none(r):return {'n':0}

def _mode_attr(mod,attr='mode'):
    return lambda r:_st(_ctl(mod,r)).get(attr) or 'SHADOW'
def _set_mode(mod,**kw):
    return lambda r,mode,auth:_ctl(mod,r).set_mode(mode,auth,**kw)
def _adm_get(r):
    from .admission import Admission
    return Admission(r.store,r.cfg).state()['authority']
def _adm_set(r,mode,auth):
    from .admission import Admission
    return Admission(r.store,r.cfg).set_authority(mode,'USER' if auth=='EXPLICIT_HUMAN' else 'SYSTEM')
def _gist_get(r):
    from .gist import Gist
    return Gist(r.store).mode()
def _gist_set(r,mode,auth):
    from .gist import Gist
    return Gist(r.store).set_mode(mode,auth)

# head -> mode getter/setter, evidence, IH-H25 objective, gate-graph node, Age capability
HEADS={
 'c5_action':dict(get=_mode_attr('actionlearn'),set=_set_mode('actionlearn'),evidence=_ev_c5,objective='c5-action-values-v1',gate='STEP5',capability='routing_skill'),
 'jef_bridge':dict(get=_mode_attr('jefbridge'),set=_set_mode('jefbridge'),evidence=_ev_jef,objective='jef-bridge-utility-v1',gate='STEP1',capability='routing_skill'),
 'fast_forward':dict(get=_mode_attr('fastforward'),set=_set_mode('fastforward'),evidence=_ev_ff,objective='fast-forward-proceduralization-v1',gate='G-PROCEDURALIZATION-004',capability='routing_skill'),
 'context_policy':dict(get=_mode_attr('context_os','learned'),set=_set_mode('context_os',which='learned'),evidence=_ev_ctx,objective='context-policy-recall-v1',gate='STEP3',capability='memory_skill'),
 'admission':dict(get=_adm_get,set=_adm_set,evidence=_ev_adm,objective='memory-admission-heldout-logistic-v1',gate='G-REPLAY-CONSOLIDATION-001',capability='memory_skill'),
 'attention':dict(get=_mode_attr('attention'),set=_set_mode('attention'),evidence=_ev_none,objective='attention-policy-v1',gate='G-FOCAL-CAPACITY-003',capability='language'),
 'deliberation':dict(get=_mode_attr('deliberation'),set=_set_mode('deliberation'),evidence=_ev_none,objective='deliberation-mode-values-v1',gate='G-FOCAL-CAPACITY-003',capability='language'),
 'callosum':dict(get=_mode_attr('callosum'),set=_set_mode('callosum'),evidence=_ev_none,objective='callosum-channel-utility-v1',gate='G-CALLOSUM-UTILITY-002',capability='language'),
 'gist':dict(get=_gist_get,set=_gist_set,evidence=_ev_none,objective='gist-readout-grouping',gate='STEP2',capability='language'),
 'neuromod_meta':dict(get=lambda r:_ctl('neuromod',r).meta_mode(),set=lambda r,m,a:_ctl('neuromod',r).set_meta_mode(m,a),evidence=_ev_none,objective='neuromod-metaplasticity-retention-v1',gate='G-MODULATOR-SPECIFICITY-001',capability='system'),
}

def empty():return {'revision':REVISION,'heads':{},'ledger':{},'last_review':None}

def _load(store):
    st,v=store.state(KEY,None);st=st or empty()
    if st.get('revision')!=REVISION:raise ValueError('Authority state revision mismatch')
    return st,v
def _mutate(store,fn):
    for attempt in (0,1):
        st,v=_load(store);out=fn(st)
        try:store.set_state(KEY,st,expected=v);return out
        except ValueError:
            if attempt:raise

def observe(store,head,scaffold,learned,scaffold_ok=None,learned_ok=None):
    """Generic shadow ledger: one scaffold-vs-learned decision (and outcomes where known)."""
    if head not in HEADS:raise ValueError('Unbekannter Kopf: '+str(head))
    def f(st):
        l=st['ledger'].setdefault(head,{'n':0,'same':0,'n_out':0,'scaffold_fail':0,'learned_fail':0})
        l['n']+=1;l['same']+=int(scaffold==learned)
        if scaffold_ok is not None and learned_ok is not None:
            l['n_out']+=1;l['scaffold_fail']+=int(not scaffold_ok);l['learned_fail']+=int(not learned_ok)
        return dict(l)
    return _mutate(store,f)

def evidence(r,head,st=None):
    spec=HEADS[head]
    try:ev=dict(spec['evidence'](r))
    except Exception as exc:ev={'n':0,'error':type(exc).__name__}
    l=(st or _load(r.store)[0])['ledger'].get(head)
    if l and l['n']>ev.get('n',0):ev.update(_agree(l['n'],l['same']))
    if l and l['n_out']>=MIN_N:
        sf,lf=l['scaffold_fail']/l['n_out'],l['learned_fail']/l['n_out']
        ev['advantage']=round(sf-lf,4);ev['regression']=ev.get('regression') or lf>sf+REGRESS_MARGIN
    return ev

def verdict(ev):
    """Own shadow gate of one head: PASS, FAIL (regression) or HOLD with the reason."""
    if ev.get('regression'):return {'status':'FAIL','reason':'REGRESSION'}
    if ev.get('passed'):return {'status':'PASS','reason':'HEAD_GATE_PASSED'}
    if ev.get('n',0)<MIN_N:return {'status':'HOLD','reason':'NO_COMPARISON' if not ev.get('n') else 'TOO_FEW_SHADOW_DECISIONS'}
    if ev.get('advantage') is not None and ev['advantage']>0:return {'status':'PASS','reason':'BETTER_OUTCOMES_THAN_SCAFFOLD'}
    if ev.get('agreement') is not None and ev['agreement']>=AGREE_MIN:return {'status':'PASS','reason':'REPRODUCES_SCAFFOLD'}
    return {'status':'HOLD','reason':'BELOW_AGREEMENT'}

def _gate_status():
    try:
        from .gates import summary
        return summary()['gates']
    except Exception:return {}

def _row(st,head):return st['heads'].setdefault(head,{'level':0,'history':[],'last':None})
def _event(row,kind,frm,to,why,origin):
    row['history']=(row['history']+[{'kind':kind,'from':frm,'to':to,'reason':why,'origin':origin,'at':now()}])[-HISTORY:]

def assess(r,head,gates=None,st=None,registry=None):
    spec=HEADS[head];st=st or _load(r.store)[0];ev=evidence(r,head,st);v=verdict(ev)
    obj=(registry or OBJ.registry(r.cfg)).get(spec['objective']);gg=(gates if gates is not None else _gate_status()).get(spec['gate'])
    try:mode=spec['get'](r)
    except Exception as exc:mode='UNAVAILABLE:'+type(exc).__name__
    blockers=[]
    if v['status']!='PASS':blockers.append(v['reason'])
    if not obj or obj.status!='IMPLEMENTED':blockers.append('OBJECTIVE_'+(obj.status if obj else 'MISSING'))
    if gg not in GATE_OK:blockers.append('GATE_'+str(gg))
    return {'head':head,'mode':mode,'level':_row(st,head)['level'] if mode!='ACTIVE' else 2,'evidence':ev,'verdict':v,
            'objective':spec['objective'],'objective_status':obj.status if obj else 'MISSING','gate':spec['gate'],'gate_status':gg,
            'capability':spec['capability'],'candidate_ok':not blockers,'blockers':blockers}

def review(r,origin='SYSTEM'):
    """§14.3 medium timescale: promote 0 -> 1, lapse 1 -> 0, demote a regressing ACTIVE head to SHADOW."""
    gates=_gate_status();reg=OBJ.registry(r.cfg);st=_load(r.store)[0];out={};changes=[]
    for head in HEADS:
        a=assess(r,head,gates,st,reg);out[head]=a
        if a['mode']=='ACTIVE' and a['verdict']['status']=='FAIL':
            try:HEADS[head]['set'](r,'SHADOW','SYSTEM');changes.append((head,2,0,'REGRESSION_FALLBACK_TO_SCAFFOLD'))
            except Exception as exc:a['demote_error']=type(exc).__name__
        elif a['mode']!='ACTIVE':
            lvl=_row(st,head)['level']
            if lvl==0 and a['candidate_ok']:changes.append((head,0,1,a['verdict']['reason']))
            elif lvl>=1 and not a['candidate_ok']:changes.append((head,lvl,0,'EVIDENCE_LAPSED:'+','.join(a['blockers'])))
    def f(s):
        for head,frm,to,why in changes:
            row=_row(s,head);row['level']=to;_event(row,'PROMOTE' if to>frm else 'DEMOTE',frm,to,why,origin)
        for head,a in out.items():_row(s,head)['last']={'verdict':a['verdict'],'blockers':a['blockers'],'at':now()}
        s['last_review']=now()
    _mutate(r.store,f)
    for head,frm,to,why in changes:
        r.store.log('authority_change',None,{'head':head,'from':LEVELS[frm],'to':LEVELS[to],'reason':why[:120],'origin':origin})
        out[head]['level']=to
    return {'heads':out,'changes':[{'head':h,'from':LEVELS[a],'to':LEVELS[b],'reason':w} for h,a,b,w in changes]}

def promote(r,head,authority):
    """CANDIDATE -> ACTIVE: only an explicit human decision, and only while the candidate gate still holds."""
    if head not in HEADS:raise ValueError('Unbekannter Kopf: '+str(head))
    if authority!='EXPLICIT_HUMAN':raise PermissionError('ACTIVE nur per expliziter Nutzerfreigabe (Age 0, §88.1)')
    st=_load(r.store)[0];a=assess(r,head,st=st)
    if _row(st,head)['level']<1 or not a['candidate_ok']:
        raise ValueError('Kein bestandener Kandidat: '+(', '.join(a['blockers']) or 'erst :authority review'))
    HEADS[head]['set'](r,'ACTIVE','EXPLICIT_HUMAN')
    def f(s):row=_row(s,head);_event(row,'PROMOTE',row['level'],2,'HUMAN_APPROVED',authority);row['level']=2
    _mutate(r.store,f);r.store.log('authority_change',None,{'head':head,'from':'CANDIDATE','to':'ACTIVE','reason':'HUMAN_APPROVED','origin':'USER'})
    return assess(r,head)

def demote(r,head,origin='USER'):
    """Any level -> SHADOW; the scaffold acts again. Always allowed."""
    if head not in HEADS:raise ValueError('Unbekannter Kopf: '+str(head))
    HEADS[head]['set'](r,'SHADOW','SYSTEM')
    def f(s):row=_row(s,head);_event(row,'DEMOTE',row['level'],0,'USER' if origin=='USER' else 'SYSTEM',origin);row['level']=0
    _mutate(r.store,f);r.store.log('authority_change',None,{'head':head,'from':'ANY','to':'SHADOW','reason':'DEMOTE','origin':origin})
    return assess(r,head)

def report(r):
    st=_load(r.store)[0];gates=_gate_status();reg=OBJ.registry(r.cfg)
    return {'revision':REVISION,'levels':LEVELS,'last_review':st['last_review'],
            'heads':{h:{k:v for k,v in assess(r,h,gates,st,reg).items() if k!='head'}|{'history':_row(st,h)['history'][-4:]} for h in HEADS},
            'claim_limit':'Promotion path and gates only; no head becomes ACTIVE without an explicit human decision at Age 0'}

def operator_command(r,args):
    """:authority [status|review|promote <Kopf>|demote <Kopf>|<Kopf>]"""
    from .common import dumps
    if not args or args==['status']:return dumps(report(r))
    if args==['review']:return dumps(review(r,'USER'))
    if len(args)==2 and args[0]=='promote':return dumps(promote(r,args[1],'EXPLICIT_HUMAN'))
    if len(args)==2 and args[0]=='demote':return dumps(demote(r,args[1],'USER'))
    if len(args)==1 and args[0] in HEADS:return dumps(assess(r,args[0]))
    raise ValueError(':authority [status|review|promote <Kopf>|demote <Kopf>|<Kopf>]')

# -- §14.3 / §14.4 learning timescales as scheduled jobs ------------------------------------------------------------
MEDIUM_S=1800  # BOOT: at most one medium-timescale review per 30 min of idle

def medium_due(store,clock_now):
    last=_load(store)[0]['last_review']
    return last is None or float(clock_now)-float(last)>=MEDIUM_S

def job(r,action,origin='SYSTEM'):
    """learn_medium: authority review + admission retrain when new labels arrived.
    learn_slow (after a full night): review, objective registry check, and — outside RECORD_ONLY — post the AG6
    consolidation of an already staged batch (training itself stays gated by AG6/drift gates)."""
    out={'action':action,'review':review(r,origin)['changes']}
    if action=='learn_medium':
        try:  # WP-T8: refit the control-grounded world model on new own transitions
            from .world_model import fit as wm_fit
            out['world_model']=wm_fit(r.store).get('status')
        except Exception as exc:out['world_model_error']=type(exc).__name__
        try:  # WP-T8 §6.6: curiosity may pick its own practice region only with Age right + exploration budget
            from .agi import hub
            g=hub(r);region=g.curiosity.choose(origin='SELF')
            if region and getattr(r,'sleep',None) is not None:out['practice_event']=r.sleep.scheduler.post('TIMER',origin='SELF',action='growth_practice',payload={'region':region},dedup='practice:'+region)
            out['curiosity']=region
        except Exception as exc:out['curiosity_error']=type(exc).__name__
        try:
            from .admission import Admission
            a=Admission(r.store,r.cfg);n=sum(x['label'] is not None for x in a.table())
            def f(s):
                prev=s.get('admission_labels',0);s['admission_labels']=n;return prev
            if n>_mutate(r.store,f):out['admission']=a.train().get('status')
        except Exception as exc:out['admission_error']=type(exc).__name__
    elif action=='learn_slow':
        out['objectives']=OBJ.report(r.cfg)['counts']
        from .homeostasis import holding
        if holding(r.store):out['consolidate_held']='HOMEOSTASIS_GATE_FAIL'  # WP-T11: slow consolidation waits for a passing Sleep C
        elif r.cfg.get('learning_mode','RECORD_ONLY')!='RECORD_ONLY':
            try:
                from .agi import hub
                staged=[b for b in hub(r).weights.box.load()[0]['batches'].values() if b['status']=='STAGED']
                if staged and getattr(r,'sleep',None) is not None:out['consolidate_event']=r.sleep.scheduler.post('TIMER',action='growth_consolidate',dedup='growth-consolidate')
            except Exception as exc:out['consolidate_error']=type(exc).__name__
    else:raise ValueError('Unbekannte Lern-Aktion: '+str(action))
    out['status']='DONE';return out

def review_candidates(r):
    """Heads at CANDIDATE that wait for a human decision (read-only; used by the open-questions artifact)."""
    st=_load(r.store)[0]
    return sorted(h for h,row in st['heads'].items() if row.get('level')==1)
