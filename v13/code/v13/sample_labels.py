"""WP-BP2f (BP2 rest): per-sample label-source weights for everyday weight learning (§12.4, §14.5, §63).

Weight learning mixes three label sources in one batch: human (stated facts, corrections, explicit ratings),
own (model-written targets: sdft, rated answers, own final answers) and real outcomes (deterministic tool/world results).
`neuromod.sample_factor` can already weigh one sample by its source; until now no learner path carried the source per sample.
This module labels each training item with a neuromod source class and credits the factor as `weight` (multiplied with a
weight already there, e.g. a `:note` rating, sign kept). Dream and vetoed items get weight 0 and are dropped.
Strongest source present is normalised to 1.0 so total step size stays comparable; ratios between sources are kept.
Pure functions, no state, no authority. Opt-in via cfg `sample_modulation` (default off); wiring: WeightConsolidation.stage.
"""
from . import neuromod as N
from .guards import item_origin

COMPONENT = 'B1_DETAIL'
OUTCOME_KINDS = ('tool_outcome', 'world_outcome', 'outcome')
# origin -> (neuromod source class, channels credited to the sample)
_CHANNELS = {
    'human': ('human_correction', {'human_correction': 1.0, 'evidence_gain': 0.6}),
    'human_replay': ('human_correction', {'human_correction': 1.0, 'evidence_gain': 0.6}),
    'self': ('internal_crosscheck', {'retention': 0.5}),
    'outcome': ('real_deterministic_outcome', {'task_success': 1.0, 'evidence_gain': 1.0}),
}


def label_class(item):
    """'human' | 'human_replay' | 'self' | 'outcome' | 'dream' | 'seed' for one item. Outcome wins over self."""
    if item.get('kind') in OUTCOME_KINDS or item.get('label_source') == 'real_deterministic_outcome':
        return 'outcome'
    return item_origin(item)


def factor_of(item, rule_violation=0.0):
    cls = label_class(item)
    if cls not in _CHANNELS:
        return 0.0
    src, ch = _CHANNELS[cls]
    ch = dict(ch)
    if rule_violation:
        ch['rule_violation'] = rule_violation
    return N.sample_factor(COMPONENT, src, safety_veto=bool(item.get('safety_veto')),
                           irreversible=bool(item.get('irreversible')), rollback_available=bool(item.get('rollback_available')), **ch)


def modulate(items, enabled=True):
    """Return (items with `label_class`, `sample_factor` and scaled `weight`, report). Dropped items listed in the report."""
    if not enabled:
        return list(items), {'enabled': False}
    scored = [(i, label_class(i), factor_of(i)) for i in items]
    top = max([f for _, _, f in scored] + [0.0])
    kept, dropped, by = [], [], {}
    for i, cls, f in scored:
        if f <= 0 or top <= 0:
            dropped.append({'memory_id': i.get('memory_id'), 'class': cls})
            continue
        w = float(i.get('weight', 1.0)) * f / top
        kept.append(dict(i, label_class=cls, sample_factor=f, weight=round(w, 6)))
        by.setdefault(cls, []).append(round(f / top, 4))
    return kept, {'enabled': True, 'top_factor': top, 'dropped': dropped,
                  'mean_relative_factor': {k: round(sum(v) / len(v), 4) for k, v in by.items()}, 'counts': {k: len(v) for k, v in by.items()}}
