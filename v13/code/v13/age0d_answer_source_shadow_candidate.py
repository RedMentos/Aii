"""WP-AGE0d read-only answer-sees-source late verifier, default OFF.

Narrow deterministic budget/arithmetic domains only. This is an isolated
SHADOW candidate, not wired to SelfSystem, late_correction delivery, C3,
training, output or any Age gate. Source and answer text are never returned.
"""
from __future__ import annotations

import json
import re

from .common import digest, dumps

REVISION = 'age0d-answer-source-shadow-run113-v1'
BUDGET_SOURCE = re.compile(
    r'\bProject\s+([A-Za-z]+)\s+budget:\s*(\d{1,8})\s+Euro\b', re.I)
BUDGET_ANSWER = re.compile(
    r'\bThe\s+budget\s+for\s+Project\s+([A-Za-z]+)\s+is\s+(\d{1,8})\s+Euros?\b', re.I)
CALCULATE_SOURCE = re.compile(
    r'\bCalculate\s+(\d{1,5})\s*([+*])\s*(\d{1,5})\s*\.', re.I)
CALCULATE_ANSWER = re.compile(
    r'\b(\d{1,5})\s*([+*])\s*(\d{1,5})\s*=\s*(\d{1,9})\b')


def _receipt(verdict, *, source_ref=None, kind=None, expected=None, observed=None):
    result = {
        'schema': 'v13.age0d.answer_source_shadow.v1',
        'revision': REVISION, 'verdict': verdict,
        'source_ref_sha256': source_ref.get('sha256') if type(source_ref) is dict else None,
        'claim_kind': kind, 'evidence_sha256': None,
        'native_model_called': False, 'tool_dispatches': 0,
        'delivery_authority': 0, 'learning_authority': 0,
        'output_committed': False, 'age0': 'RECORD_ONLY',
        'step2': 'UTILITY_FAIL', 'b3': 'NO_PROMOTION',
        'body_jepa': 'UNAVAILABLE', 'jepa_weight': 0,
        'whole_system_complete': False,
    }
    if kind is not None and expected is not None and observed is not None:
        result['evidence_sha256'] = digest(
            dumps([kind, int(expected), int(observed)]).encode())
    return result


def _check(source, answer):
    source_budget = list(BUDGET_SOURCE.finditer(source))
    answer_budget = list(BUDGET_ANSWER.finditer(answer))
    if source_budget or answer_budget:
        if len(source_budget) != 1 or len(answer_budget) != 1:
            return 'ABSTAIN', None, None, None
        src, ans = source_budget[0], answer_budget[0]
        if src.group(1).casefold() != ans.group(1).casefold():
            return 'ABSTAIN', None, None, None
        expected, observed = int(src.group(2)), int(ans.group(2))
        return ('NO_SIGNAL' if expected == observed else 'CONTRADICTION',
                'PROJECT_BUDGET', expected, observed)
    source_math = list(CALCULATE_SOURCE.finditer(source))
    answer_math = list(CALCULATE_ANSWER.finditer(answer))
    if source_math or answer_math:
        if len(source_math) != 1 or len(answer_math) != 1:
            return 'ABSTAIN', None, None, None
        src, ans = source_math[0], answer_math[0]
        if src.group(1, 2, 3) != ans.group(1, 2, 3):
            return 'ABSTAIN', None, None, None
        a, op, b = int(src.group(1)), src.group(2), int(src.group(3))
        expected = a + b if op == '+' else a * b
        observed = int(ans.group(4))
        return ('NO_SIGNAL' if expected == observed else 'CONTRADICTION',
                'SOURCE_BOUND_INTEGER_ARITHMETIC', expected, observed)
    return 'ABSTAIN', None, None, None


def check(runtime, event_id, source_ref, answer, *, operator_opt_in=False):
    """Inspect only an explicitly bound current-session Event/SourceRef.

    No database writes, no model call, no messages, no suggestion to user.
    The caller must already hold the normal Runtime/Store coordinator lock.
    """
    if operator_opt_in is not True:
        return _receipt('OFF')
    if (type(event_id) is not str or not event_id
            or type(source_ref) is not dict or type(answer) is not str
            or not 0 < len(answer) <= 4096
            or not {'source_id','sha256','char_start','char_end','modality'} <= set(source_ref)
            or source_ref.get('modality') != 'text'
            or type(source_ref.get('char_start')) is not int
            or type(source_ref.get('char_end')) is not int
            or source_ref.get('char_start') != 0):
        return _receipt('SOURCE_RED')
    try:
        row = runtime.store.one(
            'SELECT session_id,packet FROM events WHERE id=?', (event_id,))
        if not row or row['session_id'] != runtime.session:
            return _receipt('SOURCE_RED')
        packet = json.loads(row['packet'])
        if packet.get('source_ref') != source_ref or packet.get('kind') != 'USER_TEXT':
            return _receipt('SOURCE_RED')
        source = runtime.store.read_source(source_ref)
        if len(source) > 4096:
            return _receipt('ABSTAIN', source_ref=source_ref)
    except Exception:
        return _receipt('SOURCE_RED')
    verdict, kind, expected, observed = _check(source, answer)
    return _receipt(verdict, source_ref=source_ref,
                    kind=kind, expected=expected, observed=observed)
