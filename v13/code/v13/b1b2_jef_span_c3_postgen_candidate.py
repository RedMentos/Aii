"""Default-OFF B1/B2 persisted hypotheses + Store JEF + ContextOS C3 postgen.

A caller-supplied generator is TRUSTED and may have side effects. This is not
a sandbox, production delivery path, approval receipt or native-model proof.
Only a source-bound, non-delivering SHADOW integrity result is returned.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from .b1b2_c3_source_envelope_candidate import build_c3_source_envelope
from .b1b2_jef_c3_source_role_bridge_candidate import _read_bound_shadow_plan
from .b1b2_jef_span_c3_bridge_candidate import (
    build_b1b2_jef_span_c3_bridge,
)
from .common import dumps
from .context_os import controller
from .jef_b1b2_c3_role_postgen_shadow_candidate import _epoch, _parse
from .jef_span_budget_shadow_candidate import build_jef_span_budget_shadow
from .two_source_pointer_shadow_candidate import bind_two_source

SCHEMA = 'v13.b1b2_jef_span_c3_postgen_shadow.v1'
PASS = 'SHADOW_B1B2_JEF_CONTEXTOS_C3_FORMATTER_MATCH'


def _result(status, **extra):
    return {
        'schema': SCHEMA, 'status': status,
        'callback_invoked': False, 'source_rechecked': False,
        'formatter_match_shadow': False, 'native_proof': False,
        'native_b1_proven': False, 'native_b2_proven': False,
        'native_c2_proven': False, 'native_jef_proven': False,
        'native_c3_proven': False, 'body_model_quote_verified': False,
        'body_hypotheses_are_facts': False,
        'source_semantic_truth_authority': False,
        'output_committed': False, 'tool_dispatches': 0,
        'delivery_authority': 0, 'learning_authority': 0,
        'age0': 'RECORD_ONLY', 'step2_exit': 'EVIDENCE_NOT_PASSING',
        'b3': 'NO_PROMOTION', 'body_jepa': 'UNAVAILABLE',
        'jepa_weight': 0, 'redmi_measured': False,
        'whole_system_complete': False, **extra,
    }


def evaluate(runtime, prior_event, current_event, offer_packet_ids, generator,
             *, operator_opt_in=False, callback_opt_in=False,
             approval_receipt=None):
    """Validate one trusted callback without delivering its output.

    No model is invoked here except via the explicitly opted-in callback.
    Passing does not prove model provenance, reasoning or Body complementarity.
    """
    if operator_opt_in is not True or callback_opt_in is not True:
        return _result('OFF')
    if approval_receipt is not None:
        return _result('REAL_TTY_APPROVAL_UNSUPPORTED_RED')
    if not callable(generator):
        return _result('INVALID_GENERATOR_RED')
    try:
        bridge = build_b1b2_jef_span_c3_bridge(
            runtime, prior_event, current_event, offer_packet_ids,
            operator_opt_in=True)
        if bridge.get('status') != 'SHADOW_B1B2_JEF_SPAN_C3_BRIDGE_VERIFIED':
            return _result('SOURCE_PREFLIGHT_RED',
                           component_status=bridge.get('status'))
        prompt = bridge['messages']
        if (type(prompt) is not list or len(prompt) != 2
                or any(type(m) is not dict or set(m) != {'role', 'content'}
                       or type(m['content']) is not str for m in prompt)
                or [m['role'] for m in prompt] != ['system', 'user']
                or bridge.get('messages_sha256') != hashlib.sha256(
                    dumps(prompt).encode('utf-8')).hexdigest()
                or bridge.get('output_committed') is not False
                or bridge.get('delivery_authority') != 0
                or bridge.get('learning_authority') != 0
                or bridge.get('body_model_quote_verified') is not False
                or bridge.get('body_hypotheses_are_facts') is not False
                or bridge.get('source_semantic_truth_authority') is not False):
            return _result('PROMPT_INTEGRITY_RED')
        payload = json.loads(prompt[1]['content'])
        candidate = bridge['typed_jef_candidate']
        refs = bridge['source_refs']
        plan_id = bridge['context_plan_packet_id']
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
                'DETERMINISTIC_EXACT_USER_SOURCE_RECIPE_NOT_MODEL'
                or payload.get('body_hypotheses_are_facts') is not False
                or payload.get('body_model_quote_verified') is not False
                or payload.get('source_semantic_truth_authority') is not False
                or payload.get('context_plan_packet_id') != plan_id
                or type(refs) is not list or len(refs) != 2):
            return _result('TYPED_PAYLOAD_INTEGRITY_RED')
        bound = bind_two_source(runtime, prior_event, current_event,
                                operator_opt_in=True)
        body = build_c3_source_envelope(
            runtime, current_event, offer_packet_ids, operator_opt_in=True)
        jef = build_jef_span_budget_shadow(
            runtime, prior_event, current_event, operator_opt_in=True)
        plan = _read_bound_shadow_plan(runtime, plan_id, current_event, refs)
        jef_payload = json.loads(jef['messages'][1]['content'])
        body_payload = json.loads(body['messages'][1]['content'])
        if (bound.get('status') != 'SHADOW_TWO_SOURCE_POINTER_VERIFIED'
                or [s['source_ref'] for s in bound['sources']] != refs
                or body.get('status') !=
                'C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL'
                or body.get('offer_packet_ids') != offer_packet_ids
                or body_payload.get('body_observations') !=
                payload.get('body_observations')
                or body.get('verified_quote_count') !=
                payload.get('verified_quote_count')
                or jef.get('status') !=
                'SHADOW_SOURCE_BOUND_JEF_BUDGET_VERIFIED'
                or jef.get('typed_jef_candidate') != candidate
                or jef_payload.get('policy') != payload.get('policy')
                or jef_payload.get('options') != payload.get('options')
                or jef.get('source_refs') != refs
                or plan is None
                or controller(runtime)._load()[0]['mode'] != 'SHADOW'):
            return _result('PREFLIGHT_LINEAGE_RED')
        epoch = _epoch(runtime.store)
        frozen = (dumps(prompt), dumps(bound), dumps(body), dumps(jef),
                  plan, dumps(prior_event), dumps(current_event),
                  dumps(offer_packet_ids))
    except Exception:
        return _result('SOURCE_PREFLIGHT_INTEGRITY_RED')

    messages = deepcopy(prompt)
    try:
        raw = generator(messages)
    except Exception as exc:
        return _result('CALLBACK_EXCEPTION_RED', callback_invoked=True,
                       error_type=type(exc).__name__)
    try:
        if dumps(messages) != frozen[0]:
            return _result('CALLBACK_PROMPT_MUTATED_RED',
                           callback_invoked=True)
        if (dumps(prior_event), dumps(current_event),
                dumps(offer_packet_ids)) != frozen[5:]:
            return _result('CALLBACK_INPUT_MUTATED_RED',
                           callback_invoked=True)
        if _epoch(runtime.store) != epoch:
            return _result('CALLBACK_STORE_CHANGED_RED',
                           callback_invoked=True)
        after_bound = bind_two_source(
            runtime, prior_event, current_event, operator_opt_in=True)
        after_body = build_c3_source_envelope(
            runtime, current_event, offer_packet_ids, operator_opt_in=True)
        after_jef = build_jef_span_budget_shadow(
            runtime, prior_event, current_event, operator_opt_in=True)
        after_plan = _read_bound_shadow_plan(
            runtime, plan_id, current_event, refs)
        if (dumps(after_bound) != frozen[1]
                or dumps(after_body) != frozen[2]
                or dumps(after_jef) != frozen[3]
                or after_plan != frozen[4]
                or controller(runtime)._load()[0]['mode'] != 'SHADOW'
                or _epoch(runtime.store) != epoch):
            return _result('POSTGEN_SOURCE_OFFER_PLAN_CHANGED_RED',
                           callback_invoked=True)
        meta = {'callback_invoked': True, 'source_rechecked': True,
                'messages_sha256': bridge['messages_sha256'],
                'source_refs': refs, 'context_plan_packet_id': plan_id,
                'offer_packet_ids': dict(offer_packet_ids)}
        parsed = _parse(raw)
        if parsed is None:
            return _result('FORMATTER_JSON_RED', **meta)
        if parsed != candidate:
            return _result('FORMATTER_CANDIDATE_MISMATCH_RED', **meta)
        return _result(
            PASS, formatter_match_shadow=True,
            output_sha256=hashlib.sha256(raw.encode('utf-8')).hexdigest(),
            output_bytes=len(raw.encode('utf-8')), **meta)
    except Exception:
        return _result('POSTGEN_INTEGRITY_RED', callback_invoked=True)
