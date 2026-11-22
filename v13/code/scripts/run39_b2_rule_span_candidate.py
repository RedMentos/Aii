"""Run39: OFF-by-default, source-only B2 historical-rule span selector.

This is a bounded counterfactual candidate, not a Runtime/Store patch. The
caller supplies original persisted B2 offers and a source-integrity-enforcing
read_source callback. Only source-exact spans are returned, with zero authority.
No model, oracle, learning, or original frozen cohort is accessed.
"""
from __future__ import annotations

import re
from collections import Counter

from scripts import run12_b2_context_identity_candidate as base

REVISION = 'run39-b2-rule-span-shadow-v1'
MAX_SCAN = 64
# These are *lexical cues*, not a rule parser or assertion of truth.
CUES = {
    'budget': re.compile(r'\b(?:budget|etat)\s*(?:(?:of|von)\s*)?:?\s*\d+', re.I),
    'deadline': re.compile(r'\b(?:deadline|frist)\s*(?:(?:of|von)\s*)?:?\s*\d+', re.I),
    'local_only': re.compile(r'\b(?:local[- ]only\s+requirement|nur\s+lokal)\s*:?\s*(?:true|false|ja|nein)', re.I),
}
PRIOR = re.compile(r'\b(?:earlier|prior|previous|fr[uü]her(?:e|en|er)?|vorherig(?:e|en|er)?)\b', re.I)
RULE = re.compile(r'\b(?:rules?|regeln?)\b', re.I)
NEGATED = re.compile(r'\b(?:no active rules|not binding|superseded|replaced|nicht verbindlich|ersetzt)\b', re.I)


def _valid_ref(ref):
    return (type(ref) is dict and type(ref.get('source_id')) is str and
            type(ref.get('sha256')) is str and
            re.fullmatch(r'[0-9a-f]{64}', ref['sha256']) is not None and
            type(ref.get('char_start')) is int and
            type(ref.get('char_end')) is int and
            0 <= ref['char_start'] < ref['char_end'] and
            ref.get('modality') == 'text')


def _best_span(source, width):
    """Find the highest-coverage exact lexical window, no rule values parsed."""
    hits = [(name, m.start()) for name, rx in CUES.items() for m in rx.finditer(source)]
    if len({name for name, _ in hits}) < 2:
        return None
    starts = {0, max(0, len(source) - width)}
    for _, pos in hits:
        starts.add(max(0, pos - 30))
        starts.add(max(0, pos - width + 50))
    options = []
    for start in starts:
        end = min(len(source), start + width)
        excerpt = source[start:end]
        coverage = frozenset(name for name, rx in CUES.items() if rx.search(excerpt))
        options.append((len(coverage), -start, start, end, coverage))
    _, _, start, end, coverage = max(options)
    if len(coverage) < 2:
        return None
    return start, end, coverage


def select_rule_span(current, current_event_id, session, generation, revision,
                     retained, read_source, *, cap=768, slots=4,
                     scan_limit=32, excerpt_chars=240):
    """Select at most one verified same-project old-rule span, as SHADOW.

    Retained may contain historical B2 offers beyond runtime's present
    b2_state_slots; sourcing them from the immutable event log is a separate
    integration prerequisite. Slots caps output; it never truncates the scan.
    read_source MUST validate full source digest, tombstones, and exact spans.
    """
    if (type(current) is not str or len(current) > base.MAX_SOURCE_CHARS or
            type(retained) is not list or len(retained) > MAX_SCAN or
            not callable(read_source)):
        raise ValueError('RUN39_INVALID_INPUT')
    if (type(cap) is not int or not 128 <= cap <= 4096 or
            type(slots) is not int or not 1 <= slots <= 12 or
            type(scan_limit) is not int or not 1 <= scan_limit <= MAX_SCAN or
            type(excerpt_chars) is not int or not 80 <= excerpt_chars <= 960):
        raise ValueError('RUN39_BOUNDS')
    result = {'revision': REVISION, 'items': [], 'reasons': {},
              'authority': 'SOURCE_POINTER_ONLY_SHADOW',
              'canonical_gate_pass': False, 'native_executed': False,
              'jepa_weight': 0, 'whole_system_complete': False}
    why = Counter()
    names = base.named_entities(current)
    if len(names) != 1 or not PRIOR.search(current) or not RULE.search(current):
        result['reasons'] = {'NO_UNAMBIGUOUS_PRIOR_RULE_REQUEST': 1}
        return result
    eligible = []
    seen = set()
    for item in retained[:scan_limit]:
        if type(item) is not dict or not _valid_ref(item.get('source_ref')):
            why['BAD_ITEM_OR_REF'] += 1
            continue
        if (item.get('role') != 'B2_GIST' or item.get('session') != session or
                item.get('generation') != generation or
                item.get('model_revision') != revision or
                item.get('event_id') == current_event_id):
            why['OUT_OF_SCOPE'] += 1
            continue
        ref = item['source_ref']
        if ref['source_id'] in seen:
            why['DUPLICATE_SOURCE'] += 1
            continue
        seen.add(ref['source_id'])
        try:
            source = read_source(ref)
            if (type(source) is not str or len(source) > base.MAX_SOURCE_CHARS or
                    len(source) != ref['char_end'] - ref['char_start']):
                raise ValueError('SOURCE_LENGTH')
            if base.named_entities(source) != names or NEGATED.search(source):
                why['PROJECT_OR_RULE_AMBIGUITY'] += 1
                continue
            span = _best_span(source, excerpt_chars)
            if span is None:
                why['NO_COMPLETE_RULE_SPAN'] += 1
                continue
            start, end, coverage = span
            exact_ref = dict(ref, char_start=ref['char_start'] + start,
                             char_end=ref['char_start'] + end)
            exact = read_source(exact_ref)
            if exact != source[start:end]:
                raise ValueError('SOURCE_CHANGED_DURING_READ')
        except (ValueError, OSError, KeyError):
            why['SOURCE_UNAVAILABLE'] += 1
            continue
        eligible.append((len(coverage), frozenset(coverage), item, exact_ref, exact))
    if eligible:
        eligible.sort(key=lambda row: row[0], reverse=True)
        best = eligible[0]
        # Two different full-rule sources of equal lexical quality may conflict.
        # No recency or model hypothesis may silently choose between them.
        if any(row[0] == best[0] and row[3]['sha256'] != best[3]['sha256']
               for row in eligible[1:]):
            why['AMBIGUOUS_RULE_SOURCES'] += 1
        else:
            context = {'exact_source_excerpt': best[4], 'hypothesis': '',
                       'authority': 'PRIOR_HYPOTHESIS_NOT_FACT'}
            if base._json_len([context]) > cap:
                why['CAP'] += 1
            else:
                result['items'] = [{'offer_id': best[2].get('offer_id'),
                                    'source_ref': best[3],
                                    'native_context': context}]
    result['reasons'] = dict(why)
    return result
