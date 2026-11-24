"""WP-AG3 long-horizon goals: a persistent goal/plan store in F3 with subgoals, progress and wake-ups.

Goals outlive turns and restarts. Each goal has a status, optional parent, ordered plan steps,
progress, evidence refs and an optional wake time; wakes go through the G13 EventScheduler as
GOAL_WAKE events, so quiet hours, resources and Age rights apply. USER goals are the user's
own initiative; SELF goals (V13 sets its own) need Age right choose_learning_goals and their
wakes need resume_open_goals (Age 4) — at Age 0 they stay HELD_AGE. Plans can be scored by a
pluggable evaluator (later World-JEPA rollouts, AG2) before execution. Goal-tree depth is a developmental planning right plus a hard ceiling,
not per-turn focal compute depth.
"""
import math
import time
from numbers import Real
from .base import StateBox,age_allows,learning_limit

KEY='G3_GOALS';REVISION='g3-goals-v1'
STATUS=('OPEN','ACTIVE','BLOCKED','DONE','ABANDONED')
OPEN={'OPEN','ACTIVE','BLOCKED'}
MAX_GOALS=256;MAX_DEPTH=6;MAX_STEPS=32


def _finite_wake_at(value):
    """Return a finite numeric scheduler timestamp before any goal mutation."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError("wake_at must be a finite numeric timestamp")
    try:
        due = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError("wake_at must be a finite numeric timestamp") from exc
    if not math.isfinite(due):
        raise ValueError("wake_at must be a finite numeric timestamp")
    return due


class GoalStore:
    def __init__(self,store,age=None,scheduler=None,clock=time.time):
        self.s=store;self.age=age;self.scheduler=scheduler;self.clock=clock
        self.box=StateBox(store,KEY,REVISION,lambda:{'goals':{},'seq':0})
    def _depth(self,st,gid):
        d=0
        while gid:d+=1;gid=st['goals'][gid]['parent']
        return d
    def add(self,title,origin='USER',parent=None,steps=None,wake_at=None,evidence=None,deadline=None):
        if origin not in ('USER','SYSTEM','SELF'):raise ValueError('origin')
        if origin=='SELF' and not age_allows(self.age,'choose_learning_goals','SELF'):raise PermissionError('Eigene Ziele erst ab Age-Recht choose_learning_goals')
        # Validate the timestamp before the first durable goal/sequence write.
        wake_due=None if wake_at is None else _finite_wake_at(wake_at)
        steps=[str(x)[:300] for x in (steps or [])][:MAX_STEPS]
        # Goal IDs and their wake event are one logical publication. The Store's
        # RLock prevents a scheduler worker from dispatching between the goal
        # row and the wake_event backlink.
        with self.s.mutex:
            before,_=self.box.load()
            old_seq=before['seq']
            def f(st):
                if sum(g['status'] in OPEN for g in st['goals'].values())>=MAX_GOALS:raise ValueError('Ziel-Speicher voll')
                if parent is not None:
                    if parent not in st['goals']:raise ValueError('Unbekanntes Elternziel')
                    limit=min(MAX_DEPTH,max(2,int(learning_limit(self.age,'goal_depth',1,capability='system'))+1)) if origin!='USER' else MAX_DEPTH
                    if self._depth(st,parent)+1>limit:raise ValueError(f'Zieltiefe > {limit}')
                st['seq']+=1;gid=f'goal_{st["seq"]}'
                st['goals'][gid]={'id':gid,'title':str(title)[:300],'origin':origin,'parent':parent,'status':'OPEN','progress':0.,
                    'steps':[{'text':t,'done':False} for t in steps],'evidence':list(evidence or [])[:16],'created':self.clock(),
                    'updated':self.clock(),'wake_at':wake_due,'deadline':deadline,'wake_event':None,'notes':[]}
                return gid
            gid=self.box.mutate(f)
            if wake_due is not None and self.scheduler is not None:
                try:
                    event_id=self.schedule(gid,wake_due)
                    if event_id is None:
                        raise RuntimeError('Goal wake could not be scheduled')
                except BaseException:
                    def rollback(st):
                        if gid in st['goals']:
                            del st['goals'][gid]
                        if st.get('seq')==old_seq+1:
                            st['seq']=old_seq
                    try:
                        self.box.mutate(rollback)
                    except BaseException as rollback_error:
                        raise RuntimeError('Goal wake publication failed and goal rollback could not be confirmed') from rollback_error
                    raise
        return gid
    def decompose(self,gid,subgoals,origin=None):
        g=self.get(gid);origin=origin or g['origin']
        return [self.add(t,origin,parent=gid) for t in subgoals]
    def step_done(self,gid,index,evidence=None):
        def f(st):
            g=st['goals'][gid];g['steps'][index]['done']=True
            if evidence:g['evidence']=(g['evidence']+[evidence])[-16:]
            self._recompute(st,gid)
        self.box.mutate(f);return self.get(gid)
    def set_status(self,gid,status,note=None):
        if status not in STATUS:raise ValueError('Status '+'|'.join(STATUS))
        def f(st):
            g=st['goals'][gid];g['status']=status;g['updated']=self.clock()
            if note:g['notes']=(g['notes']+[str(note)[:300]])[-8:]
            if status=='DONE':g['progress']=1.
            if g['parent']:self._recompute(st,g['parent'])
        self.box.mutate(f);return self.get(gid)
    def _recompute(self,st,gid):
        """Progress = mean over own plan steps and child goals; a goal whose parts are all done becomes DONE."""
        g=st['goals'][gid];kids=[c for c in st['goals'].values() if c['parent']==gid and c['status']!='ABANDONED']
        parts=[1. if s['done'] else 0. for s in g['steps']]+[c['progress'] for c in kids]
        if parts:g['progress']=round(sum(parts)/len(parts),4)
        if parts and g['progress']>=1. and g['status'] in OPEN:g['status']='DONE'
        g['updated']=self.clock()
        if g['parent']:self._recompute(st,g['parent'])
    def _cancel_pending_dedup(self,dedup):
        pending=getattr(self.scheduler,'pending',None)
        cancel=getattr(self.scheduler,'cancel_pending',None)
        if not callable(pending) or not callable(cancel):
            return
        for event in pending():
            if event.get('dedup')==dedup and event.get('status') in {'PENDING','HELD_AGE'}:
                if not cancel(event['id']):
                    raise RuntimeError('Goal wake cleanup could not be confirmed')

    def schedule(self,gid,wake_at):
        """Post a finite GOAL_WAKE and persist its event backlink without orphaning either side."""
        due=_finite_wake_at(wake_at)
        if self.scheduler is None:return None
        with self.s.mutex:
            g=self.get(gid)
            origin='USER' if g['origin']=='USER' else 'SELF'
            dedup='goal:'+gid
            try:
                eid=self.scheduler.post('GOAL_WAKE',origin=origin,due=due,action='growth_goal',payload={'goal_id':gid},dedup=dedup)
            except BaseException:
                # EventScheduler may have committed the queue row before a later
                # telemetry write raises. Remove only this exact pending wake.
                self._cancel_pending_dedup(dedup)
                raise
            if eid is None:
                existing=next((event for event in self.scheduler.pending()
                               if event.get('dedup')==dedup
                               and event.get('status') in {'PENDING','HELD_AGE','DISPATCHED'}),None)
                if existing is None:return None
                eid=existing['id']
            try:
                def f(st):
                    goal=st['goals'].get(gid)
                    if goal is None:raise KeyError(gid)
                    goal['wake_event']=eid
                    goal['wake_at']=due
                self.box.mutate(f)
            except BaseException:
                if not self.scheduler.cancel_pending(eid):
                    raise RuntimeError('Goal wake could not be cancelled after goal state write failure')
                raise
            return eid
    def next_actionable(self):
        """Deepest open goal with an open step, oldest first: what a woken plan should work on."""
        st=self.box.load()[0];best=None
        for g in st['goals'].values():
            if g['status'] not in {'OPEN','ACTIVE'}:continue
            if any(c['parent']==g['id'] and c['status'] in OPEN for c in st['goals'].values()):continue
            step=next((i for i,s in enumerate(g['steps']) if not s['done']),None)
            key=(-self._depth(st,g['id']),g['created'])
            if best is None or key<best[0]:best=(key,g,step)
        return None if best is None else {'goal':dict(best[1]),'step':best[2]}
    def score_plans(self,gid,plans,evaluator):
        """evaluator(goal, plan) -> {'value': float, 'risk': float}. Highest value-risk wins; nothing executes here."""
        g=self.get(gid);scored=[]
        for p in plans:
            r=evaluator(g,p) or {};scored.append({'plan':p,'value':float(r.get('value',0.)),'risk':float(r.get('risk',0.))})
        return sorted(scored,key=lambda x:x['value']-x['risk'],reverse=True)
    def on_wake(self,event):
        gid=(event.get('payload') or {}).get('goal_id')
        try:g=self.get(gid)
        except KeyError:return {'status':'UNKNOWN_GOAL'}
        if g['status'] not in OPEN:return {'status':'GOAL_CLOSED','goal_id':gid}
        if g['status']=='OPEN':self.set_status(gid,'ACTIVE')
        nxt=self.next_actionable()
        return {'status':'WOKEN','goal_id':gid,'next':nxt and {'goal_id':nxt['goal']['id'],'step':nxt['step']}}
    def get(self,gid):
        g=self.box.load()[0]['goals'].get(gid)
        if g is None:raise KeyError(gid)
        return g
    def tree(self,status=None):
        st=self.box.load()[0]
        return [g for g in st['goals'].values() if status is None or g['status'] in ({status} if isinstance(status,str) else status)]
    def report(self):
        gs=self.tree()
        return {'revision':REVISION,'open':sum(g['status'] in OPEN for g in gs),'done':sum(g['status']=='DONE' for g in gs),
                'self_goals_allowed':age_allows(self.age,'choose_learning_goals','SELF'),'next':self.next_actionable(),
                'claim_limit':'Persistent goal tree and wakes; no learned planner, plan scoring needs a world model (AG2)'}
