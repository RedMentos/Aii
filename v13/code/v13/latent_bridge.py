"""Bounded numeric cross-organ projector. Experimental, NOT GGUF KV injection."""
import hashlib,json,math
SCHEMA="v13.latent-bridge/1"
def vec(v,n):
    if not isinstance(v,(tuple,list)) or len(v)!=n or not all(type(x) in (int,float) and math.isfinite(x) and abs(x)<1e6 for x in v):
        raise ValueError("invalid vector")
    return [float(x) for x in v]
class Projector:
    def __init__(self,source,target,ni,no,rate=.02):
        if not source or not target or not 1<=ni<=256 or not 1<=no<=256 or not 0<rate<=.1:raise ValueError("geometry")
        self.source,self.target,self.ni,self.no,self.rate=source,target,ni,no,rate
        self.w=[[0.]*ni for _ in range(no)];self.steps=0
    def revision(self):
        return hashlib.sha256(json.dumps(self.w,allow_nan=False).encode()).hexdigest()
    def project(self,x,source_id,generation):
        if not source_id or not generation:raise ValueError("missing provenance")
        x=vec(x,self.ni)
        return dict(schema=SCHEMA,source=self.source,target=self.target,source_id=source_id,generation=generation,revision=self.revision(),steps=self.steps,authority="EXPERIMENTAL_NUMERIC_ONLY",values=[sum(a*b for a,b in zip(row,x)) for row in self.w])
    def update(self,x,y,admitted=False,committed=False):
        if not (admitted and committed):raise PermissionError("committed admitted supervision required")
        x,y=vec(x,self.ni),vec(y,self.no)
        pred=[sum(a*b for a,b in zip(row,x)) for row in self.w]
        loss=sum((a-b)**2 for a,b in zip(pred,y))/self.no
        scale=self.rate/max(1.,math.sqrt(sum(v*v for v in x)))
        for j in range(self.no):
            d=max(-1.,min(1.,y[j]-pred[j]))*scale
            for i in range(self.ni):self.w[j][i]+=d*x[i]
        self.steps+=1
        return loss
    def checkpoint(self):
        return dict(schema=SCHEMA,source=self.source,target=self.target,ni=self.ni,no=self.no,rate=self.rate,w=self.w,steps=self.steps,revision=self.revision())
    @classmethod
    def restore(cls,data):
        if data.get("schema")!=SCHEMA:raise ValueError("schema")
        p=cls(data["source"],data["target"],data["ni"],data["no"],data["rate"])
        if len(data["w"])!=p.no:raise ValueError("shape")
        p.w=[vec(row,p.ni) for row in data["w"]]
        if type(data.get("steps")) is not int or data["steps"]<0:raise ValueError("steps")
        p.steps=data["steps"]
        if p.revision()!=data.get("revision"):raise ValueError("integrity")
        return p
def receive(packet,target,generation,source_ids,revision):
    if packet.get("schema")!=SCHEMA or packet.get("authority")!="EXPERIMENTAL_NUMERIC_ONLY":raise ValueError("schema")
    if packet.get("target")!=target or packet.get("generation")!=generation or packet.get("source_id") not in source_ids:raise PermissionError("source")
    if packet.get("revision")!=revision:raise ValueError("stale revision")
    v=packet.get("values")
    if not isinstance(v,list) or not 1<=len(v)<=256:raise ValueError("shape")
    return vec(v,len(v))
