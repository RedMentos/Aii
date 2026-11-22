"""G13 / §22.2.1 event and wake scheduler.

The scheduler is runtime infrastructure, not intelligence and not a fourth
body: it keeps a durable, bounded, prioritised queue of wake events and hands
the next permitted one to the coordinator. User turns keep their own durable
queue (store.accepted_turns) and always preempt background work; here they
only reset the idle clock. Rules, Age rights, quiet/idle policy and resource
limits stay binding for every background event.
"""
import time
from .common import uid,dumps

STATE_KEY='G13_EVENT_QUEUE'
REVISION='g13-event-scheduler-v1'
# Static priority classes (§22.2.1 order). Higher wins; ties: earlier due, then sequence.
PRIORITY={'USER_INPUT':100,'TOOL_EVENT':80,'RESOURCE_CHANGE':70,'TIMER':50,'GOAL_WAKE':40,'REPLAY_DUE':20,'IDLE':10}
FOREGROUND={'USER_INPUT','TOOL_EVENT','RESOURCE_CHANGE'}
ORIGINS={'USER','SYSTEM','SELF'}
# Background actions a wake event may start. Anything else is refused at post time.
ACTIONS={'sleep_full','wake_replay','sleep_a','sleep_b','sleep_c','notice',None}
# WP-AG growth actions (v13/agi): goal wakes, generality eval, weight-consolidation staging, practice.
ACTIONS|={'growth_goal','growth_eval','growth_consolidate','growth_practice','growth_teacher'}
ACTIONS|={'learn_medium','learn_slow'}  # WP-T10 §14.3/§14.4 learning timescales (authority.job)
# Age right needed when the event's origin is V13 itself (§17, age.RIGHTS).
SELF_RIGHTS={'GOAL_WAKE':'resume_open_goals','TIMER':'self_initiative','REPLAY_DUE':'own_sleep_planning','IDLE':'own_sleep_planning'}
MAX_PENDING=256
HISTORY=64
MAX_ATTEMPTS=3
RESOURCE_MODE={'NORMAL':'GREEN','RECOVERY':'GREEN','PRESSURE':'YELLOW','CRITICAL':'RED'}

def empty():return {'revision':REVISION,'sequence':0,'events':[],'history':[],'counters':{}}

