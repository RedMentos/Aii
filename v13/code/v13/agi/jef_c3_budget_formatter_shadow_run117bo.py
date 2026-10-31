"""Run117BO default-OFF exact Store JEF -> C3 choice+remaining formatter SHADOW.

The native C3 350M Run117BM selected wrong choices/remaining. Here JEF's
existing deterministic recipe decides from two exact USER SourceRefs; C3 is
only an untrusted JSON copier. No live Runtime wiring or delivery permission.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from .jef_eligibility_source_shadow_run46b import propose, _digest
from ..common import dumps

REVISION = 'v13-run117bo-jef-c3-budget-formatter-shadow-v1'
SCHEMA = {'type': 'object', 'additionalProperties': False,
          'required': ['choice', 'remaining'],
          'properties': {'choice': {'type': 'string', 'enum': ['A', 'B', 'NONE', 'UNKNOWN']},
                         'remaining': {'type': ['integer', 'null']}}}
SYSTEM = ('You are a JSON formatter, not a decision maker. Copy the supplied '
          'source-verified typed JEF candidate exactly. Do not infer rules, '
          'recalculate, or invent remaining budget. Return only JSON with '
          'choice and remaining. For NONE or UNKNOWN remaining must be null.')
MAX_OUTPUT_BYTES = 512


def _sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _epoch(store):
    db = store.db
    return (db.total_changes, db.execute('PRAGMA data_version').fetchone()[0],
            db.in_transaction, store.generation_id)


def _pair(store, session, prior_ref, current_ref):
    """Two most recent authoritative USER events in this session and generation."""
    if type(session) is not str or not session or type(prior_ref) is not dict or type(current_ref) is not dict:
        raise ValueError('SOURCE_INPUT_RED')
    rows = store.rows('SELECT id,source_id,generation_id,packet FROM events '
                      'WHERE session_id=? ORDER BY rowid DESC LIMIT 64', (session,))
    user = []
    for row in rows:
        packet = json.loads(row['packet'])
        if packet.get('kind') == 'USER_TEXT' and packet.get('authority') == 'AUTHORITATIVE':
            user.append((row, packet))
            if len(user) == 2:
                break
    if len(user) != 2:
        raise ValueError('LATEST_TWO_USER_EVENTS_RED')
    for (row, packet), ref in zip(user, (current_ref, prior_ref)):
        if (row['source_id'] != ref.get('source_id') or row['generation_id'] != store.generation_id
                or packet.get('event_id') != row['id'] or packet.get('source_ref') != ref
                or packet.get('provenance') != [ref]
                or packet.get('brain_generation_id') != row['generation_id']):
            raise ValueError('EVENT_SOURCE_LINEAGE_RED')
    return (user[1][0]['id'], user[0][0]['id'])


def _candidate(store, session, prior_ref, current_ref):
    events = _pair(store, session, prior_ref, current_ref)
    result = propose(store, prior_ref, current_ref)
    value = result.get('candidate')
    if (result.get('reason') != 'EXACT_USER_SOURCE_RECIPE_SHADOW'
            or result.get('status') != 'SHADOW_NO_AUTHORITY'
            or result.get('authority') != 0 or result.get('model_called') is not False
            or result.get('source_ref_sha256') != [_digest(prior_ref), _digest(current_ref)]
            or type(value) is not dict or set(value) != {'choice', 'remaining'}):
        raise ValueError('JEF_SOURCE_RECIPE_RED')
    choice, remaining = value['choice'], value['remaining']
    if (type(choice) is not str or choice not in ('A', 'B', 'NONE', 'UNKNOWN')
            or (choice in ('NONE', 'UNKNOWN') and remaining is not None)
            or (choice in ('A', 'B') and (type(remaining) is not int or remaining < 0))):
        raise ValueError('JEF_TYPED_CANDIDATE_RED')
    if _pair(store, session, prior_ref, current_ref) != events:
        raise ValueError('EVENTS_CHANGED_RED')
    return value, events


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('DUPLICATE_JSON_RED')
        out[key] = value
    return out


def _nonfinite(_):
    raise ValueError('NONFINITE_JSON_RED')


def _parse(raw):
    try:
        value = json.loads(raw, object_pairs_hook=_unique, parse_constant=_nonfinite)
    except (ValueError, TypeError, OverflowError):
        return None, 'FORMATTER_JSON_RED'
    if type(value) is not dict or set(value) != {'choice', 'remaining'}:
        return None, 'FORMATTER_JSON_RED'
    choice, remaining = value['choice'], value['remaining']
    if type(choice) is not str or choice not in ('A', 'B', 'NONE', 'UNKNOWN'):
        return None, 'FORMATTER_JSON_RED'
    if ((choice in ('NONE', 'UNKNOWN') and remaining is not None)
            or (choice in ('A', 'B') and (type(remaining) is not int or remaining < 0))):
        return None, 'FORMATTER_SEMANTIC_RED'
    return value, None


def _result(status, **extra):
    return {'revision': REVISION, 'status': status,
            'age0': 'RECORD_ONLY', 'step2': 'UTILITY_FAIL', 'b3': 'NO_PROMOTION',
            'body_jepa': 'UNAVAILABLE', 'world_jepa': 'SHADOW', 'jepa_weight': 0,
            'redmi_measured': False, 'whole_system_complete': False,
            'delivery_authority': 0, 'output_committed': False,
            'tool_dispatches': 0, 'learning_authority': 0,
            'native_proof': False, 'callback_invoked': False,
            'source_rechecked': False, 'source_only_fallback': False, **extra}


def format_shadow(store, session, prior_ref, current_ref, generator,
                  *, operator_opt_in=False, callback_opt_in=False,
                  approval_receipt=None):
    """Strict read-only source recheck before/after callback, no permission token."""
    if operator_opt_in is not True or callback_opt_in is not True:
        return _result('OFF')
    if approval_receipt is not None:
        return _result('REAL_TTY_APPROVAL_UNSUPPORTED')
    if not callable(generator):
        return _result('INVALID_GENERATOR')
    try:
        before_epoch = _epoch(store)
        if before_epoch[2]:
            raise ValueError('ACTIVE_TRANSACTION_RED')
        candidate, events = _candidate(store, session, prior_ref, current_ref)
        messages = [{'role': 'system', 'content': SYSTEM},
                    {'role': 'user', 'content': dumps({
                        'typed_jef_candidate': candidate, 'candidate_authority': 0,
                        'source_ref_sha256': [_digest(prior_ref), _digest(current_ref)]})}]
        prompt = dumps(messages)
        if _epoch(store) != before_epoch:
            raise ValueError('PREFLIGHT_STORE_CHANGED_RED')
    except Exception:
        return _result('SOURCE_PREFLIGHT_RED')
    copied_messages = deepcopy(messages)
    copied_schema = deepcopy(SCHEMA)
    try:
        raw = generator(copied_messages, copied_schema)
    except Exception as exc:
        return _result('CALLBACK_RED', callback_invoked=True,
                       callback_error_type=type(exc).__name__)
    try:
        if dumps(copied_messages) != prompt or copied_schema != SCHEMA:
            return _result('CALLBACK_INPUT_MUTATED_RED', callback_invoked=True)
    except (TypeError, ValueError, OverflowError, UnicodeError):
        return _result('CALLBACK_INPUT_MUTATED_RED', callback_invoked=True)
    try:
        if _epoch(store) != before_epoch:
            return _result('CALLBACK_STORE_MUTATION_RED', callback_invoked=True)
    except Exception:
        return _result('CALLBACK_STORE_MUTATION_RED', callback_invoked=True)
    try:
        after, after_events = _candidate(store, session, prior_ref, current_ref)
        if after != candidate or after_events != events or _epoch(store) != before_epoch:
            raise ValueError('POST_CALLBACK_CHANGED_RED')
    except Exception:
        return _result('POST_CALLBACK_SOURCE_RED', callback_invoked=True)
    base = {'callback_invoked': True, 'source_rechecked': True,
            'candidate_sha256': _sha(dumps(candidate)),
            'prompt_sha256': _sha(prompt),
            'source_ref_sha256': [_digest(prior_ref), _digest(current_ref)]}
    if type(raw) is not str:
        return _result('FORMATTER_OUTPUT_SHAPE_RED', source_only_fallback=True, **base)
    try:
        raw_bytes = raw.encode('utf-8')
    except UnicodeError:
        return _result('FORMATTER_OUTPUT_SHAPE_RED', source_only_fallback=True, **base)
    if not 0 < len(raw_bytes) <= MAX_OUTPUT_BYTES:
        return _result('FORMATTER_OUTPUT_SHAPE_RED', source_only_fallback=True, **base)
    parsed, error = _parse(raw)
    base.update(output_sha256=hashlib.sha256(raw_bytes).hexdigest(),
                output_bytes=len(raw_bytes))
    if error:
        return _result(error, source_only_fallback=True, **base)
    if parsed != candidate:
        return _result('FORMATTER_MISMATCH_RED', source_only_fallback=True, **base)
    return _result('FORMATTER_MATCH_SHADOW', formatter_match=True, **base)
