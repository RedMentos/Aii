"""Incremental learning from V13's committed T8 digital action transitions.

The predictor parameters and consumed action IDs share one atomic checkpoint.
This prevents a restart between weight persistence and cursor persistence from
applying the same transition twice. It remains a small local predictor, not
full JEPA or pretrained GGUF weight training.
"""
from contextlib import contextmanager
from pathlib import Path
import fcntl
import json
import os
import stat
import numpy as np
from . import world_model
from .continuous_predictor import OnlinePredictor

REVISION='v13-online-world-v2'
CHECKPOINT_SCHEMA='v13.online-world-checkpoint/2'


class OnlineWorld:
    def __init__(self,runtime,lr=0.02,replay=128):
        self.runtime=runtime
        self.home=Path(runtime.home)/'online_world'
        self.home.mkdir(parents=True,exist_ok=True)
        self.model=OnlinePredictor(7,len(world_model.ACTIONS),self.home,lr=lr,replay=replay)
        self.cursor=self.home/'cursor.json'  # read-only legacy migration source
        self.lock_path=self.home/'online_world.lock'
        with self._state_lock():
            if self.model.path.exists():
                self.model.restore()
            else:
                self.model.checkpoint(metadata={'schema':CHECKPOINT_SCHEMA,'processed_ids':[]})
            stored=self._checkpoint_ids()
            legacy=self._legacy_ids()
            merged=list(dict.fromkeys(stored+legacy))[-world_model.MAX_ROWS:]
            if merged!=stored:
                metadata=dict(self.model.metadata)
                metadata.update(schema=CHECKPOINT_SCHEMA,processed_ids=merged)
                self.model.checkpoint(metadata=metadata)
            self.processed=merged

    @contextmanager
    def _state_lock(self):
        flags=os.O_CREAT|os.O_RDWR|getattr(os,'O_NOFOLLOW',0)
        fd=os.open(self.lock_path,flags,0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError('Online-world lock is not a regular file')
            os.fchmod(fd,0o600)
            fcntl.flock(fd,fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(fd,fcntl.LOCK_UN)
            finally:
                os.close(fd)

    @staticmethod
    def _validate_ids(ids):
        if (type(ids) is not list or len(ids)>world_model.MAX_ROWS
                or any(type(i) is not str or not i for i in ids)):
            raise ValueError('Incompatible online world checkpoint IDs')
        if len(set(ids))!=len(ids):
            raise ValueError('Duplicate online world checkpoint IDs')
        return ids

    def _checkpoint_ids(self):
        metadata=self.model.metadata
        if type(metadata) is not dict:
            raise ValueError('Invalid online world checkpoint metadata')
        schema=metadata.get('schema')
        if schema not in (None,CHECKPOINT_SCHEMA):
            raise ValueError('Incompatible online world checkpoint schema')
        return list(self._validate_ids(metadata.get('processed_ids',[])))

    def _legacy_ids(self):
        if not self.cursor.exists():
            return []
        record=json.loads(self.cursor.read_text())
        if type(record) is not dict:
            raise ValueError('Incompatible legacy online world cursor')
        ids=record.get('processed')
        if (record.get('revision')!='v13-online-world-v1' or type(ids) is not list
                or len(ids)>world_model.MAX_ROWS
                or any(type(i) is not str or not i for i in ids)):
            raise ValueError('Incompatible legacy online world cursor')
        return list(dict.fromkeys(ids))

    @staticmethod
    def encode(row):
        state=np.asarray(row['s'],dtype=float)
        outcome=np.asarray(row['y'],dtype=float)
        action=world_model.ACTIONS.index(row['a'])
        if (state.shape!=(4,) or outcome.shape!=(3,)
                or not np.isfinite(state).all() or not np.isfinite(outcome).all()):
            raise ValueError('Invalid committed T8 transition')
        x=np.concatenate((state,np.zeros(3)))
        y=np.concatenate((state,outcome))
        return x,action,y

    def update(self,limit=2048):
        if type(limit) is not int or not 1<=limit<=world_model.MAX_ROWS:
            raise ValueError('Invalid update limit')
        with self._state_lock():
            # A second Runtime/process may have committed since this instance
            # was created. Reload parameters and action IDs inside the lock.
            self.model.restore()
            self.processed=self._checkpoint_ids()
            rows=world_model.transitions(self.runtime.store,limit=limit)
            already=set(self.processed)
            new=[]
            for row in rows:
                action_id=row['action_id']
                if type(action_id) is not str or not action_id:
                    raise ValueError('Invalid action identifier')
                if action_id not in already:
                    new.append(row)
                    already.add(action_id)
            replay=[(x.copy(),int(a),y.copy())
                    for x,a,y in zip(self.model.x,self.model.act,self.model.y)]
            retention_before=self.model.error(replay) if replay else None
            learned=0
            for row in new:
                x,a,y=self.encode(row)
                action_id=row['action_id']
                try:
                    self.model.observe(x,a,y)
                    next_ids=(self.processed+[action_id])[-world_model.MAX_ROWS:]
                    metadata=dict(self.model.metadata)
                    metadata.update(schema=CHECKPOINT_SCHEMA,processed_ids=next_ids)
                    self.model.checkpoint(metadata=metadata)
                except Exception:
                    # If observe/checkpoint failed before atomic replace, discard
                    # its in-memory mutation. If replace already happened before
                    # a later fsync error, the same checkpoint contains action_id
                    # and is treated as committed rather than learned twice.
                    self.model.restore()
                    self.processed=self._checkpoint_ids()
                    if action_id in self.processed:
                        learned+=1
                        continue
                    raise
                self.processed=next_ids
                learned+=1
            retention_after=self.model.error(replay) if replay else None
            return {'learned':learned,'seen':self.model.seen,'tracked_ids':len(self.processed),
                    'old_replay_loss_before':retention_before,'old_replay_loss_after':retention_after,
                    'old_replay_loss_delta':None if not replay else retention_after-retention_before,
                    'status':'LOCAL_ONLINE_PLASTICITY_NOT_FULL_JEPA'}

    def predict(self,state,action):
        if action not in world_model.ACTIONS:
            raise ValueError('Unknown route')
        s=np.asarray(state,dtype=float)
        if s.shape!=(4,) or not np.isfinite(s).all():
            raise ValueError('Invalid state')
        x=np.concatenate((s,np.zeros(3)))
        return self.model.predict(x,world_model.ACTIONS.index(action))[4:].tolist()
