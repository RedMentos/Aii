"""G9/§17/§95 developmental age envelope: system stage, capability stages, continuous maturity.

Stage gates need several consecutive, distinct passing evidence records (hysteresis); a
separate lower maintenance band demotes after repeated or severe regression. Stages never
rise above min(user_stage_cap, BUILD_CEILING); a blocked gate only records a proposal.
Rights and maturity are orthogonal (§95.2): maturity scales budgets inside what the
stage ceiling, user cap, hard rules, user permissions and resource state allow.
BUILD_CEILING is 0 until STEP7 (Age>0 is not released); all thresholds are BOOT values.
"""
from .common import now,uid

STATE_KEY='age_control'
REVISION='age-envelope-v1'
BUILD_CEILING=0
STAGES=range(6)
CAPABILITIES=('language','routing_skill','memory_skill','tool','vision','audio','social','body_port')
METRICS=('competence','stability','retention','calibration','memory_health','safe_self_control')
PROMOTE_AFTER=3  # BOOT: consecutive distinct passing evidence records per gate
DEMOTE_AFTER=2   # BOOT: consecutive maintenance failures before a one-stage demotion
BAND=.05         # BOOT: hysteresis gap between promotion and maintenance thresholds
EMA=.2           # BOOT: continuous maturity smoothing
HISTORY=64
# Promotion gate for reaching stage s (index s); stage 0 has no gate. BOOT engineering values.
GATES={'experience':(0,50,200,800,2000,5000),'competence':(0,.6,.7,.78,.85,.9),'stability':(0,.7,.8,.85,.9,.93),
       'retention':(0,.9,.92,.94,.96,.97),'calibration':(0,.6,.7,.75,.8,.85),'memory_health':(0,.9,.9,.92,.94,.95),
       'safe_self_control':(0,.95,.97,.98,.99,.995)}
# Minimum stage per right (§17.7-17.12). Hard-rule edits are never an age right.
RIGHTS={'direct_route':0,'episodic_memory_write':0,'simple_feedback':0,'small_shadow_update':0,'late_correction':0,
 'shadow_alternative_routes':1,'autonomous_memory_edit':1,'simple_tool_choice':1,'skip_translator':1,'short_dream':1,'route_exploration':1,
 'deliberation_modes':2,'tool_learning':2,'raw_body_attempt':2,'procedural_memory':2,'routine_skip_defaults':2,'adaptive_gist_grouping':2,
 'long_loops':3,'own_sleep_planning':3,'request_teacher':3,'safe_self_edit_without_dialog':3,
 'self_initiative':4,'resume_open_goals':4,'choose_learning_goals':4,'active_info_search':4,'propose_config_changes':4,
 'integrate_new_body':5,'body_swap':5,'structural_modification':5}
STRUCTURAL={'integrate_new_body','body_swap','structural_modification'}
RESOURCE_BLOCKED={'RED':{'short_dream','route_exploration','long_loops','own_sleep_planning','self_initiative','active_info_search','tool_learning','raw_body_attempt'},
                  'ORANGE':{'short_dream','long_loops','route_exploration','self_initiative','active_info_search','tool_learning'},  # §97.2: pause shadow learning
                  'YELLOW':{'long_loops','route_exploration','self_initiative'}}
NEVER={'edit_hard_rules','exceed_user_stage_cap'}
# WP-T2 §17.4: the capability whose stage governs a right (ceiling = min(system, capability)); unlisted rights follow the system stage.
# Capabilities fed by no measurement (vision, audio, social, body_port) stay at 0, so their rights stay closed honestly.
RIGHT_CAPABILITY={'simple_tool_choice':'tool','tool_learning':'tool','active_info_search':'tool',
 'episodic_memory_write':'memory_skill','autonomous_memory_edit':'memory_skill','procedural_memory':'memory_skill',
 'deliberation_modes':'language','skip_translator':'language','adaptive_gist_grouping':'language','long_loops':'language',
 'shadow_alternative_routes':'routing_skill','route_exploration':'routing_skill','direct_route':'routing_skill','routine_skip_defaults':'routing_skill',
 'raw_body_attempt':'body_port','integrate_new_body':'body_port','body_swap':'body_port'}
