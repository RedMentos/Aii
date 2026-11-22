"""WP-N12 parameter register (IH-H5 KnobSpec + PathSpec, blueprint §49–§78, Age-0 profile §78).

One view over all regulators: the operator knobs of config.KNOBS plus every research knob the blueprint
declares in §49–§78 (specs/blueprint-knobs.json, built by scripts/build_knob_register.py). A curated map
(specs/knob-map.json) ties blueprint ids to the code constant that implements them; the register reads the
live code value and reports MATCH, DRIFT (code differs from blueprint) or DECLARED_ONLY (no code yet).
0..1 is never silently a probability: every entry carries a kind (IH-H5).
"""
import importlib
import json
import re
from .common import APP
from .config import knob_specs

KIND_RULES=(('threshold','THRESHOLD'),('authority','AUTHORITY'),('prior','PRIOR'),('probab','PROBABILITY'),('budget','BUDGET_FRACTION'),
            ('decay','DECAY'),('beta','DECAY'),('half_life','DECAY'),('learning_rate','LEARNING_RATE'),('_lr','LEARNING_RATE'),('temperature','TEMPERATURE'),
            ('rate_hz','RATE_HZ'),('_ms','DURATION_MS'),('cycles','COUNT'),('successes','COUNT'),('confirmations','COUNT'),('slot_','COUNT'),
            ('max_','COUNT'),('stage','COUNT'),('rung','COUNT'),('span_target','COUNT'),('gain','MIX_WEIGHT'),('weight','MIX_WEIGHT'),('mix','MIX_WEIGHT'))

def kind_of(knob):
    kid=knob['id'].lower()
    for needle,kind in KIND_RULES:
        if needle in kid:return kind,False
    if knob.get('value') is not None and float(knob['value']).is_integer() and abs(knob['value'])>1:return 'COUNT',True
    return 'MIX_WEIGHT',True  # §49 normalized research scale; flagged as inferred, never PROBABILITY

def _json(name):return json.loads((APP/'specs'/name).read_text())
def blueprint():return _json('blueprint-knobs.json')
def calibration():
    """WP-KAL measured values per code location (specs/calibration.json); {} when absent."""
    try:return _json('calibration.json')['values']
    except (OSError,KeyError,ValueError):return {}
def calibration_for(cal,location):
    if not location:return None
    return cal.get(location) or cal.get(location.split('[',1)[0])
def mapping():return _json('knob-map.json')['map']
def deviations():return _json('knob-map.json').get('deviations',{})  # WP-T15: deliberate, reasoned code != blueprint

def resolve(loc):
    v=getattr(importlib.import_module(loc['module']),loc['attr'])
    v=v[loc['key']] if 'key' in loc else v
    return v[loc['index']] if 'index' in loc else v  # e.g. sleep.POLICY entries are (default, lo, hi)

