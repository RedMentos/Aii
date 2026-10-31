"""Default-OFF real USER Store JEF-span -> C3 formatter postgen SHADOW guard.

The callback is trusted and may have external side effects; this is NOT a
sandbox, production delivery gate, native proof or approval receipt. No model
is called by this module except through an explicitly opted-in callback.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from .common import dumps
from .jef_span_budget_shadow_candidate import build_jef_span_budget_shadow
from .jef_b1b2_c3_role_postgen_shadow_candidate import _epoch, _parse

SCHEMA = 'v13.jef_span_c3_postgen_shadow.v1'
PASS = 'SHADOW_REAL_STORE_JEF_C3_FORMATTER_MATCH'


def _base(status, **extra):
    return {
        'schema': SCHEMA, 'status': status,
        'callback_invoked': False, 'source_rechecked': False,
        'formatter_match_shadow': False,
        'native_proof': False, 'native_c2_proven': False,
        'native_jef_proven': False, 'body_model_quote_verified': False,
        'output_committed': False, 'tool_dispatches': 0,
        'delivery_authority': 0, 'learning_authority': 0,
        'age0': 'RECORD_ONLY', 'step2_exit': 'EVIDENCE_NOT_PASSING',
        'b3': 'NO_PROMOTION', 'body_jepa': 'UNAVAILABLE',
        'jepa_weight': 0, 'redmi_measured': False,
        'whole_system_complete': False, **extra,
    }


def evaluate(runtime, prior_event, current_event, generator, *,
             operator_opt_in=False, callback_opt_in=False,
             approval_receipt=None):
    """Strictly check one trusted callback against exact Store JEF candidate.

    No output is delivered. A passing callback may be a recorded native output,
    synthetic test double, or separately authorized runner; this function
    does not independently establish native inference provenance.
    """
    if operator_opt_in is not True or callback_opt_in is not True:
        return _base('OFF')
    if approval_receipt is not None:
        return _base('REAL_TTY_APPROVAL_UNSUPPORTED_RED')
    if not callable(generator):
        return _base('INVALID_GENERATOR_RED')
    try:
        before = build_jef_span_budget_shadow(
            runtime, prior_event, current_event, operator_opt_in=True)
        if before.get('status') != 'SHADOW_SOURCE_BOUND_JEF_BUDGET_VERIFIED':
            return _base('SOURCE_PREFLIGHT_RED',
                         component_status=before.get('status'))
        prompt = before['messages']
        if (type(prompt) is not list or len(prompt) != 2
                or [m.get('role') for m in prompt] != ['system', 'user']
                or before['messages_sha256'] != hashlib.sha256(
                    dumps(prompt).encode('utf-8')).hexdigest()
                or before.get('candidate_authority') != 0
                or before.get('output_committed') is not False
                or before.get('delivery_authority') != 0
                or before.get('learning_authority') != 0):
            return _base('PROMPT_INTEGRITY_RED')
        payload = json.loads(prompt[1]['content'])
        candidate = before['typed_jef_candidate']
        if (type(candidate) is not dict
                or set(candidate) != {'choice', 'remaining'}
                or candidate['choice'] not in ('A', 'B', 'NONE')
                or (candidate['choice'] == 'NONE') !=
                (candidate['remaining'] is None)
                or (candidate['remaining'] is not None and
                    (type(candidate['remaining']) is not int or
                     candidate['remaining'] < 0))
                or payload.get('typed_jef_candidate') != candidate
                or payload.get('candidate_authority') != 0
                or payload.get('candidate_origin') !=
                'DETERMINISTIC_EXACT_USER_SOURCE_RECIPE_NOT_MODEL'):
            return _base('TYPED_PAYLOAD_INTEGRITY_RED')
        epoch = _epoch(runtime.store)
        frozen = dumps(before)
        frozen_prompt = dumps(prompt)
    except Exception:
        return _base('SOURCE_PREFLIGHT_INTEGRITY_RED')
    messages = deepcopy(prompt)
    try:
        raw = generator(messages)
    except Exception as exc:
        return _base('CALLBACK_EXCEPTION_RED', callback_invoked=True,
                     error_type=type(exc).__name__)
    try:
        if dumps(messages) != frozen_prompt:
            return _base('CALLBACK_PROMPT_MUTATED_RED', callback_invoked=True)
        if _epoch(runtime.store) != epoch:
            return _base('CALLBACK_STORE_CHANGED_RED', callback_invoked=True)
        after = build_jef_span_budget_shadow(
            runtime, prior_event, current_event, operator_opt_in=True)
        if dumps(after) != frozen or _epoch(runtime.store) != epoch:
            return _base('POSTGEN_SOURCE_CHANGED_RED', callback_invoked=True)
        metadata = {
            'callback_invoked': True, 'source_rechecked': True,
            'messages_sha256': before['messages_sha256'],
            'source_refs': before['source_refs'],
        }
        parsed = _parse(raw)
        if parsed is None:
            return _base('FORMATTER_JSON_RED', **metadata)
        if parsed != candidate:
            return _base('FORMATTER_CANDIDATE_MISMATCH_RED', **metadata)
        return _base(PASS, formatter_match_shadow=True,
                     output_sha256=hashlib.sha256(raw.encode('utf-8')).hexdigest(),
                     output_bytes=len(raw.encode('utf-8')), **metadata)
    except Exception:
        return _base('POSTGEN_INTEGRITY_RED', callback_invoked=True)