# Budget range [lo,hi] per stage; maturity interpolates inside the range so budgets change smoothly within a stage.
BUDGETS={'own_loops':((0,0),(0,1),(1,2),(2,4),(4,6),(6,8)),'focal_depth':((1,1),(1,2),(2,3),(3,4),(4,5),(5,6)),
 'dream_seconds':((0,5),(5,30),(30,120),(120,300),(300,900),(900,1800)),'replay_items':((0,4),(4,8),(8,16),(16,32),(32,64),(64,128)),
 'context_edit_tokens':((0,32),(32,64),(64,128),(128,256),(256,512),(512,1024)),'exploration_rate':((0,0),(0,.05),(.05,.1),(.1,.15),(.15,.2),(.2,.25)),
 'autonomous_effort_max':((1,1),(1,2),(2,2),(2,3),(3,3),(3,4))}
EFFORT_LEVELS=('disabled','low','adaptive','high','max')
GIST_BASE=(8,8,10,12,14,16);GIST_FINE=4;GIST_SLOTS=12
PLASTICITY_BASE=(1.,.9,.75,.6,.5,.45)
HOLD_AFTER_DEMOTION=4  # WP-AB stable_reopen: evidence records during which a demotion does not raise plasticity (BOOT)
NOISE_EMA=.2;NOISE_K=2.;NOISE_REF=.05;NOISE_MIN_N=4  # noise_aware: MAD of competence around its EMA; fails inside K*noise are noise (BOOT)
PERSISTENT_ERRORS=2    # WP-AB stable_reopen: consecutive retention/regression failures before errors reopen plasticity (BOOT)

def _subject(stage=0):
    return {'stage':stage,'pass_streak':[],'fail_streak':0,'maturity':{'trust':0.,'retention':0.,'calibration':0.,'stability':0.,'competence':0.},
            'evidence_count':0,'last_evidence':None}
def default_state():
    return {'revision':REVISION,'system':_subject(),'capabilities':{c:_subject() for c in CAPABILITIES},'frozen':False,
            'structural_locked':True,'proposals':[],'history':[],'seen_evidence':[]}

def gate_pass(metrics,stage,band=0.):
    """True if metrics meet the gate for `stage`; band lowers ratio thresholds (maintenance band)."""
    if stage<=0:return True
    if metrics.get('regression_pass') is not True:return False
    if metrics.get('experience',0)<GATES['experience'][stage]:return False
    return all(isinstance(metrics.get(k),(int,float)) and metrics[k]>=GATES[k][stage]-band for k in METRICS)