class EventScheduler:
    def __init__(self,store,cfg,clock=time.time,age=None,key=STATE_KEY):
        self.s=store;self.cfg=cfg;self.clock=clock;self.age=age;self.key=key
    def _load(self):
        st,version=self.s.state(self.key,empty())
        if st.get('revision')!=REVISION:raise ValueError('Scheduler state revision mismatch')
        return st,version
    def _save(self,st,version):self.s.set_state(self.key,st,expected=version)
    def _count(self,st,name):st['counters'][name]=st['counters'].get(name,0)+1
    def recover(self):
        with self.s.mutex:return self._recover()
    def _recover(self):
        """Restart: events dispatched to a job that never completed become due again (bounded attempts)."""
        st,v=self._load();changed=0
        for e in st['events']:
            if e['status']=='DISPATCHED':
                changed+=1
                if e['attempts']>=MAX_ATTEMPTS:e['status']='FAILED';e['result']={'reason':'MAX_ATTEMPTS_AFTER_RESTART'}
                else:e['status']='PENDING'
        if changed:self._retire(st);self._save(st,v)
        return changed
    def post(self,kind,origin='SYSTEM',due=None,action=None,payload=None,dedup=None,ttl=None):
        with self.s.mutex:return self._post(kind,origin,due,action,payload,dedup,ttl)
    def _post(self,kind,origin='SYSTEM',due=None,action=None,payload=None,dedup=None,ttl=None):
        if kind not in PRIORITY:raise ValueError('Unbekannter Event-Typ: '+str(kind))
        if origin not in ORIGINS:raise ValueError('origin USER|SYSTEM|SELF')
        if action not in ACTIONS:raise ValueError('Unbekannte Scheduler-Aktion: '+str(action))
        dumps(payload or {})
        st,v=self._load();now=self.clock()
        if dedup and any(e['dedup']==dedup and e['status'] in {'PENDING','DISPATCHED','HELD_AGE'} for e in st['events']):
            self._count(st,'deduplicated');self._save(st,v);return None
        if sum(e['status'] in {'PENDING','HELD_AGE'} for e in st['events'])>=MAX_PENDING:
            # Bounded queue: the lowest-priority oldest background event is dropped, never a foreground one.
            victims=sorted((e for e in st['events'] if e['status'] in {'PENDING','HELD_AGE'} and e['kind'] not in FOREGROUND),key=lambda e:(PRIORITY[e['kind']],e['seq']))
            if not victims or PRIORITY[victims[0]['kind']]>PRIORITY[kind]:self._count(st,'refused_full');self._save(st,v);return None
            victims[0]['status']='DROPPED_CAPACITY';self._count(st,'dropped_capacity')
        st['sequence']+=1
        e={'id':uid('wake'),'seq':st['sequence'],'kind':kind,'origin':origin,'priority':PRIORITY[kind],'created':now,
           'due':now if due is None else float(due),'expires':None if ttl is None else now+float(ttl),'action':action,
           'payload':payload or {},'dedup':dedup,'status':'PENDING','attempts':0,'result':None}
        st['events'].append(e);self._count(st,'posted');self._retire(st);self._save(st,v)
        self.s.log('scheduler_post',None,{'kind':kind,'priority':e['priority']})
        return e['id']
    def _right(self,e,resource_state):
        """Age gate for SELF-originated wakes. USER and configured SYSTEM policy are not V13's own initiative."""
        if e['origin']!='SELF':return True
        right=SELF_RIGHTS.get(e['kind'])
        if not right:return False
        if self.age is None:return False  # no age controller: stage 0 conservative default, no self-initiative
        try:return self.age.may(right,resource_mode=RESOURCE_MODE.get(resource_state,'RED'))
        except Exception:return False
    def _allowed(self,e,idle,resource_state,quiet):
        if e['kind'] in FOREGROUND:return True
        if not idle:return False  # never block or interleave a live user turn
        if resource_state=='CRITICAL':return False
        if resource_state=='PRESSURE' and e['action'] not in {'sleep_c','notice'}:return False
        if quiet and e['origin']!='USER':return False
        if e['origin']!='USER' and e['action'] not in (None,'notice'):
            # WP-V5: :pause classes and the burn-out budget (activity decays without user input).
            from .inputs import background_blocked
            if background_blocked(self.s,e['action'],self.background_since_input()):return False
        return True
    def background_since_input(self):
        """Background dispatches since the last accepted user turn."""
        row=self.s.one('SELECT MAX(accepted_at) AS t FROM accepted_turns');last=row['t'] if row and row['t'] else 0.
        st,_=self._load()
        return sum(1 for e in st['events']+st['history'] if e['origin']!='USER' and e.get('action') not in (None,'notice')
                   and e['status'] in {'DISPATCHED','DONE','FAILED'} and e['created']>=last)
    def next(self,idle=True,resource_state='NORMAL',quiet=False):
        with self.s.mutex:return self._next(idle,resource_state,quiet)
    def _next(self,idle=True,resource_state='NORMAL',quiet=False):
        st,v=self._load();now=self.clock();changed=False;best=None
        for e in st['events']:
            if e['status'] not in {'PENDING','HELD_AGE'}:continue
            if e['expires'] is not None and e['expires']<now:e['status']='EXPIRED';changed=True;self._count(st,'expired');continue
            if e['due']>now:continue
            ok=self._right(e,resource_state)
            status='PENDING' if ok else 'HELD_AGE'
            if e['status']!=status:e['status']=status;changed=True
            if not ok or not self._allowed(e,idle,resource_state,quiet):continue
            if best is None or (e['priority'],-e['due'],-e['seq'])>(best['priority'],-best['due'],-best['seq']):best=e
        if best:
            best['status']='DISPATCHED';best['attempts']+=1;best['dispatched']=now;changed=True;self._count(st,'dispatched')
        if changed:self._retire(st);self._save(st,v)
        if best:self.s.log('scheduler_dispatch',None,{'kind':best['kind'],'priority':best['priority'],'resource_state':resource_state})
        return dict(best) if best else None
    def complete(self,event_id,status='DONE',result=None):
        with self.s.mutex:return self._complete(event_id,status,result)
    def _complete(self,event_id,status='DONE',result=None):
        if status not in {'DONE','FAILED','CANCELLED','RETRY'}:raise ValueError('status')
        st,v=self._load()
        for e in st['events']:
            if e['id']==event_id and e['status']=='DISPATCHED':
                e['result']=result
                if status in {'CANCELLED','RETRY'} and e['attempts']<MAX_ATTEMPTS:e['status']='PENDING'
                else:e['status']='FAILED' if status in {'CANCELLED','RETRY'} else status
                self._count(st,'completed_'+e['status'].lower());self._retire(st);self._save(st,v);return e['status']
        return None
    def _retire(self,st):
        done=[e for e in st['events'] if e['status'] not in {'PENDING','HELD_AGE','DISPATCHED'}]
        if done:
            st['history']=(st['history']+[{k:e[k] for k in ('id','kind','origin','action','status','created','attempts')} for e in done])[-HISTORY:]
            st['events']=[e for e in st['events'] if e['status'] in {'PENDING','HELD_AGE','DISPATCHED'}]
    def pending(self):return [dict(e) for e in self._load()[0]['events']]
    def report(self):
        st,v=self._load()
        return {'revision':REVISION,'state_version':v,'pending':[{k:e[k] for k in ('id','kind','origin','action','status','due','priority','attempts')} for e in st['events']],
                'history':st['history'][-16:],'counters':st['counters'],'priority_order':PRIORITY,
                'claim_limit':'Runtime wake queue only; no learned salience, no tool events exist at Age 0'}
