"""Nonpromoting G-FOCAL-CAPACITY-003 marginal-diversity competition candidate.

Actual focal.item/priority and memory.relevance are used. No model, live
authority, age right or runtime admission change. Original focal.admit remains
the fixed control. Synthetic capacity pressure is NOT semantic utility.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile

from v13 import focal
from v13.config import initialize
from v13.memory import relevance
from v13.store import Store

SCHEMA = "v13.focal_capacity_diversity_candidate.software.v1"
CAPACITY = 2
THRESHOLD = .45
INTERRUPT = focal.BOOT['sal_interrupt']


def _marginal(candidate, active):
    text = candidate.get('text') or ''
    redundancy = max((relevance(text, a['text']) for a in active
                      if text and a.get('text')), default=0.)
    terms = dict(candidate['priority_terms'])
    terms['redundancy'] = round(redundancy, 4)
    score = round(focal.priority(terms) * candidate['decay'], 4)
    return terms, score


def admit_diverse(candidates, capacity=CAPACITY, threshold=THRESHOLD,
                  interrupt=INTERRUPT):
    """Greedy marginal priority with deterministic high-salience reservation.

    Mutates the supplied candidate copies like focal.admit, but never mutates
    source references or grants fact/learning/action authority.
    """
    if (type(capacity) is not int or capacity < 0
            or not all(isinstance(x, (int, float)) and math.isfinite(x)
                       and not isinstance(x, bool) and 0 <= x <= 1
                       for x in (threshold, interrupt))):
        raise ValueError("FOCAL_CAPACITY_INVALID_BOUNDS")
    active = []
    pool = [c for c in candidates if c['state_type'] != 'DROPPED']
    rest = [c for c in candidates if c['state_type'] == 'DROPPED']
    if len({c['item_id'] for c in candidates}) != len(candidates):
        raise ValueError("FOCAL_DUPLICATE_ITEM_ID")
    while len(active) < capacity:
        ranked = []
        for c in pool:
            terms, score = _marginal(c, active)
            if score >= threshold or c['salience'] >= interrupt:
                ranked.append((c['salience'] >= interrupt, score,
                               c['item_id'], c, terms))
        if not ranked:
            break
        ranked.sort(key=lambda x: (-int(x[0]), -x[1], x[2]))
        urgent, score, _, chosen, terms = ranked[0]
        chosen['priority_terms'] = terms
        chosen['priority'] = score
        chosen['admission'] = ('SALIENCE_INTERRUPT' if urgent and score < threshold
                               else 'PRIORITY')
        chosen['state_type'] = 'ACTIVE'
        active.append(chosen)
        pool.remove(chosen)
    for c in pool:
        terms, score = _marginal(c, active)
        c['priority_terms'] = terms
        c['priority'] = score
        c['admission'] = 'BELOW_THRESHOLD' if score < threshold else 'CAPACITY'
        rest.append(c)
    for c in rest:
        if c['state_type'] == 'ACTIVE':
            c['state_type'] = (c['home_type'] if c['home_type'] != 'ACTIVE'
                               else 'REACTIVATABLE')
    return active, rest


def pressure_fixture(store):
    shared = ("Project Cedar exact archived budget 120 credits and "
              "deadline 10 ticks. Verify both constraints.")
    distinct = ("Project Cedar local-only requirement is true; "
                "remote shipping is forbidden.")
    ref_shared = store.source(shared)
    ref_distinct = store.source(distinct)
    def make(kind, identifier, ref, text, conflict, utility):
        return focal.item(kind, identifier, [ref], text, 'focal-pressure-event',
                          uncertainty=.3, salience=.3, goal=1., utility=utility,
                          sq=1., conflict=conflict)
    return [
        make('B1_DETAIL', 'A', ref_shared, shared, .6, .9),
        make('B2_GIST', 'B', ref_shared, shared, .5, .85),
        make('MEMORY', 'C', ref_distinct, distinct, .4, .7),
    ]


def evidence(store, active):
    refs = [r for c in active for r in c['source_refs']]
    for ref in refs:
        store.read_source(ref)
    return {'ids': [c['item_id'] for c in active],
            'distinct_source_ids': len({r['source_id'] for r in refs}),
            'marginal_priority_sum': round(sum(c['priority'] for c in active), 4),
            'refs_readable': True}


def evaluate():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        initialize(home)
        store = Store(home)
        try:
            items = pressure_fixture(store)
            baseline, _ = focal.admit(deepcopy(items), CAPACITY, THRESHOLD)
            candidate, _ = admit_diverse(deepcopy(items), CAPACITY, THRESHOLD)
            result = {'schema': SCHEMA, 'capacity': CAPACITY,
                      'threshold': THRESHOLD, 'baseline': evidence(store, baseline),
                      'candidate': evidence(store, candidate),
                      'native_model_used': False, 'redmi_measured': False,
                      'semantic_utility_proven': False, 'gate_promoted': False}
            return result
        finally:
            store.close()


if __name__ == '__main__':
    print(json.dumps(evaluate(), sort_keys=True))