def entries(cfg=None):
    bp=blueprint();mp=mapping();cal=calibration();dev=deviations();out=[]
    for s in knob_specs(cfg):out.append(s|{'source':'OPERATOR_KNOB','status':'OPERATOR','blueprint_value':None,'code_location':'config.KNOBS'})
    seen=set()
    for k in bp['knobs']:
        if k['id'] in seen:continue  # later duplicate declarations (§72H) restate the same knob
        seen.add(k['id']);kind,inferred=kind_of(k);loc=mp.get(k['id']);code=None;status='DECLARED_ONLY'
        if loc:
            try:
                code=resolve(loc);status='MATCH' if k['value'] is not None and abs(float(code)-k['value'])<1e-9 else ('DOCUMENTED_DEVIATION' if k['id'] in dev else 'DRIFT')
            except Exception as exc:status='MAP_BROKEN';code=type(exc).__name__
        normalized=kind not in {'COUNT','DURATION_MS','RATE_HZ','BYTES','LEARNING_RATE'}
        out.append({'id':k['id'],'kind':kind,'kind_inferred':inferred,'value':code if status in {'MATCH','DRIFT','DOCUMENTED_DEVIATION'} else k['value'],'unit':'normalized' if normalized else '1',
                    'min':-1. if normalized and (k['value'] or 0)<0 else (0. if normalized else None),'max':1. if normalized else None,'owner':'BLUEPRINT_RESEARCH',
                    'stage_cap':None,'user_cap':None,'learned_allowed':'LEARNED' in k['tags'],'clamp_policy':'REJECT_OUT_OF_RANGE',
                    'description':f"§{k['section']} {k['title']}"+(f" · {k['raw']}" if k['raw'] and k['value'] is None else ''),
                    'source':'BLUEPRINT','section':k['section'],'tags':k['tags'],'blueprint_value':k['value'],
                    'code_location':(loc['module'].split('.',1)[1]+'.'+loc['attr']+(f"[{loc['key']}]" if 'key' in loc else '')) if loc else None,'status':status})
        out[-1]['calibration']=calibration_for(cal,out[-1]['code_location'])
        if status=='DOCUMENTED_DEVIATION':out[-1]['deviation_reason']=dev[k['id']]
    return out

def paths():
    """PathSpec: every learnable path with its learning kind, Age capability and LR knob."""
    from .neuromod import COMPONENT_KIND,AGE_CAPABILITY
    from .plasticity import LR_KEYS
    names=sorted(set(COMPONENT_KIND)|set(LR_KEYS))
    return [{'path':n,'kind':COMPONENT_KIND.get(n,'skill'),'age_capability':AGE_CAPABILITY.get(COMPONENT_KIND.get(n,'skill')),'lr_knob':LR_KEYS.get(n),
             'gate':'neuromod.gate x plasticity.budget','base_merge_authority':0} for n in names]

def summary(cfg=None):
    rows=entries(cfg);bp=[r for r in rows if r['source']=='BLUEPRINT'];count=lambda s:sum(r['status']==s for r in bp)
    groups={}
    for r in bp:
        g=groups.setdefault(r['id'].split('.')[0],{'declared':0,'implemented':0});g['declared']+=1;g['implemented']+=r['status'] in {'MATCH','DRIFT','DOCUMENTED_DEVIATION'}
    return {'operator_knobs':len(rows)-len(bp),'blueprint_knobs':len(bp),'match':count('MATCH'),'drift':count('DRIFT'),'documented_deviation':count('DOCUMENTED_DEVIATION'),'declared_only':count('DECLARED_ONLY'),
            'map_broken':count('MAP_BROKEN'),'kind_inferred':sum(r['kind_inferred'] for r in bp),'learnable_paths':len(paths()),
            'coverage':round((count('MATCH')+count('DRIFT')+count('DOCUMENTED_DEVIATION'))/max(len(bp),1),4),'calibrated':sum(1 for r in bp if r.get('calibration')),'groups':dict(sorted(groups.items())),
            'drift_list':[{k:r[k] for k in ('id','blueprint_value','value','code_location')} for r in bp if r['status']=='DRIFT'],
            'deviation_list':[{k:r[k] for k in ('id','blueprint_value','value','code_location','deviation_reason')} for r in bp if r['status']=='DOCUMENTED_DEVIATION'],
            'canon_sha256':blueprint()['canon_sha256']}

def operator_command(r,args):
    if not args or args==['summary']:return summary(r.cfg)
    if args==['drift']:return summary(r.cfg)['drift_list']
    if args==['paths']:return paths()
    if args==['declared']:return [x['id'] for x in entries(r.cfg) if x['status']=='DECLARED_ONLY']
    if len(args)==1 and re.fullmatch(r'[A-Za-z0-9_.]+',args[0]):return [x for x in entries(r.cfg) if x['id'].startswith(args[0])]
    raise ValueError(':register [summary|drift|paths|declared|<Präfix>]')
