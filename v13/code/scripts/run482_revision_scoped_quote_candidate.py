#!/usr/bin/env python3
"""Run482: revision-scoped exact quote pointers (shadow, no authority).

The caller MUST supply trusted, externally authenticated current-document SHA256
pins. This candidate validates consistency, not the authenticity of those pins.
Historical revisions are never passed to the lexical ranker. It does not
resolve contradictory statements inside a current document or prove utility.
"""
import hashlib
import re

_HEX = re.compile(r'[0-9a-f]{64}\Z')
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z')


def _valid(condition, message):
    if not condition:
        raise ValueError(message)


def revision_scoped_choices(documents, goal, current_pins, cap=24, ranker=None):
    """Return exact pointers to externally pinned current document revisions.

    documents: list of {doc_id, revision, body, sha256}. Multiple historical
    revisions per doc_id are allowed; current_pins maps each doc_id to the
    externally authenticated SHA256 of its authorized current body.
    Output source_index always refers to the ORIGINAL documents list.
    """
    _valid(type(documents) in (list, tuple) and 1 <= len(documents) <= 16,
           'REVISION_DOCUMENT_BUDGET')
    _valid(type(current_pins) is dict and 1 <= len(current_pins) <= 16 and
           all(type(k) is str and _ID.fullmatch(k) and type(v) is str and
               _HEX.fullmatch(v) for k, v in current_pins.items()),
           'REVISION_PIN_FORMAT')
    _valid(type(goal) is str and 0 < len(goal) <= 512 and
           type(cap) is int and 1 <= cap <= 24,
           'REVISION_QUERY_BUDGET')
    _valid(ranker is None or callable(ranker), 'REVISION_RANKER_INVALID')

    seen = set()
    current = {}
    ids = set()
    total = 0
    for i, item in enumerate(documents):
        _valid(type(item) is dict and set(item) ==
               {'doc_id', 'revision', 'body', 'sha256'},
               'REVISION_RECORD_SCHEMA')
        doc_id, rev, body, digest = (item[k] for k in
                                      ('doc_id', 'revision', 'body', 'sha256'))
        _valid(type(doc_id) is str and _ID.fullmatch(doc_id) and
               type(rev) is int and 0 <= rev <= 2**31 - 1 and
               type(body) is str and 0 < len(body) <= 16_384 and
               type(digest) is str and _HEX.fullmatch(digest),
               'REVISION_RECORD_FORMAT')
        total += len(body)
        _valid(total <= 32_768, 'REVISION_TOTAL_BUDGET')
        _valid(doc_id in current_pins, 'REVISION_UNPINNED_DOCUMENT')
        _valid((doc_id, rev) not in seen, 'REVISION_DUPLICATE_ID')
        seen.add((doc_id, rev))
        ids.add(doc_id)
        _valid(hashlib.sha256(body.encode('utf-8')).hexdigest() == digest,
               'REVISION_CONTENT_MISMATCH')
        if digest == current_pins[doc_id]:
            _valid(doc_id not in current, 'REVISION_AMBIGUOUS_CURRENT')
            current[doc_id] = (i, item)
    _valid(ids == set(current_pins) and set(current) == ids,
           'REVISION_CURRENT_MISSING')

    # Preserve document order, but pass ONLY authorized current bytes.
    active = sorted(current.values(), key=lambda pair: pair[0])
    bodies = [record['body'] for _, record in active]
    if ranker is None:
        from scripts.run481_ranked_quote_choices_candidate import ranked_quote_choices
        ranker = ranked_quote_choices
    pointers = ranker(bodies, goal, cap)
    _valid(type(pointers) in (list, tuple) and len(pointers) <= cap,
           'REVISION_RANKER_RESULT')
    choices = []
    used = set()
    for ptr in pointers:
        _valid(type(ptr) in (tuple, list) and len(ptr) == 3 and
               all(type(n) is int for n in ptr), 'REVISION_POINTER_FORMAT')
        j, a, b = ptr
        _valid(0 <= j < len(active) and 0 <= a < b <= len(bodies[j]),
               'REVISION_POINTER_RANGE')
        _valid((j, a, b) not in used, 'REVISION_POINTER_DUPLICATE')
        used.add((j, a, b))
        original_index, item = active[j]
        choices.append({'source_index': original_index, 'doc_id': item['doc_id'],
                        'revision': item['revision'], 'source_sha256': item['sha256'],
                        'char_start': a, 'char_end': b, 'text': bodies[j][a:b]})
    return {'schema': 'V13_RUN482_REVISION_SCOPED_QUOTES_V1',
            'choices': choices, 'status': 'SHADOW_PINNED_SOURCE_ONLY',
            'canonical_gate_pass': False, 'latent_authority': 0,
            'step2_exit': 'UTILITY_FAIL', 'b3_l1': 'FAIL',
            'body_jepa': 'UNAVAILABLE', 'jepa_weight': 0,
            'redmi_measured': False,
            'claim_limit': 'Caller must authenticate pins; only current pinned bytes are selected. No temporal truth, within-document conflict resolution, or native utility established.'}
