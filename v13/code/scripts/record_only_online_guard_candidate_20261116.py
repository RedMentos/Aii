"""Hash-bound review candidate for RAW OnlineWorld learning control.

Only produces replacement bytes for a private copy. No deployment, model download,
GGUF update, authority promotion or Redmi inference is performed by this builder.
The underlying two-file predictor/cursor publication is not crash-atomic; this
candidate detects a torn cursor and refuses further learning instead of replaying.
"""
from hashlib import sha256
from pathlib import Path

SOURCE_SHA256 = {
    'v13/runtime.py': 'a533660776f7e2b1697e9793a3abb811eb6d1e7191ec6fe0af523d58efa0ce38',
    'v13/online_world.py': 'ebd6044651ccd031c947a2e8d0d188232c2bab2da79b19ea6c513c433d59e8c8',
    'v13/agi/__init__.py': '75333b385dbc2d581e8fc028b433b0a93847dc80b64f83d9aedf104cc45c8661',
    'v13/operator.py': 'b81aa415acd3c2e6fe4c63de538719872976e4cff6dc532d434918a0fac57186',
}

RUNTIME_OLD = b'''    def online_world_update(self,limit=2048):
        """Explicit bounded online learning from committed T8 transitions.

        The predictor is local and never modifies pretrained GGUF weights.
        No model is initialized until the operator invokes this entrypoint.
        """
        from .online_world import OnlineWorld
        if not hasattr(self,'_online_world'):
            self._online_world=OnlineWorld(self)
        return self._online_world.update(limit=limit)
'''
RUNTIME_NEW = b'''    def online_world_update(self,limit=2048,authority='SYSTEM'):
        """Gate both automatic and operator-invoked local predictor updates."""
        if authority not in ('SYSTEM','EXPLICIT_HUMAN'):raise ValueError('Invalid authority')
        mode=self.cfg.get('learning_mode')
        if mode not in ('SHADOW_UPDATE','APPROVED_COMMIT'):
            return {'status':'SKIPPED_'+('RECORD_ONLY' if mode=='RECORD_ONLY' else 'INVALID_LEARNING_MODE'),'learned':0}
        from .online_world import OnlineWorld,blocked,skipped
        with self.lock:
            with self.store.mutex:
                reason=blocked(self,authority)
                if reason:return skipped(reason)
                if authority=='EXPLICIT_HUMAN':self.require_idle()
                if not hasattr(self,'_online_world'):self._online_world=OnlineWorld(self)
                world=self._online_world
        return world.update(limit=limit,authority=authority)
'''

POLICY = b'''\n# The same local opt-in state is used by the reviewed staged policy.
POLICY_KEY='ONLINE_WORLD_POLICY_V1'
POLICY_REVISION='online-world-policy-v1'
HUMAN='EXPLICIT_HUMAN'


def enabled(store):
    state,_=store.state(POLICY_KEY,None)
    if state is None:return False
    if (not isinstance(state,dict) or set(state)!={'revision','enabled'}
            or state['revision']!=POLICY_REVISION or type(state['enabled']) is not bool):
        raise ValueError('Invalid online world policy')
    return state['enabled']


def set_enabled(runtime,value):
    if type(value) is not bool:raise ValueError('Expected boolean')
    with runtime.lock:
        with runtime.store.mutex:
            _,version=runtime.store.state(POLICY_KEY,None)
            runtime.store.set_state(POLICY_KEY,{'revision':POLICY_REVISION,'enabled':value},expected=version)
    return value


def blocked(runtime,authority='SYSTEM'):
    if authority not in ('SYSTEM',HUMAN):raise ValueError('Invalid authority')
    mode=runtime.cfg.get('learning_mode')
    if mode=='RECORD_ONLY':return 'RECORD_ONLY'
    if mode not in ('SHADOW_UPDATE','APPROVED_COMMIT'):return 'INVALID_LEARNING_MODE'
    if authority=='SYSTEM' and not enabled(runtime.store):return 'OFF'
    from .inputs import paused
    if paused(runtime.store,'training'):return 'PAUSED_TRAINING'
    if runtime.paused or runtime.stop.is_set() or runtime.cancel_event.is_set():return 'PAUSED_OR_CANCELLED'
    if runtime.store.queue_stats()['count'] or not runtime.jobs.empty():return 'USER_OR_JOB_WAITING'
    from . import age,resource_modes
    if runtime.guard.state!='NORMAL' or not resource_modes.allows(runtime.guard.mode,'shadow_learning'):return 'RESOURCES'
    if not age.controller(runtime).may('small_shadow_update',resource_mode=runtime.guard.mode):return 'AGE_RIGHT'
    return None


def skipped(reason,learned=0):
    return {'status':'SKIPPED_'+reason,'learned':learned,
            'claim_limit':'Local numeric predictor; no GGUF update or JEPA proof'}


def policy_status(runtime):
    with runtime.lock:
        with runtime.store.mutex:
            reason=blocked(runtime,'SYSTEM')
            return {'enabled':enabled(runtime.store),'learning_mode':runtime.cfg.get('learning_mode'),
                    'automatic_ready':reason is None,'blocked_reason':reason,
                    'claim_limit':'Local predictor; cursor and checkpoint are separately published'}
'''

