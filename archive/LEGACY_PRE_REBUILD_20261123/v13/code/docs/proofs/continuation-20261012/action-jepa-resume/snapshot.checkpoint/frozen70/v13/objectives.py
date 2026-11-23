"""IH-H25 Learning Objective Plugin Contract: ObjectiveAdapter objects instead of a bare registry file.

specs/learning-objectives.json stays the declarative source; registry() turns each row into a validated
ObjectiveAdapter, and code may register() further adapters (with callable target builders / losses).
Rules enforced here, not only documented:
  - every adapter carries all ten contract fields (None/[] allowed only when the status is not IMPLEMENTED)
  - status UNAVAILABLE or PARTIAL  -> learn_gain 0 (§IH-H25: "objective status = unavailable, learn_gain = 0")
  - IMPLEMENTED needs loss_terms, eval_metrics, update_scope and existing implementation files
  - effective learn gain is 0 in RECORD_ONLY; otherwise the objective's configured rate (verification parity)
"""
import json
from dataclasses import dataclass,field,asdict
from .common import APP

CONTRACT=('objective_id','applicable_components','required_inputs','target_builder','stop_gradient_policy','ema_policy',
          'loss_terms','credit_mapper','update_scope','eval_metrics')
STATUSES=('IMPLEMENTED','PARTIAL','UNAVAILABLE')
_PLUGINS={}

@dataclass
class ObjectiveAdapter:
    objective_id:str
    applicable_components:list
    required_inputs:list
    target_builder:object
    stop_gradient_policy:object
    ema_policy:object
    loss_terms:list
    credit_mapper:object
    update_scope:object
    eval_metrics:list
    status:str='UNAVAILABLE'
    reason:str=''
    implementation_files:list=field(default_factory=list)
    learning_rate_config_key:str=None
    loss:object=None  # optional callable(batch) -> float for code plugins
    def validate(self):
        if self.status not in STATUSES:raise ValueError(self.objective_id+': status '+str(self.status))
        if not self.objective_id or not self.applicable_components:raise ValueError('objective_id/applicable_components fehlen')
        if self.status=='IMPLEMENTED':
            for k in ('loss_terms','eval_metrics','update_scope','target_builder','credit_mapper'):
                if not getattr(self,k):raise ValueError(self.objective_id+': IMPLEMENTED ohne '+k)
            missing=[p for p in self.implementation_files or [] if not (APP/p).is_file()]
            if not self.implementation_files or missing:raise ValueError(self.objective_id+': Implementierung fehlt '+str(missing or 'implementation_files'))
        return self
    def learn_gain(self,cfg):
        if self.status!='IMPLEMENTED' or cfg.get('learning_mode','RECORD_ONLY')=='RECORD_ONLY':return 0
        return cfg.get(self.learning_rate_config_key or 'learning_rate',0)
    def view(self):
        d=asdict(self);d.pop('loss');d['target_builder']=d['target_builder'] if isinstance(d['target_builder'],(str,type(None))) else 'callable'
        return d

def from_row(row):
    kw={k:row.get(k) for k in CONTRACT}
    for k in ('applicable_components','required_inputs','loss_terms','eval_metrics'):kw[k]=kw[k] or []
    return ObjectiveAdapter(**kw,status=row.get('status','UNAVAILABLE'),reason=row.get('reason',''),
                            implementation_files=row.get('implementation_files') or [],learning_rate_config_key=row.get('learning_rate_config_key')).validate()

def register(adapter):
    """Code plugin: add or override an objective (validated)."""
    _PLUGINS[adapter.validate().objective_id]=adapter;return adapter

def spec():return json.loads((APP/'specs/learning-objectives.json').read_text())

def registry(cfg=None):
    out={}
    for row in spec()['objectives']:
        a=from_row(row)
        if a.objective_id in out:raise ValueError('Doppeltes Lernziel: '+a.objective_id)
        out[a.objective_id]=a
    out.update(_PLUGINS);return out

def report(cfg):
    reg=registry(cfg);count={}
    for a in reg.values():count[a.status]=count.get(a.status,0)+1
    return {'counts':count,'objectives':{k:{'status':a.status,'components':a.applicable_components,'learn_gain':a.learn_gain(cfg),'reason':a.reason[:160]} for k,a in reg.items()}}
