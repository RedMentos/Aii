"""Bounded persistent online action-conditioned predictor, independent of AG6 promotion.

This is a small real-gradient plasticity substrate, NOT a full World-JEPA or
permission to alter frozen GGUF weights. Every observe() updates live local
parameters; replay reduces overwriting; snapshots are atomic and recoverable.
"""
import os
import json
import shutil
from pathlib import Path
import numpy as np

REVISION='v13-online-predictor-v1'

class OnlinePredictor:
    def __init__(self,features,actions,home,lr=0.02,replay=128,seed=0):
        if not (type(features) is int and 1<=features<=512 and type(actions) is int and 1<=actions<=64):
            raise ValueError('Invalid predictor dimensions')
        if not (np.isfinite(lr) and 0<lr<=0.1 and type(replay) is int and 2<=replay<=4096):
            raise ValueError('Invalid learning configuration')
        self.d=features;self.a=actions;self.lr=float(lr);self.cap=replay
        self.path=Path(home)/'online_predictor.npz';self.rng=np.random.default_rng(seed)
        self.W=np.eye(features);self.U=np.zeros((actions,features));self.bias=np.zeros(features)
        self.x=np.zeros((0,features));self.act=np.zeros(0,dtype=np.int64);self.y=np.zeros((0,features))
        self.seen=0;self.updates=0;self.checkpoint_processed=None
        if self.path.exists():self.restore()

    def _check(self,x,action,y=None):
        x=np.asarray(x,dtype=np.float64)
        if x.shape!=(self.d,) or not np.isfinite(x).all() or np.max(np.abs(x))>1e6:
            raise ValueError('Invalid observation')
        if type(action) not in (int,np.int64) or not 0<=action<self.a:
            raise ValueError('Invalid action')
        if y is not None:
            y=np.asarray(y,dtype=np.float64)
            if y.shape!=(self.d,) or not np.isfinite(y).all() or np.max(np.abs(y))>1e6:
                raise ValueError('Invalid next observation')
        return x,y

    def predict(self,x,action):
        x,_=self._check(x,action)
        return x@self.W+self.U[action]+self.bias

    def error(self,examples):
        vals=[]
        for x,a,y in examples:
            x,y=self._check(x,a,y)
            vals.append(float(np.mean((self.predict(x,a)-y)**2)))
        if not vals:raise ValueError('Empty evaluation')
        return float(np.mean(vals))

    def observe(self,x,action,y,rehearsals=2):
        x,y=self._check(x,action,y)
        if type(rehearsals) is not int or not 0<=rehearsals<=8:raise ValueError('Invalid rehearsal count')
        # Reject pathological targets before any state mutation; gradients are
        # clipped, but a nonfinite result must never become a live parameter.
        if not np.isfinite(x@self.W+self.U[action]+self.bias).all():
            raise ValueError('Nonfinite predictor state')
        self.seen+=1
        if len(self.x)==self.cap:
            # Reservoir sampling: old observations remain represented as stream grows.
            index=int(self.rng.integers(0,self.seen))
            if index<self.cap:
                self.x[index]=x;self.act[index]=action;self.y[index]=y
        else:
            self.x=np.vstack((self.x,x));self.act=np.append(self.act,action);self.y=np.vstack((self.y,y))
        for i in range(rehearsals+1):
            if i==0:xx,aa,yy=x,action,y
            else:
                j=int(self.rng.integers(0,len(self.x)))
                xx,aa,yy=self.x[j],int(self.act[j]),self.y[j]
            residual=xx@self.W+self.U[aa]+self.bias-yy
            # Gradient clipping prevents unbounded single-step parameter changes.
            gW=np.outer(xx,residual);gU=residual;gb=residual
            # Norm via scaled hypot avoids overflow for large finite features.
            norm=float(np.linalg.norm(np.concatenate((gW.ravel(),gU,gb))))
            if not np.isfinite(norm):
                raise ValueError('Nonfinite online gradient')
            scale=min(1.,10./max(norm,1e-12))
            self.W-=self.lr*scale*gW;self.U[aa]-=self.lr*scale*gU;self.bias-=self.lr*scale*gb
            self.updates+=1
        return {'seen':self.seen,'updates':self.updates,'loss':float(np.mean((self.predict(x,action)-y)**2))}

    def learn_stream(self,transitions,checkpoint_every=32):
        """Consume observed numeric transitions without delaying local plasticity.

        The producer must supply grounded (x, action, next_x) observations;
        no speculative JEPA predictions are treated as target evidence.
        """
        if type(checkpoint_every) is not int or not 1<=checkpoint_every<=1024:
            raise ValueError('Invalid checkpoint cadence')
        count=0;last=None
        for x,action,next_x in transitions:
            last=self.observe(x,action,next_x)
            count+=1
            if count%checkpoint_every==0:self.checkpoint()
        if count%checkpoint_every:self.checkpoint()
        return {'observed':count,'last':last,'checkpoint':str(self.path) if count else None}

    def checkpoint(self, processed_ids=None):
        if processed_ids is not None and (not isinstance(processed_ids,list) or
            any(type(i) is not str or not i for i in processed_ids)):
            raise ValueError('Invalid committed transition identifiers')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temp=self.path.with_name(self.path.name+'.tmp.npz')
        try:
            np.savez_compressed(temp,revision=np.array(REVISION),dimensions=np.array([self.d,self.a,self.cap]),
                W=self.W,U=self.U,bias=self.bias,x=self.x,act=self.act,y=self.y,
                counters=np.array([self.seen,self.updates]),
                rng_state=np.array(json.dumps(self.rng.bit_generator.state)),
                processed_ids=np.array(json.dumps(processed_ids)) if processed_ids is not None else np.array('null'))
            if self.path.exists():
                shutil.copy2(self.path,self.path.with_suffix('.previous.npz'))
            os.replace(temp,self.path)
        finally:
            if temp.exists():temp.unlink()
        return str(self.path)

    def rollback(self):
        """Restore last committed snapshot; never overwrite current checkpoint on failure."""
        previous=self.path.with_suffix('.previous.npz')
        if not previous.exists():raise FileNotFoundError('No prior predictor checkpoint')
        current=self.path
        self.path=previous
        try:self.restore()
        finally:self.path=current
        return {'status':'ROLLED_BACK_IN_MEMORY','source':str(previous)}

    def restore(self):
        with np.load(self.path,allow_pickle=False) as data:
            if str(data['revision'])!=REVISION or not np.array_equal(data['dimensions'],[self.d,self.a,self.cap]):
                raise ValueError('Incompatible predictor checkpoint')
            shapes={'W':(self.d,self.d),'U':(self.a,self.d),'bias':(self.d,),
                    'x':(None,self.d),'act':(None,),'y':(None,self.d),'counters':(2,)}
            loaded={k:data[k].copy() for k in shapes}
            rng_state=json.loads(str(data['rng_state']))
            committed=json.loads(str(data['processed_ids'])) if 'processed_ids' in data else None
            if committed is not None and (not isinstance(committed,list) or any(type(i) is not str or not i for i in committed)):
                raise ValueError('Invalid committed transition identifiers')
        n=len(loaded['x'])
        if (n>self.cap or len(loaded['act'])!=n or len(loaded['y'])!=n
            or any(v.shape!=tuple(n if d is None else d for d in shapes[k]) for k,v in loaded.items())
            or any(not np.isfinite(v).all() for v in loaded.values())
            or np.any(loaded['act']<0) or np.any(loaded['act']>=self.a)
            or not np.all(loaded['counters']>=0)):
            raise ValueError('Invalid predictor checkpoint')
        for k in ('W','U','bias','x','act','y'):setattr(self,k,loaded[k])
        self.seen,self.updates=map(int,loaded['counters'])
        self.rng.bit_generator.state=rng_state
        self.checkpoint_processed=committed
