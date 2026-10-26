"""WP-AG3 long-horizon goals: a persistent goal/plan store in F3 with subgoals, progress and wake-ups.

Goals outlive turns and restarts. Each goal has a status, optional parent, ordered plan steps,
progress, evidence refs and an optional wake time; wakes go through the G13 EventScheduler as
GOAL_WAKE events, so quiet hours, resources and Age rights apply. USER goals are the user's
own initiative; SELF goals (V13 sets its own) need Age right choose_learning_goals and their
wakes need resume_open_goals (Age 4) — at Age 0 they stay HELD_AGE. Plans can be scored by a
pluggable evaluator (later World-JEPA rollouts, AG2) before execution. Depth is bounded by the
Age budget focal_depth plus a hard ceiling.
"""
import math
import time
from .base import StateBox,age_allows,budget

KEY='G3_GOALS';REVISION='g3-goals-v1'
STATUS=('OPEN','ACTIVE','BLOCKED','DONE','ABANDONED')
OPEN={'OPEN','ACTIVE','BLOCKED'}
MAX_GOALS=256;MAX_DEPTH=6;MAX_STEPS=32

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
        steps=[str(x)[:300] for x in (steps or [])][:MAX_STEPS]
        def f(st):
            if sum(g['status'] in OPEN for g in st['goals'].values())>=MAX_GOALS:raise ValueError('Ziel-Speicher voll')
            if parent is not None:
                if parent not in st['goals']:raise ValueError('Unbekanntes Elternziel')
                limit=min(MAX_DEPTH,max(2,int(budget(self.age,'focal_depth',1))+1)) if origin!='USER' else MAX_DEPTH
                if self._depth(st,parent)+1>limit:raise ValueError(f'Zieltiefe > {limit}')
            st['seq']+=1;gid=f'goal_{st["seq"]}'
            st['goals'][gid]={'id':gid,'title':str(title)[:300],'origin':origin,'parent':parent,'status':'OPEN','progress':0.,
                'steps':[{'text':t,'done':False} for t in steps],'evidence':list(evidence or [])[:16],'created':self.clock(),
                'updated':self.clock(),'wake_at':wake_at,'deadline':deadline,'wake_event':None,'notes':[]}
            return gid
        gid=self.box.mutate(f)
        if wake_at is not None:self.schedule(gid,wake_at)
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
            g=st['goals'][gid];prior=g['status'];g['status']=status;g['updated']=self.clock()
            if note:g['notes']=(g['notes']+[str(note)[:300]])[-8:]
            if status=='DONE':g['progress']=1.
            elif status=='OPEN' and prior in {'DONE','ABANDONED'}:
                # Reopening is a new work cycle, not 100%-complete progress.
                # Keep prior steps, children and notes as historical evidence.
                g['progress']=0.
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
    def schedule(self,gid,wake_at):
        """Post a GOAL_WAKE; the scheduler applies idle/quiet/resource/Age rules at dispatch time."""
        g=self.get(gid)
        if self.scheduler is None:return None
        origin='USER' if g['origin']=='USER' else 'SELF'
        eid=self.scheduler.post('GOAL_WAKE',origin=origin,due=float(wake_at),action='growth_goal',payload={'goal_id':gid},dedup='goal:'+gid)
        def f(st):st['goals'][gid]['wake_event']=eid;st['goals'][gid]['wake_at']=float(wake_at)
        self.box.mutate(f);return eid
    def next_actionable(self,root_id=None):
        """Deepest open goal, oldest first; a wake may only inspect its own subtree."""
        st=self.box.load()[0];best=None
        def depth_in_scope(goal):
            if root_id is None:
                return self._depth(st,goal['id'])  # existing global operator view
            seen=set();current=goal['id'];depth=0
            while current is not None and current not in seen and depth<MAX_DEPTH:
                node=st['goals'].get(current)
                # No route through a blocked/closed ancestor or corrupt parent.
                if node is None or node['status'] not in {'OPEN','ACTIVE'}:return None
                depth+=1
                if current==root_id:return depth
                seen.add(current);current=node.get('parent')
            return None
        for g in st['goals'].values():
            if g['status'] not in {'OPEN','ACTIVE'}:continue
            depth=depth_in_scope(g)
            if depth is None:continue
            if any(c['parent']==g['id'] and c['status'] in OPEN for c in st['goals'].values()):continue
            step=next((i for i,s in enumerate(g['steps']) if not s['done']),None)
            key=(-depth,g['created'])
            if best is None or key<best[0]:best=(key,g,step)
        return None if best is None else {'goal':dict(best[1]),'step':best[2]}
    def score_plans(self,gid,plans,evaluator):
        """evaluator(goal, plan) -> {'value': float, 'risk': float}. Highest value-risk wins; nothing executes here."""
        g=self.get(gid);scored=[]
        for p in plans:
            r=evaluator(g,p) or {}
            if not isinstance(r,dict):raise ValueError('Invalid plan evaluation')
            raw_value,raw_risk=r.get('value',0.),r.get('risk',0.)
            if type(raw_value) not in (int,float) or type(raw_risk) not in (int,float):
                raise ValueError('Plan score must be a numeric value and risk')
            try:value,risk=float(raw_value),float(raw_risk)
            except (OverflowError,ValueError,TypeError) as exc:raise ValueError('Invalid plan score') from exc
            margin=value-risk
            if not all(math.isfinite(x) for x in (value,risk,margin)):
                raise ValueError('Nonfinite plan score or margin')
            scored.append((margin,{'plan':p,'value':value,'risk':risk}))
        # Stable ties preserve proposal order, not an arbitrary float/NaN ordering.
        return [row for _,row in sorted(scored,key=lambda x:x[0],reverse=True)]
    def on_wake(self,event):
        payload=event.get('payload')
        gid=payload.get('goal_id') if isinstance(payload,dict) else None
        if not isinstance(gid,str) or not gid:return {'status':'UNKNOWN_GOAL'}
        try:g=self.get(gid)
        except KeyError:return {'status':'UNKNOWN_GOAL'}
        if g['status'] not in OPEN:return {'status':'GOAL_CLOSED','goal_id':gid}
        if g['status']=='BLOCKED':return {'status':'GOAL_BLOCKED','goal_id':gid,'next':None}
        if g['status']=='OPEN':self.set_status(gid,'ACTIVE')
        nxt=self.next_actionable(root_id=gid)
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