UPDATE_START = b'    def update(self,limit=2048):\n'
UPDATE_END = b'    def predict(self,state,action):\n'
UPDATE = b'''    def update(self,limit=2048,authority='SYSTEM'):
        """Gate each step and detect a torn predictor/cursor before any update."""
        import threading
        with self.runtime.lock:
            if not hasattr(self.runtime,'_online_world_update_lock'):
                self.runtime._online_world_update_lock=threading.Lock()
            guard=self.runtime._online_world_update_lock
        if not guard.acquire(blocking=False):return skipped('UPDATE_BUSY')
        try:return self._guarded_update(limit,authority)
        finally:guard.release()

    def _guarded_update(self,limit,authority):
        from copy import deepcopy
        if type(limit) is not int or not 1<=limit<=world_model.MAX_ROWS:raise ValueError('Invalid update limit')
        # Runtime lock serializes distinct OnlineWorld instances, source pause
        # changes, explicit enablement and operator mode changes for each step.
        with self.runtime.lock:
            with self.runtime.store.mutex:
                reason=blocked(self.runtime,authority)
                if reason:return skipped(reason)
                if authority==HUMAN:self.runtime.require_idle()
                current=getattr(self.runtime,'_online_world',None)
                if current is not None and current is not self:return skipped('STALE_INSTANCE')
                self.runtime._online_world=self
                if (getattr(self,'_guard_torn',False) or self.model.seen!=len(self.processed)
                        or len(set(self.processed))!=len(self.processed)):return skipped('TORN_OR_BOUNDED_CURSOR')
        rows=world_model.transitions(self.runtime.store,limit=limit)
        replay=[(x.copy(),int(a),y.copy()) for x,a,y in zip(self.model.x,self.model.act,self.model.y)]
        retention_before=self.model.error(replay) if replay else None
        learned=0
        for row in rows:
            with self.runtime.lock:
                with self.runtime.store.mutex:
                    reason=blocked(self.runtime,authority)
                    if reason:return skipped(reason,learned)
                    if (getattr(self,'_guard_torn',False) or self.model.seen!=len(self.processed)
                            or len(set(self.processed))!=len(self.processed)):return skipped('TORN_OR_BOUNDED_CURSOR',learned)
                    action_id=row['action_id']
                    if type(action_id) is not str or not action_id:raise ValueError('Invalid action identifier')
                    if action_id in self.processed:continue
                    # Do not silently forget old IDs when the legacy cursor reaches its bound.
                    if len(self.processed)>=world_model.MAX_ROWS:return skipped('CURSOR_LIMIT',learned)
                    x,a,y=self.encode(row)
                    names=('W','U','bias','x','act','y')
                    model=self.model
                    old={name:getattr(model,name).copy() for name in names}
                    old.update(seen=model.seen,updates=model.updates,rng=deepcopy(model.rng.bit_generator.state))
                    try:
                        model.observe(x,a,y)
                        # A reentrant stop must not leave an in-memory update.
                        reason=blocked(self.runtime,authority)
                        if reason:
                            for name in names:setattr(model,name,old[name])
                            model.seen=old['seen'];model.updates=old['updates'];model.rng.bit_generator.state=old['rng']
                            return skipped(reason,learned)
                        # Any failure while publishing the pair is ambiguous;
                        # require recovery/restart even if the first file may
                        # already have reached disk before an exception.
                        self._guard_torn=True
                        model.checkpoint()
                    except BaseException:
                        for name in names:setattr(model,name,old[name])
                        model.seen=old['seen'];model.updates=old['updates'];model.rng.bit_generator.state=old['rng']
                        raise
                    # Publication of these two files is not atomic. Keep the
                    # old cursor in memory until its replace succeeds so that
                    # a failed cursor write blocks the next update as torn.
                    processed=self.processed+[action_id]
                    temp=self.cursor.with_suffix('.tmp')
                    temp.write_text(json.dumps({'revision':REVISION,'processed':processed}))
                    os.replace(temp,self.cursor)
                    self.processed=processed;self._guard_torn=False;learned+=1
        retention_after=self.model.error(replay) if replay else None
        return {'learned':learned,'seen':self.model.seen,'tracked_ids':len(self.processed),
                'old_replay_loss_before':retention_before,'old_replay_loss_after':retention_after,
                'old_replay_loss_delta':None if not replay else retention_after-retention_before,
                'status':'LOCAL_ONLINE_PLASTICITY_NOT_FULL_JEPA'}

'''

