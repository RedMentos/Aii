"""WP-AG1..AG12: infrastructure for the twelve gaps between V13 and a general learner (FORSCHUNG.md §9).

Each module is the plumbing a model can later be taught through, step by step; none of them
makes V13 general by itself. All of them are model-free, persistent, Age-gated and end in a
human decision wherever weights, structure, hard rules or the outside world are touched.

  AG0  slots.py         model slots: swap any model (B1/B2/C3/C2/teacher/embedder/world), carry or relearn learned state
  AG1  teacher.py        teacher requests, reference traces, distillation set, reliance/dropout
  AG2  grounding.py      predicted vs actual outcome of own actions (M_world), modality registry
  AG3  goals.py          persistent goal tree, plans, GOAL_WAKE through the G13 scheduler
  AG4  skills.py         declarative skill library, lifecycle, frontier practice
  AG5  curiosity.py      learning progress + novelty as intrinsic value, Age-bounded exploration
  AG6  weights.py        nightly consolidation into weights: stage → train → retention gate → user
  AG7  abstraction.py    cluster → induce rule → test on held-out cases (DSL inducer)
  AG8  self_improve.py   knob/learning-rule proposals, sandbox eval, regression shield, user approval
  AG9  metacog.py        calibration per component, second-attempt/abstain, semantic entropy
  AG10 tools.py          tool registry + per-call transaction, safe calc, outcome → AG2
  AG11 user_model.py     evidence-bound beliefs about the user, decay, forget
  AG13 residency.py     MoE experts in RAM only while active; learning only while resident
  AG12 generality.py     fixed eval suite: seen/unseen, transfer, forgetting, planning depth, calibration
       solver.py         body solvers (C3/B1/B2/ensemble 'v13') for the suite, no memory/tools/store writes
  AG1  teacher_backends.py  local TEACHER runner or Claude (cloud, only with user permission)
  AG6  trainers.py      live trainer choice: LoRA (served by the runner) / sparse memory / none
"""
from .base import age_allows

# Scheduler actions handled here (added to scheduler.ACTIONS).
ACTIONS=('growth_goal','growth_eval','growth_consolidate','growth_practice','growth_teacher')

class Growth:
    """Runtime-scoped hub. Built lazily so runtime.py stays untouched (like age.controller)."""
    def __init__(self,store,cfg,home=None,age=None,scheduler=None):
        from .generality import GeneralityEval
        from .weights import WeightConsolidation
        from .metacog import Metacognition
        from .goals import GoalStore
        from .curiosity import Curiosity
        from .tools import ToolRegistry
        from .grounding import Grounding
        from .skills import SkillLibrary
        from .abstraction import Abstraction
        from .self_improve import SelfImprovement
        from .teacher import TeacherDistillation
        from .user_model import UserModel
        from .slots import ModelSlots
        from .residency import ExpertResidency
        self.s=store;self.cfg=cfg;self.home=home;self.age=age;self.scheduler=scheduler
        self.solver=None  # AG12 body solver (solver.make_solver); set by hub() once a body model is installed
        self.eval=GeneralityEval(store,home)
        self.weights=WeightConsolidation(store,cfg,self.eval,age,None,home)
        self.metacog=Metacognition(store)
        self.goals=GoalStore(store,age,scheduler)
        self.curiosity=Curiosity(store,age)
        self.grounding=Grounding(store)
        self.tools=ToolRegistry(store,age,on_outcome=self._tool_outcome)
        self.forecast=None  # Thread M: toolforecast.ToolForecast, set by hub()
        self.skills=SkillLibrary(store,age,self.tools)
        self.abstraction=Abstraction(store)
        self.improve=SelfImprovement(store,cfg,age)
        self.teacher=TeacherDistillation(store,age,self.eval)
        self.users=UserModel(store)
        self.slots=ModelSlots(store,age)
        self.residency=ExpertResidency(store)
    def _tool_outcome(self,tx):
        """ToolRegistry.on_outcome: AG2 grounding as before; a SHADOW tool forecast (IH-H29 `predicted`) is scored on its own
        and hidden from grounding, whose frequency baseline expects {'outcome',...} predictions."""
        from ..toolforecast import is_forecast
        fc=is_forecast(tx.get('predicted'))
        out=self.grounding.from_tool(dict(tx,predicted=None) if fc else tx)
        if fc and self.forecast is not None:self.forecast.observe(tx)
        return out
    def age_evidence(self,record=False):
        """Metrics for age.record() from real measurements (maturity.py); record=True feeds one evidence record."""
        from .maturity import collect,estimate
        m=collect(self,self.s,self.cfg);out={'metrics':m}
        stage=self.age.system_stage() if self.age is not None else 0
        out['next_stage']=estimate(m,stage)
        if record and self.age is not None:  # WP-T2: system + every measured capability
            from .maturity import feed
            from ..common import uid
            out['recorded']=feed(self,'sleep',record if isinstance(record,str) else uid('night'),m)['recorded']
        return out
    def report(self):
        parts={'AG0':self.slots,'AG1':self.teacher,'AG2':self.grounding,'AG3':self.goals,'AG4':self.skills,'AG5':self.curiosity,'AG6':self.weights,
               'AG7':self.abstraction,'AG8':self.improve,'AG9':self.metacog,'AG10':self.tools,'AG11':self.users,'AG12':self.eval,'AG13':self.residency}
        out={}
        for k,m in parts.items():
            try:out[k]=m.report()
            except Exception as exc:out[k]={'error':type(exc).__name__+': '+str(exc)[:200]}
        return out

