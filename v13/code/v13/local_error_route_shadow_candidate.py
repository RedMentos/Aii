"""Per-event N10/route-worker preview; never applies an optimizer update.

It requires a current explicit route correction and an explicitly typed,
source-bound N10 outcome for the same event. The supplied embedding is an
unverified diagnostic input, not evidence that a native encoder ran.
"""
import hashlib
import math
from pathlib import Path

import numpy as np

from . import learning_worker,neuromod,world_model
from .common import digest,dumps
from . import world_semantic_evidence_candidate as semantic


PINS={'neuromod.py':'abd6379bd8843b2e763fea315ea78dfbb5142ee03d4b71eae3b33a48c018c86d',
      'learning_worker.py':'b6ca098612016f138240c19ad847e8f7fc850a125cfb8b0c10a7ca9fbaf85c2a',
      'learning.py':'6776dd82eb2604f7fb2c17a9773911df73fbf4f672d7c533ed15135987cfa53c',
      'world_semantic_evidence_candidate.py':'354306bb763fda116728bd13e8502d81ed8e6a790c4387d98e0920960a87b8a5'}
REVISION='local-error-route-shadow-v1'


def _check_sources():
    directory=Path(__file__).resolve().parent
    for name,sha in PINS.items():
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=sha:
            raise ValueError('local-error candidate source changed: '+name)


def _object(raw):return world_model._t8_source_object(raw)


def _route_correction(store,conn,event_id,session,generation):
    rows=conn.execute("SELECT f.id,f.source_id,f.value,f.permission,m.value AS memory_value,"
                      "m.session_id,s.chars,s.kind AS source_kind FROM feedback f "
                      "JOIN memories m ON m.event_id=f.event_id AND m.source_id=f.source_id "
                      "AND m.kind='route' AND m.active=1 JOIN sources s ON s.id=f.source_id "
                      "WHERE f.event_id=? AND f.kind='route' LIMIT 2",(event_id,)).fetchall()
    if len(rows)!=1:raise ValueError('unique active route correction required')
    row=rows[0]
    if (row['session_id']!=session or row['source_kind']!='HUMAN_DECISION'
            or row['value'] not in world_model.ACTIONS or row['permission'] not in {'record','learn'}):
        raise ValueError('route correction binding invalid')
    decisions=conn.execute("SELECT id,payload,generation_id FROM packets WHERE event_id=? "
                           "AND kind='HumanDecision' ORDER BY id LIMIT 129",(event_id,)).fetchall()
    if len(decisions)>=129:raise ValueError('human decision scan saturated')
    matches=[]
    for packet in decisions:
        value=_object(packet['payload']);ref=value.get('source_ref')
        if isinstance(ref,dict) and ref.get('source_id')==row['source_id']:
            matches.append((packet,value,ref))
    if len(matches)!=1:raise ValueError('route correction decision missing or ambiguous')
    packet,value,ref=matches[0]
    if (packet['generation_id']!=generation or value.get('packet_id')!=packet['id']
            or value.get('brain_generation_id')!=generation or value.get('event_id')!=event_id
            or value.get('producer_component')!='F5_HUMAN_CONTROL' or value.get('schema_version')!='1.0'
            or value.get('kind')!='route' or value.get('learning_permission')!=row['permission']
            or not isinstance(value.get('provenance'),list) or ref not in value['provenance']
            or ref.get('modality')!='text' or ref.get('char_start')!=0 or ref.get('char_end')!=row['chars']
            or store.read_source(ref)!=row['value'] or row['value']!=row['memory_value']
            or row['value']!=value.get('value')):
        raise ValueError('route correction source invalid')
    return {'route':row['value'],'permission':row['permission'],'source_ref':ref,
            'packet_sha256':digest(packet['payload'])}


def _packet_bindings(store,conn,event_id,generation,input_ref,label_ref):
    packets=conn.execute("SELECT id,kind,generation_id,payload FROM packets WHERE event_id=? "
                         "AND kind IN ('LearningTrace','ModulatorPacket') ORDER BY rowid LIMIT 257",
                         (event_id,)).fetchall()
    if len(packets)>=257:raise ValueError('local-error packet scan saturated')
    traces=[];signals=[]
    for packet in packets:
        value=_object(packet['payload']);path=value.get('path_id')
        if path is not None and neuromod.path_of(path)!='route':continue
        if packet['kind']=='LearningTrace' and path is None:continue
        if (packet['generation_id']!=generation or value.get('packet_id')!=packet['id']
                or value.get('event_id')!=event_id or value.get('brain_generation_id')!=generation
                or value.get('schema_version')!='1.0' or not isinstance(value.get('provenance'),list)):
            raise ValueError('local-error packet binding invalid')
        (traces if packet['kind']=='LearningTrace' else signals).append((packet,value))
    if len(traces)!=1 or len(signals)!=1:return None
    trace_packet,trace=traces[0];signal_packet,signal=signals[0]
    channels=signal.get('channels')
    if (trace.get('producer_component') not in {'N10_NEUROMOD','F4_LEARNING'}
            or trace.get('authority') not in {'EXPLICIT_HUMAN_LEARN','EXPLICIT_HUMAN_RULE'}
            or input_ref not in trace['provenance'] or input_ref not in signal['provenance']
            or label_ref not in signal['provenance'] or signal.get('producer_component')!='N10_NEUROMOD'
            or signal.get('source_class')!='human_correction' or signal.get('finality')!='FINAL'
            or not isinstance(channels,dict) or 'task_success' not in channels
            or type(channels['task_success']) not in (int,float)
            or not math.isfinite(channels['task_success']) or channels['task_success'] not in (0,1)
            or signal.get('task_success')!=channels['task_success']
            or signal.get('values_status') is not None):
        return None
    for ref in (input_ref,label_ref):store.read_source(ref)
    return {'outcome':float(channels['task_success']),
            'trace_sha256':digest(trace_packet['payload']),'signal_sha256':digest(signal_packet['payload'])}


