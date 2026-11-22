"""Run42: read-only source-exact B2 history -> fixed eligibility SHADOW.

Never a Runtime route, tool dispatch, native inference, or authorized answer.
Every rule and option comes from a Store.read_source-verified original span.
"""
from __future__ import annotations

from scripts import run40_b2_store_history_readonly as history
from scripts import run12_b2_context_identity_candidate as identity
from v13.agi import eligibility

REVISION = 'run42-b2-eligibility-source-shadow-v1'


def _base(status):
    return {'revision': REVISION, 'status': status, 'decision': None,
            'source_refs': [], 'authority': 'SHADOW_NO_AUTHORITY',
            'native_executed': False, 'canonical_gate_pass': False,
            'phone_measured': False, 'jepa_weight': 0,
            'whole_system_complete': False}


def _options(text):
    a = eligibility.fixed_option('A', text)
    b = eligibility.fixed_option('B', text)
    return [a, b] if a is not None and b is not None else None


def evaluate(store, current_event, session, generation, model_revision, *, scan_limit=32):
    """Evaluate a deterministic decision in SHADOW; no output or tool authority."""
    past = history.collect_history(store, current_event, session, generation,
                                   model_revision, limit=scan_limit)
    current_ref = current_event['source_ref']
    current = store.read_source(current_ref)
    names = identity.named_entities(current)
    if len(names) != 1:
        return _base('ABSTAIN_PROJECT_IDENTITY')
    from scripts import run39_b2_rule_span_candidate as rule_selector
    rule = rule_selector.select_rule_span(
        current, current_event['event_id'], session, generation, model_revision,
        past, store.read_source, scan_limit=scan_limit)
    if len(rule['items']) != 1:
        return _base('ABSTAIN_RULE_SOURCE')
    rule_item = rule['items'][0]
    rule_text = store.read_source(rule_item['source_ref'])
    if rule_text != rule_item['native_context']['exact_source_excerpt']:
        return _base('ABSTAIN_RULE_CHANGED')
    options = []
    # Current text is authoritative over older option sheets if it states both.
    for ref in [current_ref, *(x['source_ref'] for x in past)]:
        if ref['source_id'] == rule_item['source_ref']['source_id']:
            continue
        try:
            text = store.read_source(ref)
            if identity.named_entities(text) != names:
                continue
            parsed = _options(text)
            if parsed is not None:
                options.append((ref, text, parsed))
        except (ValueError, OSError, KeyError):
            continue
    if not options:
        return _base('ABSTAIN_OPTION_SOURCE')
    if options[0][0]['source_id'] != current_ref['source_id']:
        # No current options: conflicting older sheets cannot silently win by recency.
        if any(row[2] != options[0][2] for row in options[1:]):
            return _base('ABSTAIN_CONFLICTING_OPTION_SOURCES')
    option_ref, option_text, parsed = options[0]
    rules = {name: eligibility.fixed_rule(name, rule_text)
             for name in ('budget', 'deadline', 'local_only')}
    if any(v is None for v in rules.values()):
        return _base('ABSTAIN_INCOMPLETE_RULES')
    # The option scan intentionally tolerates unavailable historical refs.
    # A revoked/changed *current* source is different: stale current text
    # must never authorize even a SHADOW decision using older option sheets.
    try:
        if store.read_source(current_ref) != current:
            return _base('ABSTAIN_CURRENT_SOURCE_CHANGED')
    except (ValueError, OSError, KeyError):
        return _base('ABSTAIN_CURRENT_SOURCE_CHANGED')
    decision = eligibility.decide(rules, parsed, current,
                                  quotes=(rule_text, option_text))
    if decision['action'] == 'UNKNOWN' or decision['rejected']:
        status = 'ABSTAIN_CONFLICT_OR_UNSUPPORTED'
    else:
        status = 'SHADOW_DETERMINISTIC_DECISION_NO_OUTPUT'
    out = _base(status)
    out['decision'] = decision
    out['source_refs'] = [rule_item['source_ref'], option_ref]
    return out
