"""Run192 isolated B3-H4/H5/H9 packet/paired-window authority guard candidate.

NOT imported by production Runtime or Callosum. A result marked 'ON' here is
only a diagnostic software decision, never a production LATENT grant. The
existing frozen native L1 FAIL and B3 degradation ladder remain authoritative.

Python's json.loads accepts NaN/Infinity by default (docs.python.org/3/library/
json.html); comparisons with NaN do not establish receiver compatibility.
The candidate rejects nonfinite and malformed fields *before* invoking the
existing B3 calibration helper. A trusted caller must supply receiver kind;
a packet may not self-declare dense to bypass MoE router thresholds.
"""
import math

from v13 import b3calibration as B

REVISION='RUN192_B3_GUARD_CANDIDATE_V1'
CHANNELS=('LATENT','NO_MESSAGE','SOURCE_EXACT','CONTROL','SYMBOLIC')
SIMPLER=CHANNELS[1:]
FALLBACKS=SIMPLER


def finite_number(value):
    return type(value) in (int,float) and math.isfinite(value)


def packet_reasons(cal,receiver_revision,sender_revision,expected_receiver_kind):
    if not isinstance(cal,dict):
        return ['CALIBRATION_NOT_OBJECT']
    why=['FIELD_MISSING:'+k for k in B.REQUIRED if k not in cal]
    if cal.get('receiver_kind') not in B.KINDS:
        why.append('RECEIVER_KIND_INVALID')
    if expected_receiver_kind not in B.KINDS or cal.get('receiver_kind')!=expected_receiver_kind:
        why.append('RECEIVER_KIND_UNBOUND')
    for k in ('body_pair_id','sender_revision','receiver_revision','target_tap_id',
              'calibration_dataset_id','valid_until_revision'):
        if not isinstance(cal.get(k),str) or not cal[k].strip():
            why.append('IDENTITY_INVALID:'+k)
    if type(cal.get('injection_level')) is not int or not 1<=cal['injection_level']<=4:
        why.append('INJECTION_LEVEL_INVALID')
    if type(cal.get('sample_count')) is not int or cal['sample_count']<B.MIN_SAMPLES:
        why.append('SAMPLE_COUNT_INVALID')
    positive=('native_norm_mean','norm_ratio')
    nonnegative=('native_norm_std','message_norm','mean_shift','variance_ratio',
                 'geometry_error','calibration_confidence','latency_cost','memory_cost')
    finite=('downstream_utility',)
    for k in positive+nonnegative+finite:
        x=cal.get(k)
        if not finite_number(x):
            why.append('NONFINITE_OR_UNMEASURED:'+k)
        elif k in positive and x<=0:
            why.append('NOT_POSITIVE:'+k)
        elif k in nonnegative and x<0:
            why.append('NEGATIVE:'+k)
    for k in ('geometry_error','calibration_confidence','expert_flip_rate'):
        x=cal.get(k)
        if finite_number(x) and x>1:
            why.append('ABOVE_ONE:'+k)
    for k in ('router_kl','expert_flip_rate','residual_norm_shift',
              'receiver_loss_delta','attention_shift','manifold_distance'):
        x=cal.get(k)
        if x is not None and (not finite_number(x) or
                              (k in ('router_kl','expert_flip_rate','residual_norm_shift') and x<0)):
            why.append('INVALID_OPTIONAL:'+k)
    if not why:
        valid,reasons=B.validity(cal,receiver_revision,sender_revision)
        if not valid:why.extend(reasons)
    return why


def _off(reasons,fallback='SOURCE_EXACT'):
    return {'latent':'OFF','reasons':list(reasons),
            'fallback':fallback if fallback in FALLBACKS else 'NO_MESSAGE',
            'authority_may_increase':False,
            'candidate_only':True,'production_activation_authorized':False,
            'revision':REVISION}


def safe_gate(cal,receiver_revision,*,sender_revision,expected_receiver_kind,
              ood_ok=None,thresholds=None,latent_utility=None,
              fallback_utility=None,fallback='SOURCE_EXACT'):
    """Fail-closed diagnostic. Never changes B3 state or production authority."""
    if fallback not in FALLBACKS:
        return _off(['FALLBACK_UNREGISTERED'],fallback)
    why=packet_reasons(cal,receiver_revision,sender_revision,expected_receiver_kind)
    if why:return _off(why,fallback)
    if ood_ok is not True:return _off(['OOD_NOT_PROVEN'],fallback)
    if not finite_number(latent_utility) or not finite_number(fallback_utility):
        return _off(['UTILITY_UNMEASURED_OR_NONFINITE'],fallback)
    if expected_receiver_kind=='moe':
        need={'router_kl':'B3.max_router_kl',
              'expert_flip_rate':'B3.max_expert_flip_rate',
              'residual_norm_shift':'B3.max_residual_norm_shift'}
        if not isinstance(thresholds,dict):
            return _off(['MOE_THRESHOLDS_UNCALIBRATED'],fallback)
        bad=[name for field,name in need.items()
             if not finite_number(cal.get(field))
             or not finite_number(thresholds.get(name))
             or thresholds[name]<0]
        if bad:return _off(['MOE_ROUTER_UNCALIBRATED:'+x for x in bad],fallback)
    try:
        decision=B.gate(cal,receiver_revision,sender_revision=sender_revision,
                        ood_ok=True,thresholds=thresholds,
                        latent_utility=latent_utility,
                        fallback_utility=fallback_utility,fallback=fallback)
    except (ValueError,TypeError,KeyError,OverflowError):
        return _off(['CALIBRATION_EVALUATION_INVALID'],fallback)
    if decision.get('latent')!='ON' or decision.get('authority_may_increase') is not True:
        return _off(decision.get('reasons') or ['UTILITY_NOT_ABOVE_FALLBACK'],fallback)
    return dict(decision,candidate_only=True,production_activation_authorized=False,
                revision=REVISION)


def paired_preference(rows,window=B.WINDOW):
    """All four simpler channels must be measured on the SAME distinct events.

    A list of per-event channel values is used rather than independently sliced
    channel arrays. This is still only a synthetic/software proof: real
    source/revision binding and native heldout data are required before use.
    """
    base={'preferred':False,'candidate_only':True,
          'production_activation_authorized':False,'n':0}
    if type(window) is not int or window<2 or not isinstance(rows,(list,tuple)):
        return dict(base,reason='INVALID_WINDOW')
    if len(rows)<window:
        return dict(base,n=len(rows),reason='VALIDATION_WINDOW_TOO_SHORT')
    selected=rows[-window:];seen=set();values={c:[] for c in CHANNELS}
    for row in selected:
        if not isinstance(row,dict):
            return dict(base,reason='INVALID_PAIRED_ROW')
        eid=row.get('event_id');utility=row.get('utility')
        if not isinstance(eid,str) or not eid.strip() or eid in seen:
            return dict(base,reason='DUPLICATE_OR_MISSING_EVENT_ID')
        seen.add(eid)
        if not isinstance(utility,dict) or any(not finite_number(utility.get(c)) for c in CHANNELS):
            return dict(base,reason='BASELINE_MISSING_OR_NONFINITE')
        for c in CHANNELS:values[c].append(utility[c])
    against={c:B.paired_win(values['LATENT'],values[c]) for c in SIMPLER}
    preferred=all(result['n']==window and result['wins'] for result in against.values())
    return dict(base,preferred=preferred,n=window,against=against,
                reason=None if preferred else 'DOES_NOT_BEAT_ALL_BASELINES')