AGI_OLD = b'''    if args and args[0]=='onlineworld':
        if len(args)>2:raise ValueError('Usage: :growth onlineworld [LIMIT]')
        limit=int(args[1]) if len(args)==2 else 2048
        return dumps(r.online_world_update(limit=limit))
'''
AGI_NEW = b'''    if args and args[0]=='onlineworld':
        from ..online_world import set_enabled,policy_status,HUMAN
        if args in (['onlineworld'],['onlineworld','status']):return dumps(policy_status(r))
        if args in (['onlineworld','on'],['onlineworld','off']):
            set_enabled(r,args[1]=='on');return dumps(policy_status(r))
        if len(args)==2 and args[1].isdigit():return dumps(r.online_world_update(limit=int(args[1]),authority=HUMAN))
        if len(args) in (2,3) and args[1]=='run':
            return dumps(r.online_world_update(limit=int(args[2]) if len(args)==3 else 64,authority=HUMAN))
        raise ValueError('Usage: :growth onlineworld [status|on|off|run [LIMIT]|LIMIT]')
'''

OPERATOR_OLD = b"            cfg=r.cfg|{key:value};save_config(r.home,cfg);r.cfg.update(cfg);return key+' = '+value\n"
OPERATOR_NEW = b'''            # Mode switches serialize with each local predictor step.
            with r.lock:
                cfg=r.cfg|{key:value};save_config(r.home,cfg);r.cfg.update(cfg)
            return key+' = '+value
'''


def _replace(raw, old, new, label):
    if raw.count(old) != 1:
        raise ValueError('online-world guard anchor mismatch: ' + label)
    return raw.replace(old, new, 1)


def build_sources(code_dir):
    """Validate every frozen input, return replacement bytes; no files are written."""
    code_dir = Path(code_dir)
    result = {}
    for relative, expected in SOURCE_SHA256.items():
        path = code_dir / relative
        parts=Path(relative).parts
        # Reject links within the supplied source tree. Android commonly uses
        # an alias in an ancestor such as /data/data; that is not an input path
        # controlled by this builder and must not break an otherwise valid root.
        internal=(code_dir.joinpath(*parts[:i]) for i in range(1,len(parts)+1))
        if code_dir.is_symlink() or not path.is_file() or any(p.is_symlink() for p in internal):
            raise ValueError('online-world guard source path missing or unsafe: ' + relative)
        raw = path.read_bytes()
        if sha256(raw).hexdigest() != expected:
            raise ValueError('online-world guard source hash mismatch: ' + relative)
        result[relative] = raw
    result['v13/runtime.py'] = _replace(result['v13/runtime.py'], RUNTIME_OLD, RUNTIME_NEW, 'runtime')
    world = _replace(result['v13/online_world.py'], b"REVISION='v13-online-world-v1'\n", b"REVISION='v13-online-world-v1'\n" + POLICY, 'policy')
    if world.count(UPDATE_START)!=1 or world.count(UPDATE_END)!=1:
        raise ValueError('online-world guard anchor mismatch: update')
    a = world.index(UPDATE_START); b = world.index(UPDATE_END,a)
    result['v13/online_world.py'] = world[:a] + UPDATE + world[b:]
    result['v13/agi/__init__.py'] = _replace(result['v13/agi/__init__.py'], AGI_OLD, AGI_NEW, 'operator command')
    result['v13/operator.py'] = _replace(result['v13/operator.py'], OPERATOR_OLD, OPERATOR_NEW, 'learning mode lock')
    for name, raw in result.items():compile(raw,name,'exec')
    return result
