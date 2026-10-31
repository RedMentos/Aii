"""Run117AI default-OFF event-bound wrapper for frozen Body source-ID selector.

The frozen seed1069 selector/runner is unchanged. This wrapper checks the
authoritative event -> SourceRef edge before a trusted callback and verifies
the persisted zero-authority packet after it. It is not a native proof,
sandbox, production consumer, delivery path, or semantic-truth authority.
"""
from __future__ import annotations

import json

from .b1b2_c3_source_envelope_candidate import _latest_authoritative_user
from .b1b2_source_id_quote_candidate import (
    KIND, select as frozen_select,
)
from .common import dumps
from .f1f5_event_finalizer_candidate import _event_snapshot

SCHEMA = 'v13.body_source_id_event_binding_shadow.v1'
SUCCESSES = {
    'SHADOW_SOURCE_ID_SELECTED': 'SHADOW_EVENT_SOURCE_BOUND_CORRECT',
    'SHADOW_WRONG_SOURCE_ID_RECORDED': 'SHADOW_EVENT_SOURCE_BOUND_WRONG',
    'SHADOW_ABSTAIN_RECORDED': 'SHADOW_EVENT_SOURCE_BOUND_ABSTAIN',
}


def _result(status, **extra):
    return {
        'schema': SCHEMA, 'status': status,
        'callback_invoked': False, 'native_model_proven': False,
        'source_semantic_truth_authority': False,
        'model_hypothesis_not_fact': True,
        'output_committed': False, 'tool_dispatches': 0,
        'delivery_authority': 0, 'learning_authority': 0,
        'age0': 'RECORD_ONLY', 'step2_exit': 'EVIDENCE_NOT_PASSING',
        'b3': 'NO_PROMOTION', 'body_jepa': 'UNAVAILABLE',
        'jepa_weight': 0, 'redmi_measured': False,
        'whole_system_complete': False, **extra,
    }


def _canonical(runtime, event):
    if (type(event) is not dict
            or type(event.get('event_id')) is not str
            or type(event.get('source_ref')) is not dict):
        raise ValueError('EVENT_SHAPE_RED')
    snapshot = _event_snapshot(
        runtime.memory, event['event_id'], runtime.session)
    if (event['source_ref'] != snapshot['ref']
            or event.get('brain_generation_id') != snapshot['generation']
            or _latest_authoritative_user(runtime.store, runtime.session)
            != event['event_id']):
        raise ValueError('EVENT_SOURCE_OR_LATEST_MISMATCH_RED')
    return snapshot


def _packet_ok(runtime, packet_id, event, role, snapshot, result):
    if type(packet_id) is not str or not packet_id:
        return False
    row = runtime.store.one(
        "SELECT event_id,payload FROM packets WHERE id=? AND kind=?",
        (packet_id, KIND))
    if row is None or row['event_id'] != event['event_id']:
        return False
    packet = json.loads(row['payload'])
    if (type(packet) is not dict
            or packet.get('packet_id') != packet_id
            or packet.get('event_id') != event['event_id']
            or packet.get('brain_generation_id') != snapshot['generation']
            or packet.get('role') != role
            or packet.get('source_ref') != snapshot['ref']
            or packet.get('source_refs') != [snapshot['ref']]
            or packet.get('model_revision') != runtime.models.revision(role)
            or packet.get('delivery_authority') != 0
            or packet.get('learning_authority') != 0
            or packet.get('output_committed') is not False
            or packet.get('source_semantic_truth_authority') is not False
            or packet.get('model_hypothesis_not_fact') is not True
            or packet.get('raw_output_sha256') !=
            result.get('raw_output_sha256')
            or packet.get('selection_correct_shadow') is not
            result.get('selection_correct_shadow')):
        return False
    candidates = packet.get('candidates')
    if (type(candidates) is not list or len(candidates) != 2
            or any(type(c) is not dict or set(c) !=
                   {'span_id', 'text', 'source_ref', 'origin'}
                   for c in candidates)):
        return False
    ids = [c['span_id'] for c in candidates]
    if (any(type(i) is not str or not i for i in ids)
            or len(set(ids)) != 2):
        return False
    base = snapshot['ref']
    source = snapshot['query']
    for candidate in candidates:
        ref = candidate['source_ref']
        if type(ref) is not dict:
            return False
        start, end = ref.get('char_start'), ref.get('char_end')
        if (type(start) is not int or type(end) is not int
                or not 0 <= start < end <= len(source)
                or {k: v for k, v in ref.items()
                    if k not in ('char_start', 'char_end')} !=
                {k: v for k, v in base.items()
                    if k not in ('char_start', 'char_end')}
                or candidate['text'] != source[start:end]
                or candidate['origin'] !=
                'STORE_EXACT_USER_NOT_MODEL_QUOTE'
                or runtime.store.read_source(ref) != candidate['text']):
            return False
    selected = packet.get('selected_id')
    if selected not in set(ids) | {'NONE'}:
        return False
    chosen = next((c for c in candidates if c['span_id'] == selected), None)
    expected = (None if chosen is None else
                {k: v for k, v in chosen.items() if k != 'span_id'})
    if (packet.get('selected_span') != expected
            or (selected == 'NONE') !=
            (result.get('status') == 'SHADOW_ABSTAIN_RECORDED')):
        return False
    return True


def select_bound(runtime, event, role, generator, *,
                 operator_opt_in=False, callback_opt_in=False,
                 approval_receipt=None):
    """Source-bound opt-in wrapper; only reports a fallible SHADOW selection."""
    if operator_opt_in is not True or callback_opt_in is not True:
        return _result('OFF')
    if approval_receipt is not None:
        return _result('REAL_TTY_APPROVAL_UNSUPPORTED_RED')
    if not callable(generator):
        return _result('INVALID_GENERATOR_RED')
    try:
        snapshot = _canonical(runtime, event)
        frozen_event = dumps(event)
    except Exception:
        return _result('EVENT_SOURCE_PREFLIGHT_RED')
    try:
        selected = frozen_select(
            runtime, event, role, generator,
            operator_opt_in=True, callback_opt_in=True)
    except Exception:
        return _result('FROZEN_SELECTOR_EXCEPTION_RED')
    invoked = selected.get('model_called') is True
    status = selected.get('status')
    if status not in SUCCESSES:
        return _result('FROZEN_SELECTOR_RED',
                       callback_invoked=invoked, component_status=status)
    try:
        if (dumps(event) != frozen_event
                or _canonical(runtime, event) != snapshot
                or not _packet_ok(runtime, selected.get('packet_id'),
                                  event, role, snapshot, selected)):
            return _result('POST_SELECTION_EVENT_PACKET_RED',
                           callback_invoked=invoked)
        return _result(
            SUCCESSES[status], callback_invoked=invoked,
            source_ref=snapshot['ref'],
            packet_id=selected['packet_id'],
            selected_id=selected['selected_id'],
            model_selection_correct_shadow=(
                selected['selection_correct_shadow']),
            original_component_status=status,
            authoritative_event_source_verified=True)
    except Exception:
        return _result('POST_SELECTION_INTEGRITY_RED',
                       callback_invoked=invoked)
