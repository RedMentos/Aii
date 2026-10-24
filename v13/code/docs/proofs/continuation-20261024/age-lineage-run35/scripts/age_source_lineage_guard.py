"""V13 WP-Z8 SHADOW root-lineage de-duplication for Run31 source votes.

A registry is a caller-supplied claim, NOT independent attestation.  This
module prevents known aliases from being counted as independent evidence and
binds its diagnostics to the exact registry bytes.  It cannot verify semantic
independence, source accuracy, quality calibration or any AgeControl gate.
"""
import hashlib
import json
import math
from collections import defaultdict

import age_cross_source_signal_v2 as signal

SCHEMA = 'V13_AGE_SOURCE_LINEAGE_SHADOW_V1'
REGISTRY_SCHEMA = 'V13_SOURCE_ROOT_REGISTRY_CLAIM_V1'
MAX_SOURCES = 512


def _ident(value):
    return type(value) is str and 0 < len(value) <= 80 and not value.isspace()


def _quality(value):
    return type(value) in (float, int) and math.isfinite(value) and 0 <= value <= 1


def _registry(registry):
    if type(registry) is not dict or set(registry) != {'schema', 'sources'}:
        raise ValueError('closed registry schema required')
    if registry['schema'] != REGISTRY_SCHEMA or type(registry['sources']) is not list:
        raise ValueError('wrong registry schema')
    if not 1 <= len(registry['sources']) <= MAX_SOURCES:
        raise ValueError('bounded registry required')
    source_map = {}
    for source in registry['sources']:
        if type(source) is not dict or set(source) != {'source_id', 'root_id', 'quality'}:
            raise ValueError('closed registry source entry required')
        sid, root, quality = source['source_id'], source['root_id'], source['quality']
        if not _ident(sid) or not _ident(root) or not _quality(quality):
            raise ValueError('invalid registry source entry')
        if sid in source_map:
            raise ValueError('duplicate source registry entry')
        source_map[sid] = (root, quality)
    # Canonical JSON is an integrity fingerprint only, NOT authentication.
    canonical = json.dumps(registry, sort_keys=True, ensure_ascii=False,
                           separators=(',', ':'), allow_nan=False).encode('utf-8')
    return source_map, hashlib.sha256(canonical).hexdigest()


def _collapse(rows, registry):
    if type(rows) is not list or len(rows) > signal.MAX_RECORDS:
        raise ValueError('bounded observations required')
    # Every observation is checked before the quality filter, including
    # low-quality records: unknown identities must not be silently ignored.
    grouped = defaultdict(dict)
    collapsed = 0
    for row in rows:
        if type(row) is not dict or set(row) != {'case_id', 'source_id', 'label', 'source_quality'}:
            raise ValueError('closed observation schema required')
        case, sid, label, claimed_q = (row[k] for k in ('case_id', 'source_id', 'label', 'source_quality'))
        if not _ident(case) or not _ident(sid) or type(label) is not int or label not in (0, 1):
            raise ValueError('invalid observation')
        if not _quality(claimed_q):
            raise ValueError('invalid observed quality')
        if sid not in registry:
            raise ValueError('unregistered source')
        root, registered_q = registry[sid]
        q = min(claimed_q, registered_q)  # no quality inflation via row claims
        prior = grouped[case].get(root)
        if prior is not None:
            if prior[0] != label:
                raise ValueError('conflicting aliases of one root')
            grouped[case][root] = (label, min(q, prior[1]))
            collapsed += 1
        else:
            grouped[case][root] = (label, q)
    clean = [{'case_id': case, 'source_id': root, 'label': label,
              'source_quality': quality}
             for case in sorted(grouped) for root, (label, quality) in sorted(grouped[case].items())]
    return clean, collapsed


def assess(baseline, current, registry):
    """Return an untrusted, root-de-duplicated diagnostic. Never change Age."""
    source_map, registry_sha = _registry(registry)
    base, base_collapsed = _collapse(baseline, source_map)
    now, now_collapsed = _collapse(current, source_map)
    diagnostic = signal.assess(base, now)
    return {'schema': SCHEMA,
            'status': ('UNVERIFIED_SHIFT_SIGNAL' if diagnostic['status'] == 'SHIFT_CANDIDATE'
                       else diagnostic['status']),
            'diagnostic': diagnostic,
            'registry_sha256': registry_sha,
            'registry_authenticated': False,
            'source_independence_verified': False,
            'root_alias_rows_collapsed': base_collapsed + now_collapsed,
            'registered_roots': len({root for root, _ in source_map.values()}),
            'authority': 'SHADOW_NO_AGE_ACTION',
            'canonical_gate_pass': False}