def hub(runtime):
    g=getattr(runtime,'growth',None)
    if g is None:
        from ..age import controller
        sl=getattr(runtime,'sleep',None)
        g=runtime.growth=Growth(runtime.store,runtime.cfg,runtime.home,controller(runtime),getattr(sl,'scheduler',None))
    if getattr(g,'forecast',0) is None and getattr(runtime,'home',None) is not None:  # 0: test doubles without the slot
        try:
            from ..toolforecast import for_runtime
            g.forecast=for_runtime(runtime)
        except Exception as exc:runtime.store.log('tool_forecast_unavailable',None,{'error':type(exc).__name__})
    if getattr(runtime,'pool',None) is not None:
        try:
            from . import teacher_backends
            teacher_backends.register(g,runtime)
            if g.solver is None:
                from .solver import make_solver
                g.solver=make_solver(runtime,'v13')
        except Exception as exc:runtime.store.log('growth_wiring_error',None,{'error':type(exc).__name__})
    return g

# -- scheduler glue (called from sleep.SleepRuntime) -----------------------------------------------------
def after_sleep(sleep_runtime,event,report):
    """After a completed full sleep: stage a AG6 batch; post a AG12 eval when due and a solver exists."""
    if report.get('mode')!='full' or report.get('status')!='DONE':return None
    g=hub(sleep_runtime.r);out={'g6':g.weights.stage('SYSTEM')}
    out['age_evidence']=g.age_evidence(record=True).get('recorded')  # one evidence record per full night
    if g.solver is not None and g.eval.due() and g.scheduler is not None:
        out['g12_event']=g.scheduler.post('TIMER',origin='SYSTEM',action='growth_eval',dedup='growth-eval')
    return out

def job(sleep_runtime,event):
    """Run one growth action dispatched by the G13 scheduler. Background work stays cancellable."""
    g=hub(sleep_runtime.r);a=event['action'];r=sleep_runtime.r
    if a=='growth_goal':return g.goals.on_wake(event)
    if a=='growth_eval':
        from .solver import BodySolver,run
        name=(event.get('payload') or {}).get('solver') or (g.solver.name if isinstance(g.solver,BodySolver) else None)
        if name:return run(g,r,name,label='user' if event['origin']=='USER' else 'scheduled',cancel=r.cancel_event)
        if g.solver is None:return {'status':'NO_SOLVER'}
        return {'status':g.eval.run(g.solver,label='scheduled',cancel=r.cancel_event)['status']}
    if a=='growth_teacher':
        from .teacher_backends import fulfil_open
        return fulfil_open(g,r,(event.get('payload') or {}).get('backend'),r.cancel_event)
    if a=='growth_consolidate':
        st=g.weights.stage('USER' if event['origin']=='USER' else 'SYSTEM',include_sdft=True)  # corrections marked `learn` (WP-S5 SDFT)
        if st.get('batch_id') and st['status']=='STAGED':
            from .trainers import install
            st['trainer']=install(g,r)['active']  # real trainer when master/torch/runner exist, else honest NO_TRAINER
            st['trained']=g.weights.train_and_gate(st['batch_id'],r.cancel_event)['status']
        return st
    if a=='growth_practice':
        region=g.curiosity.choose([i['family'] for i in g.eval.practice_items()],origin='USER' if event['origin']=='USER' else 'SELF')
        return {'status':'DONE' if region else 'NO_TARGET','region':region,
                'items':[i['id'] for i in g.skills.practice([i for i in g.eval.practice_items() if i['family']==region])] if region else []}
    raise ValueError('Unbekannte Growth-Aktion: '+str(a))

