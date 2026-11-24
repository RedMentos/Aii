"""F7 slow, measured budget control for the existing external shadow learners.

This is a bounded feedback controller, not a trained neural metaplasticity head.
It changes only future explicit shadow-job budgets. Base weights, inference,
commit gates and independent component approvals retain their existing owners.
"""
import json
import math
from .common import dumps,file_hash
from .config import KNOBS
from .contracts import packet

LR_KEYS={'route':'learning_rate','wake':'learning_rate','halt':'learning_rate',
         'b1_predictor':'predictor_lr','b2_predictor':'predictor_lr','a3_student':'student_lr',
         'world_predictor':'predictor_lr','control_calibration':'calibration_lr','memory_retrieval':'retrieval_lr','output_adapter':'output_adapter_lr'}
REVISION='f7-measured-shadow-budget-v1'

def initial(component):
    if component not in LR_KEYS:raise ValueError('Unknown external learning component')
    return {'revision':REVISION,'component':component,'trials':0,'stability_score':.5,'plasticity_gain':1.,
            'saturation':None,'last_update_id':None,'last_created':0.,'last_sequence':0,'seen_ids':[],
            'retention_failures':0,'consecutive_stable_trials':0,'consolidation_ready':False,
            'native_shared_attention_drift':None,'native_router_input_drift':None,'semantic_truth_authority':False}

def number(value):return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value)
def policy_scale(policy):
    """F7 gain × optional WP-N10 neuromodulation factor (absent on older manifests = 1)."""
    nm=policy.get('neuromodulation')
    if nm is None:return policy['plasticity_gain']
    if not isinstance(nm,dict) or not number(nm.get('factor')) or not 0<nm['factor']<=1:return None
    return policy['plasticity_gain']*nm['factor']

