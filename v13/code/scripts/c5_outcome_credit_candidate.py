"""Isolated source-bound candidate for C5 outcome credit.

This module is not imported or activated by the runtime. It produces bytes for
an independent test copy only; the original runtime and its frozen cohorts are
never modified. Integrating these changes requires a new, reviewed cohort.
"""
from hashlib import sha256
from pathlib import Path


BASE_SHA256 = {
    'runtime.py': '8a403bffd1c2b14d9caa798cf17ea3c299cea5796115bad40cbaf9a2054072ed',
    'neuromod.py': 'abd6379bd8843b2e763fea315ea78dfbb5142ee03d4b71eae3b33a48c018c86d',
}
DEPENDENCY_SHA256 = {
    # The narrow legacy exceptions below rely on these exact producers.
    'world.py': 'bb221176167cb1f83285127cba2b2e059ebf9b0cec79b9405b3b5f23cef0343e',
    'learning.py': '6776dd82eb2604f7fb2c17a9773911df73fbf4f672d7c533ed15135987cfa53c',
}

_RUNTIME_OLD = b"eid,task_success=1. if status=='FINAL' else 0.,cost_error="
_RUNTIME_NEW = b"eid,cost_error="

_CHANNELS_OLD = b'''    ch={k:clamp(v,-1.,1.) for k,v in (p.get('channels') or {}).items() if k in CHANNELS}
    legacy={'evidence_gain':p.get('epistemic_evidence'),'human_correction':p.get('human_correction'),
            'task_success':p.get('task_success'),'cost_error':p.get('resource_cost'),'world_prediction_error':p.get('digital_prediction_error')}
'''
_CHANNELS_NEW = b'''    # Explicit typed channels define presence; the required legacy numeric
    # defaults do not mean that a missing outcome was measured as failure.
    typed='channels' in p
    if typed:
        channels=p['channels']
        if not isinstance(channels,dict):raise ValueError('Neuromod: channels must be a dict')
        ch={k:clamp(v,-1.,1.) for k,v in channels.items() if k in CHANNELS}
    else:ch={}
    legacy={'evidence_gain':p.get('epistemic_evidence'),'human_correction':p.get('human_correction'),
            'task_success':p.get('task_success'),'cost_error':p.get('resource_cost'),'world_prediction_error':p.get('digital_prediction_error')}
    # Existing source-bound legacy producers explicitly say their mandatory
    # task_success=0 is a placeholder, not an observed negative reward.
    no_reward={
        ('F4_WORLD','measured own digital outcome; no semantic truth reward or automatic weight permission'),
        ('F6_LEARNING','measured native state target; no semantic truth label'),
        ('F4_LEARNING','human label present; task success and cost not optimizer rewards'),
    }
    identity=(p.get('producer_component'),p.get('values_status'))
    if identity in no_reward:legacy.pop('task_success')
    if identity==('F4_LEARNING','human label present; task success and cost not optimizer rewards'):
        legacy.pop('cost_error')
    # This exact F6 producer emits a literal zero, not a measured cost. A
    # nonzero legacy value is retained because older producers are unpinned.
    if (identity==('F6_LEARNING','measured native state target; no semantic truth label')
            and legacy.get('cost_error')==0.):legacy.pop('cost_error')
    # N10 mirrors four required legacy fields; if a typed key is absent its
    # mirrored field is not independent evidence. Optional digital prediction
    # error is not mirrored and retains its ordinary legacy fallback.
    if typed and p.get('producer_component')=='N10_NEUROMOD':
        for key in ('evidence_gain','human_correction','task_success','cost_error'):
            if key not in ch:legacy.pop(key)
'''


def build_sources(source_dir):
    """Return reviewed candidate bytes without writing or changing imports."""
    source_dir = Path(source_dir)
    out = {}
    for name, expected in DEPENDENCY_SHA256.items():
        if sha256((source_dir / name).read_bytes()).hexdigest() != expected:
            raise ValueError('unsupported producer source: ' + name)
    changes = {
        'runtime.py': (_RUNTIME_OLD, _RUNTIME_NEW),
        'neuromod.py': (_CHANNELS_OLD, _CHANNELS_NEW),
    }
    for name, (before, after) in changes.items():
        content = (source_dir / name).read_bytes()
        if sha256(content).hexdigest() != BASE_SHA256[name]:
            raise ValueError('unsupported source: ' + name)
        if content.count(before) != 1:
            raise ValueError('ambiguous source anchor: ' + name)
        out[name] = content.replace(before, after, 1)
    return out