def preview(n10,session,event_id,embedding):
    """Join real event evidence to a single-sample route gradient preview."""
    _check_sources()
    if not isinstance(n10,neuromod.Neuromod):raise ValueError('N10 instance required')
    store=n10.s
    # This serializes same-Store callers. It is not an interprocess transaction
    # spanning future optimization or an immutable native embedding proof.
    with store.mutex:
        first=semantic.snapshot(store,session,event_id)
        if n10.local_mode()!='SHADOW':
            return {'status':'ACTIVE_MODE_UNSUPPORTED','training_authority':0}
        with store.tx() as conn:
            event=conn.execute('SELECT packet,generation_id FROM events WHERE id=? AND session_id=?',
                               (event_id,session)).fetchone()
            if not event:raise ValueError('event unavailable')
            envelope=_object(event['packet']);input_ref=envelope['source_ref']
            label=_route_correction(store,conn,event_id,session,event['generation_id'])
            if label['permission']!='learn':
                return {'status':'LABEL_RECORD_ONLY','training_authority':0}
            packets=_packet_bindings(store,conn,event_id,event['generation_id'],input_ref,label['source_ref'])
            if packets is None:
                return {'status':'NO_UNAMBIGUOUS_TYPED_OUTCOME','training_authority':0}
        # Agreement is an operator route label, not answer correctness.
        expected=float(first['route']==label['route'])
        if packets['outcome']!=expected:
            return {'status':'OUTCOME_DISAGREES_WITH_ROUTE_LABEL','training_authority':0}
        result=n10.local_update('route')
        state,_=n10._load();path=state.get('paths',{}).get('route',{})
        delta=result['gate'].get('delta')
        if (not isinstance(delta,dict) or delta.get('event_id')!=event_id
                or path.get('last_event')!=event_id):
            return {'status':'STALE_EVENT_DELTA_OR_TRACE','training_authority':0}
        prior=delta.get('r_hat');delta_value=delta.get('value')
        if (type(prior) not in (int,float) or not math.isfinite(prior) or not 0<=prior<=1
                or type(delta_value) not in (int,float) or not math.isfinite(delta_value)
                or delta_value!=round(packets['outcome']-prior,6)
                or type(result['scale']) not in (int,float) or not math.isfinite(result['scale'])
                or not -1<=result['scale']<=1):
            return {'status':'INVALID_EVENT_DELTA','training_authority':0}
        if result['gate']['veto'] or result['gate']['conflict']['verify_first']:
            return {'status':'N10_VETO_OR_CONFLICT','training_authority':0}
        second=semantic.snapshot(store,session,event_id)
        with store.tx() as conn:
            after=_route_correction(store,conn,event_id,session,event['generation_id'])
            packet_after=_packet_bindings(store,conn,event_id,event['generation_id'],input_ref,after['source_ref'])
        if (first['fingerprint_sha256']!=second['fingerprint_sha256'] or label!=after or packets!=packet_after):
            return {'status':'EVIDENCE_CHANGED','training_authority':0}
        sample=np.asarray(embedding,dtype=float)
        if (sample.ndim!=1 or not 1<=len(sample)<=512 or not np.isfinite(sample).all()
                or np.max(np.abs(sample))>1e6):raise ValueError('invalid preview embedding')
        x=learning_worker.features([sample]);w=np.zeros((x.shape[1],len(world_model.ACTIONS)))
        loss,gradient,_=learning_worker.objective(x,np.asarray([world_model.ACTIONS.index(label['route'])]),w)
        if not np.isfinite(gradient).all() or not math.isfinite(loss):raise ValueError('nonfinite preview')
        # Error magnitude weights the human-corrected route target. Never use a
        # negative multiplier to imitate or reverse the observed wrong route.
        weight=abs(result['scale'])
        return {'revision':REVISION,'status':'SHADOW_PREVIEW','event_id':event_id,
                't8_action_id':first['t8_action_id'],'observed_route':first['route'],
                'corrected_route':label['route'],'operator_route_agreement':bool(expected),
                'event_delta':result['delta'],'local_scale':result['scale'],
                'sample_cross_entropy':float(loss),'sample_gradient_norm':float(np.linalg.norm(gradient)),
                'preview_weight':weight,'weighted_gradient_norm':float(np.linalg.norm(weight*gradient)),
                'embedding_authority':'CALLER_SUPPLIED_NOT_VALIDATED',
                'weight_reference':'ZERO_INITIALIZED_NOT_ACTIVE_CHECKPOINT',
                'source_fingerprint':digest(dumps({'semantic':first['fingerprint_sha256'],
                                                   'label':label['packet_sha256'],'packets':packets})),
                'training_authority':0,'decision_authority':0}