class Plasticity:
    def __init__(self,store):self.s=store
    def state(self,component):
        state,version=self.s.state('F7_PLASTICITY:'+component,initial(component))
        if state.get('revision')!=REVISION or state.get('component')!=component:raise ValueError('Plasticity state revision mismatch')
        if not all(number(state.get(k)) and 0<=state[k]<=1 for k in ('plasticity_gain','stability_score')) or state['plasticity_gain']<.5:raise ValueError('Plasticity state out of bounds')
        return state,version
    def observe(self,update_id):
        row=self.s.one('SELECT rowid AS sequence,* FROM updates WHERE id=?',(update_id,))
        if not row or row['status'] not in {'PENDING_APPROVAL','EVALUATED_FAIL','APPROVED','COMMITTED','ROLLED_BACK','REJECTED'}:return False
        try:manifest=json.loads(row['manifest'])
        except (TypeError,ValueError):return False
        if not isinstance(manifest,dict):return False
        component=manifest.get('component','route')
        if component not in LR_KEYS or not isinstance(manifest.get('training_policy'),dict) or manifest['training_policy'].get('revision')!=REVISION:return False
        policy=manifest['training_policy'];key=LR_KEYS[component]
        if policy.get('component')!=component or policy.get('learning_rate_key')!=key or policy.get('native_parameter_authority')!=0:return False
        required=('base_learning_rate','effective_learning_rate','base_max_update_norm','effective_max_update_norm','plasticity_gain')
        if not all(number(policy.get(k)) for k in required) or not .5<=policy['plasticity_gain']<=1:return False
        if not KNOBS[key][2]<=policy['base_learning_rate']<=KNOBS[key][3] or not KNOBS['max_update_norm'][2]<=policy['base_max_update_norm']<=KNOBS['max_update_norm'][3]:return False
        scale=policy_scale(policy)
        if scale is None:return False
        if policy['effective_learning_rate']!=max(KNOBS[key][2],policy['base_learning_rate']*scale) or policy['effective_max_update_norm']!=max(KNOBS['max_update_norm'][2],policy['base_max_update_norm']*scale):return False
        budget=self.s.rows("SELECT payload FROM packets WHERE kind='PlasticityBudget' AND event_id=?",(update_id,))
        if len(budget)!=1:return False
        bp=json.loads(budget[0]['payload'])
        if bp.get('component')!=component or bp.get('update_id')!=update_id or bp.get('brain_generation_id')!=row['base_generation'] or bp.get('policy')!=policy:return False
        metrics=manifest.get('metrics',{})
        if not isinstance(metrics,dict):return False
        retained=metrics.get('retention_pass');eligible=metrics.get('commit_eligible')
        if not isinstance(retained,bool) or not isinstance(eligible,bool):return False
        if metrics.get('effective_learning_rate')!=policy['effective_learning_rate'] or metrics.get('effective_max_update_norm')!=policy['effective_max_update_norm']:return False
        old,version=self.state(component)
        if update_id in old['seen_ids'] or row['sequence']<=old['last_sequence']:return False
        path=(self.s.home/(row['path'] or '')).resolve()
        prefix='checkpoints/head-' if component=='route' else 'checkpoints/'+component+'-'
        if not row['path'] or not row['path'].startswith(prefix) or '/' in row['path'][len(prefix):]:return False
        if not path.is_relative_to((self.s.home/'checkpoints').resolve()) or not path.is_file() or file_hash(path)!=row['hash']:return False
        state=json.loads(dumps(old));safe=retained and eligible
        state['stability_score']=.95*old['stability_score']+.05*float(safe)
        state['consecutive_stable_trials']=old['consecutive_stable_trials']+1 if safe else 0
        state['retention_failures']=old['retention_failures']+int(not retained)
        # Retention failure damps plasticity. A fit that preserves old tasks but
        # misses a utility gate slowly reopens the component, up to its base LR.
        target=.5 if not retained else (max(.5,1-.5*state['stability_score']) if safe else 1.)
        applied=metrics.get('max_applied_step_norm',metrics.get('max_step_norm'));cap=manifest['training_policy']['effective_max_update_norm']
        state['saturation']=min(1.,max(0.,applied/cap)) if number(applied) and applied>=0 and number(cap) and cap>0 else None
        if state['saturation'] is not None and state['saturation']>=.95:target=max(.5,target*.9)
        state['plasticity_gain']=min(1.,max(.5,.95*old['plasticity_gain']+.05*target))
        state.update(trials=old['trials']+1,last_update_id=update_id,last_created=row['created'],last_sequence=row['sequence'],seen_ids=(old['seen_ids']+[update_id])[-256:])
        # This is only a measured stability tag; it grants no consolidation,
        # knowledge truth, source deletion or autonomous commit authority.
        state['consolidation_ready']=state['consecutive_stable_trials']>=3 and state['stability_score']>=.7
        p=packet('PlasticityState','F7',update_id,row['base_generation'],component=component,update_id=update_id,
                 trials=state['trials'],plasticity_gain=state['plasticity_gain'],stability_score=state['stability_score'],
                 retention_pass=retained,saturation=state['saturation'],consolidation_ready=state['consolidation_ready'],
                 artifact_hash=row['hash'],native_shared_attention_drift=None,native_router_input_drift=None,semantic_truth_authority=False)
        # State and its typed observation are atomic; restart cannot count the
        # same finished trial twice even across the writer's crash window.
        with self.s.tx() as c:
            key='F7_PLASTICITY:'+component;current=c.execute('SELECT version FROM states WHERE key=?',(key,)).fetchone()
            if (current[0] if current else 0)!=version:raise ValueError('Stale plasticity state write')
            c.execute('INSERT OR REPLACE INTO states VALUES (?,?,?)',(key,version+1,dumps(state)))
            c.execute('INSERT INTO packets VALUES (?,?,?,?,?,?)',(p['packet_id'],'PlasticityState',update_id,row['base_generation'],dumps(p),p['created_wall_time']))
        self.s.log('plasticity',None,{'component':component,'trials':state['trials'],'plasticity_gain':state['plasticity_gain'],'stability_score':state['stability_score'],'retention_pass':retained,'saturation':state['saturation'],'consolidation_ready':state['consolidation_ready']})
        return True
    def reconcile(self):
        # Only instrumented trials are eligible, so old incomplete or imported
        # manifests cannot fabricate observations or silently gain authority.
        for row in self.s.rows("SELECT id FROM updates WHERE json_extract(manifest,'$.training_policy.revision')=? ORDER BY rowid",(REVISION,)):
            self.observe(row['id'])
    def budget(self,component,cfg,update_id,manifest,modulation=None):
        """modulation: WP-N10 neuromod.gate() result; its factor scales the budget, a veto blocks the job."""
        if cfg['learning_mode']=='RECORD_ONLY':raise ValueError('No optimizer budget in RECORD_ONLY')
        if modulation is not None and (modulation.get('veto') or not number(modulation.get('factor')) or not 0<modulation['factor']<=1):
            raise ValueError('Lernen für '+component+' durch Modulator-Veto/Gate gesperrt')
        self.reconcile();state,_=self.state(component);gain=state['plasticity_gain'];key=LR_KEYS[component]
        scale=gain if modulation is None else gain*modulation['factor']
        result=dict(cfg);result[key]=max(KNOBS[key][2],cfg[key]*scale)
        result['max_update_norm']=max(KNOBS['max_update_norm'][2],cfg['max_update_norm']*scale)
        manifest['training_policy']={'revision':REVISION,'component':component,'state_trials':state['trials'],'plasticity_gain':gain,
             'learning_rate_key':key,'base_learning_rate':cfg[key],'effective_learning_rate':result[key],
             'base_max_update_norm':cfg['max_update_norm'],'effective_max_update_norm':result['max_update_norm'],
             'consolidation_ready':state['consolidation_ready'],'native_parameter_authority':0}
        if modulation is not None:
            manifest['training_policy']['neuromodulation']={k:modulation[k] for k in ('revision','path_id','kind','factor','eligibility','modulator','age_plasticity','consolidation_tag')}
        p=packet('PlasticityBudget','F7',update_id,manifest['base_generation'],component=component,update_id=update_id,
                 policy=manifest['training_policy'],native_parameter_authority=0)
        self.s.add_packet('PlasticityBudget',p);return result
    def report(self,component=None):
        self.reconcile();names=[component] if component else list(LR_KEYS)
        return {'revision':REVISION,'scope':'Measured bounded control of explicit external shadow-job budgets',
                'components':{name:self.state(name)[0] for name in names},'native_parameter_authority':0,
                'learned_neural_controller':False,'shared_native_interference_measured':False}
