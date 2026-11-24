"""Source-bound N10/route-worker previews on real Store, synthetic C3."""
import json
import time
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from v13 import local_error_route_shadow_candidate as candidate
from v13.contracts import packet
from v13.neuromod import Neuromod
from v13.runtime import Runtime


@pytest.fixture
def runtime(tmp_path):
    r=Runtime(tmp_path);r.sleep.cycle.set_policy('enabled','off')
    r._route=Mock(return_value=('simple',{'source':'TEST_ROUTE_SEAM'}))
    r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},
                    generate=lambda *a,**k:iter(['synthetic response'])))
    r.learner.output_delta=Mock(return_value=None)
    try:yield r
    finally:r.close()


def turn(r,text='Test request'):
    event=r.submit(text);end=time.monotonic()+10
    while not r.idle() and time.monotonic()<end:time.sleep(.005)
    assert r.idle() and r.last_answer()['status']=='FINAL'
    return event


def correction(r,event,route='detail',permission='learn'):
    mid=r.memory.feedback(event,'route',route,permission=permission)
    source=r.store.one('SELECT source_id FROM memories WHERE id=?',(mid,))['source_id']
    values=[json.loads(row['payload']) for row in r.store.rows(
        "SELECT payload FROM packets WHERE event_id=? AND kind='HumanDecision'",(event,))]
    label=next(value['source_ref'] for value in values if value['source_ref']['source_id']==source)
    event_packet=json.loads(r.store.one('SELECT packet FROM events WHERE id=?',(event,))['packet'])
    return event_packet['source_ref'],label


def emit(n,event,input_ref,label_ref,success):
    n.touch('route',event,authority='EXPLICIT_HUMAN_LEARN',refs=[input_ref])
    n.signal(event,'route',source_class='human_correction',refs=[input_ref,label_ref],task_success=success)


def test_actual_event_correction_and_negative_delta_preview_without_weight_update(runtime):
    r=runtime;event=turn(r);input_ref,label_ref=correction(r,event)
    n=Neuromod(r.store);emit(n,event,input_ref,label_ref,0.)
    result=candidate.preview(n,r.session,event,[1.,0.])
    assert result['status']=='SHADOW_PREVIEW' and result['t8_action_id']
    assert (result['observed_route'],result['corrected_route'])==('simple','detail')
    assert result['event_delta']<0 and result['local_scale']<0
    assert result['sample_gradient_norm']>0 and np.isfinite(result['sample_cross_entropy'])
    assert result['preview_weight']>=0
    assert result['weighted_gradient_norm']==pytest.approx(abs(result['local_scale'])*result['sample_gradient_norm'])
    assert result['embedding_authority']=='CALLER_SUPPLIED_NOT_VALIDATED'
    assert result['weight_reference']=='ZERO_INITIALIZED_NOT_ACTIVE_CHECKPOINT'
    assert result['training_authority']==result['decision_authority']==0
    assert r.store.rows('SELECT * FROM updates')==[]


def test_positive_agreement_is_not_called_factual_truth(runtime):
    r=runtime;event=turn(r);input_ref,label_ref=correction(r,event,route='simple')
    n=Neuromod(r.store);emit(n,event,input_ref,label_ref,1.)
    result=candidate.preview(n,r.session,event,[0.,1.])
    assert result['operator_route_agreement'] is True and result['event_delta']>0
    assert result['training_authority']==0 and 'truth' not in result


def test_record_only_correction_does_not_authorize_preview_gradient(runtime):
    r=runtime;event=turn(r);correction(r,event,permission='record')
    result=candidate.preview(Neuromod(r.store),r.session,event,[1.,0.])
    assert result=={'status':'LABEL_RECORD_ONLY','training_authority':0}


