"""Experimental persistent numeric temporal readout; NOT full JEPA or GGUF training."""
import json, math, os, tempfile
from pathlib import Path

class TemporalReadout:
    def __init__(self, path, learning_enabled=False, rate=.1, decay=.95):
        self.path=Path(path); self.learning_enabled=learning_enabled
        if not 0 < rate <= .5 or not 0 <= decay < 1: raise ValueError("bounds")
        self.rate=rate; self.decay=decay
        self.weights={k:0. for k in ("WORLD","B1","B2")}
        self.ema=dict(self.weights); self.seen=[]
        if self.path.exists():
            d=json.loads(self.path.read_text())
            if d.get("schema")!=1 or set(d["weights"])!=set(self.weights) or set(d["ema"])!=set(self.weights): raise ValueError("schema")
            if not all(isinstance(v,(int,float)) and math.isfinite(v) and abs(v)<=4 for v in list(d["weights"].values())+list(d["ema"].values())): raise ValueError("weights")
            if not isinstance(d["seen"],list) or not all(isinstance(v,str) for v in d["seen"]): raise ValueError("seen")
            self.weights,self.ema,self.seen=d["weights"],d["ema"],d["seen"]
    def read(self, role, target=False):
        return 1/(1+math.exp(-(self.ema if target else self.weights)[role]))
    def update(self, intent, event_id, authorized=False):
        if not self.learning_enabled or not authorized: raise PermissionError("learning gate")
        if not isinstance(event_id,str) or not event_id or event_id in self.seen: raise ValueError("event id")
        if not isinstance(intent,dict) or intent.get("target")!="WORLD_TEMPORAL" or intent.get("requires_optimizer_permission") is not True: raise ValueError("intent")
        if not all(isinstance(intent.get(k),str) and intent[k].startswith("T8:") and len(intent[k])>3 for k in ("source","evidence")): raise ValueError("provenance")
        err=intent.get("prediction_error")
        if not isinstance(err,(int,float)) or not math.isfinite(err) or abs(err)>1: raise ValueError("error")
        before=(dict(self.weights),dict(self.ema),list(self.seen))
        for role,scale in (("WORLD",1.),("B1",.6),("B2",.3)):
            self.weights[role]=max(-4.,min(4.,self.weights[role]+self.rate*err*scale))
            self.ema[role]=self.decay*self.ema[role]+(1-self.decay)*self.weights[role]
        self.seen.append(event_id)
        try: self.save()
        except Exception:
            self.weights,self.ema,self.seen=before
            raise
        return {k:self.weights[k]-before[0][k] for k in self.weights}
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(dir=self.path.parent,prefix=".temporal-")
        try:
            with os.fdopen(fd,"w") as f:
                json.dump({"schema":1,"weights":self.weights,"ema":self.ema,"seen":self.seen},f)
                f.flush(); os.fsync(f.fileno())
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
    def rollback(self, snapshot):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(dir=self.path.parent,prefix=".rollback-")
        try:
            with os.fdopen(fd,"wb") as f:
                f.write(snapshot); f.flush(); os.fsync(f.fileno())
            TemporalReadout(tmp)
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
        self.__init__(self.path,self.learning_enabled,self.rate,self.decay)
