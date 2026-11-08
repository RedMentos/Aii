"""Incremental learning from V13's *committed* T8 digital action transitions.

This bridge is not a JEPA latent encoder. It learns an action-conditioned
numeric next-outcome prediction from the existing T8 provenance-checked feed.
No speculative outcomes are used as training labels.
"""
from pathlib import Path
import json
import os
import numpy as np
from . import world_model
from .continuous_predictor import OnlinePredictor

REVISION='v13-online-world-v1'

class OnlineWorld:
    def __init__(self,runtime,lr=0.02,replay=128):
        self.runtime=runtime
        self.home=Path(runtime.home)/'online_world'
        self.home.mkdir(parents=True,exist_ok=True)
        self.model=OnlinePredictor(7,len(world_model.ACTIONS),self.home,lr=lr,replay=replay)
        self.cursor=self.home/'cursor.json'
        self.last_id=None
        if self.cursor.exists():
            record=json.loads(self.cursor.read_text())
            if record.get('revision')!=REVISION or type(record.get('last_id')) not in (int,type(None)):
                raise ValueError('Incompatible online world cursor')
            self.last_id=record['last_id']

    @staticmethod
    def encode(row):
        state=np.asarray(row['s'],dtype=float)
        outcome=np.asarray(row['y'],dtype=float)
        action=world_model.ACTIONS.index(row['a'])
        if state.shape!=(4,) or outcome.shape!=(3,) or not np.isfinite(state).all() or not np.isfinite(outcome).all():
            raise ValueError('Invalid committed T8 transition')
        x=np.concatenate((state,np.zeros(3)))
        y=np.concatenate((state,outcome))
        return x,action,y

    def update(self,limit=2048):
        if type(limit) is not int or not 1<=limit<=world_model.MAX_ROWS:raise ValueError('Invalid update limit')
        rows=world_model.transitions(self.runtime.store,limit=limit)
        new=[]
        for row in rows:
            action_id=row['action_id']
            if type(action_id) is not int:raise ValueError('Invalid action identifier')
            if self.last_id is None or action_id>self.last_id:
                new.append(row)
        # Reject out-of-order records; otherwise cursor could skip observations.
        if any(a['action_id']>=b['action_id'] for a,b in zip(new,new[1:])):
            raise ValueError('Non-monotonic committed action stream')
        for row in new:
            x,a,y=self.encode(row)
            self.model.observe(x,a,y)
            # Commit learned weights BEFORE advancing the durable cursor.
            # An interrupted write may replay a sample; it must never silently skip it.
            self.model.checkpoint()
            self.last_id=row['action_id']
            temp=self.cursor.with_suffix('.tmp')
            temp.write_text(json.dumps({'revision':REVISION,'last_id':self.last_id}))
            os.replace(temp,self.cursor)
        return {'learned':len(new),'seen':self.model.seen,'last_id':self.last_id,
                'status':'LOCAL_ONLINE_PLASTICITY_NOT_FULL_JEPA'}

    def predict(self,state,action):
        if action not in world_model.ACTIONS:raise ValueError('Unknown route')
        s=np.asarray(state,dtype=float)
        if s.shape!=(4,) or not np.isfinite(s).all():raise ValueError('Invalid state')
        x=np.concatenate((s,np.zeros(3)))
        return self.model.predict(x,world_model.ACTIONS.index(action))[4:].tolist()