class AgeControl:
    def __init__(self,store,cfg,build_ceiling=None):
        self.s=store;self.cfg=cfg;self.build_ceiling=BUILD_CEILING if build_ceiling is None else build_ceiling
        if not 0<=self.build_ceiling<=5:raise ValueError('build ceiling')
    def state(self):
        st,v=self.s.state(STATE_KEY,None)
        return (st or default_state()),v
    def _save(self,st,version):self.s.set_state(STATE_KEY,st,expected=version)
    def cap(self):return min(int(self.cfg['user_stage_cap']),self.build_ceiling)
    def _subject(self,st,name):
        if name=='system':return st['system']
        if name not in st['capabilities']:raise ValueError('Unbekannte Capability: '+name)
        return st['capabilities'][name]
    def _event(self,st,kind,subject,old,new,reason):
        item={'id':uid('age'),'kind':kind,'subject':subject,'from':old,'to':new,'reason':reason,'generation':self.s.generation_id,'created':now()}
        st['history']=(st['history']+[item])[-HISTORY:];return item

    # Stage ceilings ---------------------------------------------------------------------------------------------
    def system_stage(self,st=None):return min((st or self.state()[0])['system']['stage'],self.cap())
    def ceiling(self,capability='system',st=None):
        st=st or self.state()[0];c=self.system_stage(st)
        return c if capability=='system' else min(c,self._subject(st,capability)['stage'])

    # Evidence, promotion, demotion ------------------------------------------------------------------------------
    def record(self,subject,metrics,evidence_id=None):
        """Feed one evidence record (one stable regression/shadow/retention assessment) for system or a capability."""
        st,v=self.state();sub=self._subject(st,subject);eid=evidence_id or uid('evidence')
        if eid in st['seen_evidence']:raise ValueError('Nachweis schon gezählt: '+eid)
        st['seen_evidence']=(st['seen_evidence']+[eid])[-512:];sub['evidence_count']+=1;sub['last_evidence']=eid
        m=sub['maturity'];noise_aware=self.cfg.get('age_plasticity_policy','boot')=='noise_aware';within_noise=False
        if isinstance(metrics.get('competence'),(int,float)):  # measurement-noise estimate (always tracked; used by noise_aware)
            dev=abs(float(metrics['competence'])-m['competence']);nz=sub.setdefault('noise',{'mad':0.,'n':0})
            within_noise=nz['n']>=NOISE_MIN_N and m['competence']-float(metrics['competence'])<=NOISE_K*nz['mad']
            if nz['n']>=NOISE_MIN_N:dev=min(dev,NOISE_K*nz['mad'])  # winsorized: a real competence change must not inflate the noise estimate
            nz['mad']=round(dev if nz['n']==0 else (1-NOISE_EMA)*nz['mad']+NOISE_EMA*dev,6);nz['n']+=1
        for k in ('retention','calibration','stability','competence'):
            if isinstance(metrics.get(k),(int,float)):m[k]=round((1-EMA)*m[k]+EMA*float(metrics[k]),6)
        if isinstance(metrics.get('competence'),(int,float)) and isinstance(metrics.get('safe_self_control'),(int,float)):
            m['trust']=round((1-EMA)*m['trust']+EMA*min(metrics['competence'],metrics['safe_self_control']),6)
        out={'subject':subject,'evidence_id':eid,'stage':sub['stage'],'change':None}
        severe=metrics.get('regression_pass') is False and metrics.get('retention',1)<GATES['retention'][max(sub['stage'],1)]-BAND
        if sub['stage']>0 and (severe or not gate_pass(metrics,sub['stage'],BAND)):
            if noise_aware and within_noise and not severe:  # a drop inside the measured noise band is not evidence of lost competence
                sub['pass_streak']=[];out['noise']='FAIL_WITHIN_NOISE_BAND';out['stage']=sub['stage'];self._save(st,v);return out
            sub['fail_streak']+=1;sub['pass_streak']=[]
            if severe or sub['fail_streak']>=DEMOTE_AFTER:
                old=sub['stage'];sub['stage']-=1;sub['fail_streak']=0
                if self.cfg.get('age_plasticity_policy','boot')=='stable_reopen':  # a chain of demotions keeps the highest held stage
                    h=sub.get('plasticity_hold') or {};sub['plasticity_hold']={'stage':max(old,int(h.get('stage',0))),'until':sub['evidence_count']+HOLD_AFTER_DEMOTION}
                out['change']=self._event(st,'DEMOTE',subject,old,sub['stage'],'severe regression' if severe else f'{DEMOTE_AFTER} maintenance failures')
        else:
            sub['fail_streak']=0;target=sub['stage']+1
            if target<=5 and gate_pass(metrics,target):
                sub['pass_streak']=(sub['pass_streak']+[eid])[-PROMOTE_AFTER:]
                if len(sub['pass_streak'])>=PROMOTE_AFTER:
                    limit=self.cap() if subject=='system' else min(self.cap(),5)
                    blocked='frozen' if st['frozen'] else ('user_stage_cap' if target>int(self.cfg['user_stage_cap']) else ('build_ceiling' if target>limit else None))
                    if blocked:
                        prop={'subject':subject,'to':target,'blocked_by':blocked,'evidence':list(sub['pass_streak']),'created':now()}
                        st['proposals']=[p for p in st['proposals'] if p['subject']!=subject][-15:]+[prop];out['proposal']=prop
                    else:
                        old=sub['stage'];sub['stage']=target;sub['pass_streak']=[]
                        if sub.get('plasticity_hold') and target>=int(sub['plasticity_hold']['stage']):sub.pop('plasticity_hold')
                        st['proposals']=[p for p in st['proposals'] if p['subject']!=subject]
                        out['change']=self._event(st,'PROMOTE',subject,old,target,f'{PROMOTE_AFTER} distinct passing evidence records')
            else:sub['pass_streak']=[]
        out['stage']=sub['stage'];self._save(st,v)
        if out['change']:self.s.log('age_transition',None,{'subject':subject,'from':out['change']['from'],'to':out['change']['to'],'kind':out['change']['kind']})
        return out

    # User control (§17.3) ---------------------------------------------------------------------------------------
    def freeze(self,on):
        st,v=self.state();st['frozen']=bool(on);self._event(st,'FREEZE' if on else 'UNFREEZE','system',None,None,'user');self._save(st,v);return st['frozen']
    def lock_structural(self,on):
        st,v=self.state();st['structural_locked']=bool(on);self._event(st,'STRUCTURAL_LOCK' if on else 'STRUCTURAL_UNLOCK','system',None,None,'user');self._save(st,v);return st['structural_locked']
    def lower(self,subject,stage):
        """User may only lower a stage; raising needs evidence and stays below the cap."""
        if not 0<=stage<=5:raise ValueError('Stufe 0..5')
        st,v=self.state();sub=self._subject(st,subject)
        if stage>sub['stage']:raise ValueError('Anheben nur über Nachweise; Nutzer kann nur absenken oder die Obergrenze setzen')
        old=sub['stage'];sub['stage']=stage;sub['pass_streak']=[];sub['fail_streak']=0
        item=self._event(st,'USER_LOWER',subject,old,stage,'user');self._save(st,v);return item
    def apply_cap(self):
        """After a cap change: stored stages above the new cap are clamped (logged)."""
        st,v=self.state();cap=int(self.cfg['user_stage_cap']);changed=[]
        for name,sub in [('system',st['system'])]+list(st['capabilities'].items()):
            if sub['stage']>cap:changed.append(self._event(st,'CAP_CLAMP',name,sub['stage'],cap,'user_stage_cap'));sub['stage']=cap;sub['pass_streak']=[]
        self._save(st,v);return changed
    def open_window(self,capability):
        """Lifelong (§17.13): a new domain/modality starts a young capability without touching other stages."""
        st,v=self.state()
        if capability in st['capabilities']:raise ValueError('Capability existiert schon')
        st['capabilities'][capability]=_subject();self._event(st,'NEW_CAPABILITY',capability,None,0,'new sensitive window');self._save(st,v)

    # Rights and budgets (§17.5, §95.2) --------------------------------------------------------------------------
    def allowed(self,right,capability='system',resource_mode='GREEN',user_permissions=None,hard_rule_block=False):
        if right in NEVER:return False
        if right not in RIGHTS:raise ValueError('Unbekanntes Recht: '+right)
        st=self.state()[0]
        if hard_rule_block or (user_permissions is not None and right not in user_permissions):return False
        if right in STRUCTURAL and st['structural_locked']:return False
        if right in RESOURCE_BLOCKED.get(resource_mode,()):return False
        return self.ceiling(capability,st)>=RIGHTS[right]
    def may(self,right,resource_mode='GREEN',user_permissions=None,hard_rule_block=False):
        """WP-T2: a right judged at its own capability's ceiling (RIGHT_CAPABILITY), not only the system stage."""
        return self.allowed(right,RIGHT_CAPABILITY.get(right,'system'),resource_mode,user_permissions,hard_rule_block)
    def rights(self,resource_mode='GREEN',user_permissions=None):
        """Per-capability permission view for ExecState.permission_flags (§3.3.0 C0): granted rights, stage per capability."""
        st=self.state()[0]
        caps={c:self.ceiling(c,st) for c in st['capabilities']}
        granted=sorted(r for r in RIGHTS if self.may(r,resource_mode,user_permissions))
        return {'age':self.system_stage(st),'by_capability':caps,'granted':granted,'resource_mode':resource_mode,
                'frozen':st['frozen'],'structural_locked':st['structural_locked']}
    def maturity(self,capability='system',st=None):
        st=st or self.state()[0];m=self._subject(st,capability)['maturity']
        return round(min(m['trust'],m['retention'],m['calibration']),6)
    def budgets(self,capability='system',resource_mode='GREEN'):
        st=self.state()[0];stage=self.ceiling(capability,st);m=self.maturity(capability,st);out={}
        for k,ranges in BUDGETS.items():
            lo,hi=ranges[stage];val=lo+(hi-lo)*m
            out[k]=int(round(val)) if isinstance(lo,int) and isinstance(hi,int) else round(val,6)
        if resource_mode=='RED':out.update(dream_seconds=0,replay_items=0,exploration_rate=0,own_loops=0)
        elif resource_mode=='ORANGE':out.update(dream_seconds=0,replay_items=0,exploration_rate=0)  # §97.2 ORANGE: no replay/dream, Sleep C only
        out['autonomous_effort_max']=EFFORT_LEVELS[int(out['autonomous_effort_max'])]
        mm=self._subject(st,capability)['maturity']
        out['teacher_reliance']=round(1-.15*stage-.1*mm['trust'],6)
        out['route_authority']=round(min(1.,.15*stage+.25*mm['trust']),6)
        return out
    def gist_resolution(self,capability='language',novelty=0.,conflict=False,literal=False,boundary_confidence=1.):
        """Age ↑ ≠ group size monotone ↑: novelty/conflict/literal/low boundary confidence refine temporarily."""
        st=self.state()[0];stage=self.ceiling(capability,st);m=self.maturity(capability,st)
        adaptive=capability in st['capabilities'] and self.allowed('adaptive_gist_grouping',capability)  # WP-T2: maturity widening is an Age-2 right
        hi=GIST_BASE[min(stage+1,5)] if adaptive else GIST_BASE[stage];size=GIST_BASE[stage]+(hi-GIST_BASE[stage])*m
        if literal:size=GIST_FINE
        else:
            size*=1-.5*max(0.,min(1.,float(novelty)))
            if conflict:size=min(size,GIST_BASE[0]*.75)
            if boundary_confidence<.5:size=min(size,GIST_BASE[0])
        return {'tokens_per_group':max(GIST_FINE,int(round(size))),'slots':GIST_SLOTS,'stage':stage,'adaptive_grouping':adaptive}
    def plasticity(self,capability='system',novel_domain=False,repeated_errors=0,new_modality=False):
        """Reopenable plasticity (§95.3): stable mature domains lower it, novelty/errors reopen it boundedly.
        Policy `stable_reopen` (WP-AB, flag `age_plasticity_policy`, for user review): a demotion keeps the pre-demotion
        plasticity for HOLD_AFTER_DEMOTION evidence records, and errors reopen only once they persist (§99 ablation:
        under label noise the BOOT rule demotes and so raises plasticity, the wrong direction)."""
        st=self.state()[0];sub=self._subject(st,capability);stage=sub['stage'];stab=sub['maturity']['stability']
        stable=self.cfg.get('age_plasticity_policy','boot')=='stable_reopen';hold=sub.get('plasticity_hold')
        if stable and hold:
            if sub['evidence_count']<hold['until'] or int(repeated_errors)<PERSISTENT_ERRORS:stage=max(stage,int(hold['stage']))  # released only by persistent errors
        p=PLASTICITY_BASE[stage]*(1-.3*stab)
        if new_modality:p=1.
        if novel_domain:p=max(p,.8)
        n=int(repeated_errors)-(PERSISTENT_ERRORS-1 if stable else 0)
        if self.cfg.get('age_plasticity_policy','boot')=='noise_aware':  # noisy labels lower the step size and damp error reopening
            nz=(sub.get('noise') or {}).get('mad',0.) if (sub.get('noise') or {}).get('n',0)>=NOISE_MIN_N else 0.
            damp=1/(1+nz/NOISE_REF);p*=.5+.5*damp
            if n>0:p+=min(.3,.1*n)*damp
            return round(min(1.,p),6)
        if n>0:p+=min(.3,.1*n)
        return round(min(1.,p),6)
    def view(self):
        st,v=self.state()
        return {'revision':REVISION,'state_version':v,'system_stage':self.system_stage(st),'earned_system_stage':st['system']['stage'],
                'user_stage_cap':int(self.cfg['user_stage_cap']),'build_ceiling':self.build_ceiling,'frozen':st['frozen'],
                'structural_locked':st['structural_locked'],'auto_promotion':self.cap()>0 and not st['frozen'],
                'capabilities':{k:{'stage':c['stage'],'effective_ceiling':self.ceiling(k,st),'maturity':self.maturity(k,st),'evidence':c['evidence_count'],'pass_streak':len(c['pass_streak']),'noise_mad':(c.get('noise') or {}).get('mad')} for k,c in st['capabilities'].items()},'plasticity_policy':self.cfg.get('age_plasticity_policy','boot'),
                'proposals':st['proposals'],'history':st['history'][-8:],'budgets':self.budgets('system')}

def controller(runtime):
    """Runtime-scoped instance without touching runtime.py; reads the live config dict."""
    a=getattr(runtime,'age',None)
    if a is None:a=runtime.age=AgeControl(runtime.store,runtime.cfg)
    return a