def test_placeholder_zero_is_not_a_real_outcome(runtime):
    r=runtime;event=turn(r);input_ref,_=correction(r,event)
    n=Neuromod(r.store);generation=r.store.generation_id
    r.store.add_packet('LearningTrace',packet('LearningTrace','F4_LEARNING',event,generation,[input_ref],
                       path_id='C2_EXTERNAL_ROUTE_HEAD',activity=1.,eligibility=r.cfg['eligibility_decay'],
                       authority='EXPLICIT_HUMAN_LEARN'))
    r.store.add_packet('ModulatorPacket',packet('ModulatorPacket','F4_LEARNING',event,generation,[input_ref],
                       epistemic_evidence=1.,human_correction=1.,task_success=0.,resource_cost=0.,safety_veto=False,
                       values_status='human label present; task success and cost not optimizer rewards'))
    assert n.local_update('route')['delta']<0  # Existing N10 treats the placeholder as an outcome.
    result=candidate.preview(n,r.session,event,[1.,0.])
    assert result=={'status':'NO_UNAMBIGUOUS_TYPED_OUTCOME','training_authority':0}


def test_later_trace_cannot_reuse_previous_event_delta(runtime):
    r=runtime;first=turn(r,'First request');ref1,label1=correction(r,first)
    n=Neuromod(r.store);emit(n,first,ref1,label1,0.)
    assert candidate.preview(n,r.session,first,[1.,0.])['status']=='SHADOW_PREVIEW'
    second=turn(r,'Second request');ref2,_=correction(r,second)
    n.touch('route',second,authority='EXPLICIT_HUMAN_LEARN',refs=[ref2])
    unbound=n.local_update('route')
    assert unbound['gate']['delta']['event_id']==first and unbound['scale']!=0
    assert candidate.preview(n,r.session,second,[1.,0.])['status']=='NO_UNAMBIGUOUS_TYPED_OUTCOME'
    assert candidate.preview(n,r.session,first,[1.,0.])['status']=='STALE_EVENT_DELTA_OR_TRACE'


def test_wrong_outcome_or_duplicate_signal_is_not_a_preview(runtime):
    r=runtime;event=turn(r);input_ref,label_ref=correction(r,event)
    n=Neuromod(r.store);emit(n,event,input_ref,label_ref,1.)
    assert candidate.preview(n,r.session,event,[1.,0.])['status']=='OUTCOME_DISAGREES_WITH_ROUTE_LABEL'
    n.signal(event,'route',source_class='human_correction',refs=[input_ref,label_ref],task_success=0.)
    assert candidate.preview(n,r.session,event,[1.,0.])['status']=='NO_UNAMBIGUOUS_TYPED_OUTCOME'


def test_revoked_label_source_and_invalid_embedding_fail_closed(runtime):
    r=runtime;event=turn(r);input_ref,label_ref=correction(r,event)
    n=Neuromod(r.store);emit(n,event,input_ref,label_ref,0.)
    with pytest.raises(ValueError,match='embedding'):
        candidate.preview(n,r.session,event,[float('nan'),0.])
    with r.store.tx() as c:c.execute('UPDATE sources SET deleted=1 WHERE id=?',(label_ref['source_id'],))
    with pytest.raises(ValueError):candidate.preview(n,r.session,event,[1.,0.])


def test_active_mode_is_not_silently_used(runtime):
    r=runtime;event=turn(r);correction(r,event)
    n=Neuromod(r.store);n.set_local_mode('ACTIVE','EXPLICIT_HUMAN')
    assert candidate.preview(n,r.session,event,[1.,0.])=={'status':'ACTIVE_MODE_UNSUPPORTED','training_authority':0}


def test_changed_worker_source_pin_rejects_preview(runtime,monkeypatch):
    r=runtime;event=turn(r);correction(r,event)
    monkeypatch.setitem(candidate.PINS,'learning_worker.py','0'*64)
    with pytest.raises(ValueError,match='source changed'):
        candidate.preview(Neuromod(r.store),r.session,event,[1.,0.])
