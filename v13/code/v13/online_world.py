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
        self.processed=[]
        if self.model.checkpoint_processed is not None:
            ids=self.model.checkpoint_processed
            if len(ids)>world_model.MAX_ROWS or len(set(ids))!=len(ids):
                raise ValueError('Invalid predictor-bound T8 cursor')
            self.processed=list(ids)
        elif self.cursor.exists():
            record=json.loads(self.cursor.read_text())
            ids=record.get('processed')
            if record.get('revision')!=REVISION or not isinstance(ids,list) or len(ids)>world_model.MAX_ROWS or any(type(i) is not str for i in ids):
                raise ValueError('Incompatible online world cursor')
            self.processed=ids

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
        already=set(self.processed)
        new=[]
        for row in rows:
            action_id=row['action_id']
            if type(action_id) is not str or not action_id:
                raise ValueError('Invalid action identifier')
            if action_id not in already:
                new.append(row)
                already.add(action_id)
        # Track old-experience error separately from fresh-sample loss.
        replay=[(x.copy(),int(a),y.copy()) for x,a,y in zip(self.model.x,self.model.act,self.model.y)]
        retention_before=self.model.error(replay) if replay else None
        for row in new:
            x,a,y=self.encode(row)
            self.model.observe(x,a,y)
            next_ids=(self.processed+[row['action_id']])[-world_model.MAX_ROWS:]
            # Publish weights, replay, RNG and T8 cursor in ONE atomic NPZ.
            # A crash before os.replace replays the whole transition; a crash
            # afterwards restores both the learned weights and its identifier.
            try:
                self.model.checkpoint(processed_ids=next_ids)
            except Exception:
                # observe() already mutated RAM. Rehydrate from the last
                # committed snapshot so retry cannot double-train the row.
                # If no checkpoint exists, return to the fresh initial model.
                self.model=OnlinePredictor(7,len(world_model.ACTIONS),self.home,
                    lr=self.model.lr,replay=self.model.cap)
                raise
            self.processed=next_ids
        retention_after=self.model.error(replay) if replay else None
        return {'learned':len(new),'seen':self.model.seen,'tracked_ids':len(self.processed),
                'old_replay_loss_before':retention_before,'old_replay_loss_after':retention_after,
                'old_replay_loss_delta':None if not replay else retention_after-retention_before,
                'status':'LOCAL_ONLINE_PLASTICITY_NOT_FULL_JEPA'}

    def predict(self,state,action):
        if action not in world_model.ACTIONS:raise ValueError('Unknown route')
        s=np.asarray(state,dtype=float)
        if s.shape!=(4,) or not np.isfinite(s).all():raise ValueError('Invalid state')
        x=np.concatenate((s,np.zeros(3)))
        return self.model.predict(x,world_model.ACTIONS.index(action))[4:].tolist()