def operator_command(r,args):
    """:growth [status|age|slots|export <Slot>|eval|goals|goal <Titel>|consolidate|approve <batch>|reject <batch>|tools|enable <tool>|calc <Ausdruck>]"""
    from ..common import dumps
    g=hub(r)
    if not args or args==['status']:return dumps(g.report())
    c=args[0]
    if c=='eval' and len(args)>1 and args[1]=='run':
        from .solver import ROLES
        name=args[2] if len(args)>2 else 'v13'
        if name not in ROLES:raise ValueError('Solver: '+'|'.join(ROLES))
        if r.sleep is None:raise ValueError('Kein Scheduler')
        r.sleep.scheduler.post('TIMER',origin='USER',action='growth_eval',payload={'solver':name},dedup='growth-eval-'+name)
        return f'AG12-Lauf mit {name} eingeplant (88 Aufgaben); startet sobald nichts anderes läuft. Ergebnis: :growth eval'
    if c=='eval' and len(args)>1 and args[1]=='curve':
        return dumps(g.eval.curve(args[3] if len(args)>3 else 'overall',args[2] if len(args)>2 else None)[-24:])
    if c=='eval':return dumps(g.eval.report()|{'curve':g.eval.curve('overall')[-12:]})
    if c=='trainer':
        from . import trainers
        if len(args)==1:return dumps(trainers.install(g,r))
        if args[1]=='cfg':  # :growth trainer cfg lr=3e-4 anchor_weight=8 (measured per-device LoRA overrides; 'cfg reset' clears)
            kv={} if args[2:]==['reset'] else dict(a.split('=',1) for a in args[2:])
            return dumps(trainers.set_lora_cfg(g,r,{k:__import__("json").loads(v) if v[:1] in '[{"' else float(v) if any(c in v for c in '.e') else int(v) for k,v in kv.items()}))
        return dumps(trainers.choose(g,r,args[1],args[2] if len(args)>2 else None))
    if c=='teacher':
        from . import teacher_backends as tb
        tb.register(g,r);sub=args[1] if len(args)>1 else 'status'
        if sub=='status':return dumps(g.teacher.report())
        if sub=='cloud' and len(args)==3 and args[2] in ('on','off'):
            g.teacher.allow_cloud(args[2]=='on');return 'Cloud-Lehrer '+('erlaubt: Fragen verlassen dann das Handy' if args[2]=='on' else 'aus')
        if sub=='ask' and len(args)>2:
            rid=g.teacher.request(' '.join(args[2:]),'language','USER',reason='operator')
            return 'Lehrer-Anfrage: '+str(rid)+' (beantworten mit :growth teacher run)'
        if sub=='run':
            if r.sleep is None:raise ValueError('Kein Scheduler')
            payload={'backend':args[2]} if len(args)>2 else {}
            r.sleep.scheduler.post('TIMER',origin='USER',action='growth_teacher',payload=payload,dedup='growth-teacher')
            return 'Lehrer-Lauf eingeplant.'
        if sub=='dataset':return dumps(g.teacher.dataset(limit=20))
        raise ValueError(':growth teacher [status|cloud on|off|ask <Frage>|run [local|claude]|dataset]')
    if c=='goals':return dumps(g.goals.report()|{'goals':g.goals.tree()})
    if c=='goal' and len(args)>1:return 'Ziel angelegt: '+g.goals.add(' '.join(args[1:]),'USER')
    if c=='consolidate':
        if r.sleep is None:raise ValueError('Kein Scheduler')
        r.sleep.scheduler.post('TIMER',origin='USER',action='growth_consolidate');return 'Konsolidierung eingeplant; startet sobald nichts anderes läuft.'
    if c=='approve' and len(args)==2:return dumps(g.weights.approve(args[1])['status'])
    if c=='reject' and len(args)==2:return dumps(g.weights.reject(args[1])['status'])
    if c=='age':return dumps(g.age_evidence())
    if c=='slots':return dumps(g.slots.report())
    if c=='export' and len(args)==2:return 'Slot exportiert: '+g.slots.export_bundle(args[1],home=r.home)['path']
    if c=='tools':return dumps(g.tools.report())
    if c=='enable' and len(args)==2:g.tools.enable(args[1]);return 'Werkzeug erlaubt: '+args[1]
    if c=='calc' and len(args)>1:return dumps(g.tools.call('calc',{'expression':' '.join(args[1:])},origin='USER'))
    raise ValueError(operator_command.__doc__)
