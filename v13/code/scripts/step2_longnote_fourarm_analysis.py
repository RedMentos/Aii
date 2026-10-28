"""Fail-closed four-arm STEP2 evidence analysis; never promotes Canon gates.

Consumes closed, externally generated per-run summaries. This module does not
load models, alter cohorts, or infer that supplied hashes authenticate bytes.
"""
from __future__ import annotations

import math
import random

ARMS = ('TC', 'TP', 'SC', 'SP')
SEEDS = (27, 28, 29)
VARIANTS = ('b1_only', 'b2_only', 'both_none', 'both_exact',
            'both_control', 'same_policy_dual', 'prompt_only_dual')
ROLES = ('B1_DETAIL', 'B2_GIST', 'C3_LANGUAGE')


def _sha(value):
    return (type(value) is str and len(value) == 64 and
            all(c in '0123456789abcdef' for c in value))


def _number(value):
    return type(value) in (float, int) and math.isfinite(value) and 0 <= value <= 1


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def validate(runs, fixture_ids):
    """Validate complete paired evidence, control settings and hash identities.

    A digest field is a claimed identity, not a cryptographic verification of
    its referenced file. The native evidence collector must check actual bytes.
    """
    ids = tuple(fixture_ids)
    _require(len(ids) == 10 and len(set(ids)) == 10 and
             all(type(i) is str and i and ':' not in i for i in ids),
             'Expected ten unique registered fixture IDs')
    _require(type(runs) in (tuple, list) and len(runs) == 12,
             'Expected all twelve paired arm/seed reports')
    found = {}
    identities = []
    for r in runs:
        _require(type(r) is dict, 'Malformed run')
        arm, seed = r.get('arm'), r.get('seed')
        _require(arm in ARMS and type(seed) is int and seed in SEEDS,
                 'Unregistered arm or seed')
        key = (arm, seed)
        _require(key not in found, 'Duplicate arm/seed report')
        found[key] = r
        for field in ('registration_sha256', 'fixture_sha256', 'runner_sha256', 'raw_sha256'):
            _require(_sha(r.get(field)), 'Missing/invalid ' + field)
        source = r.get('source_sha256')
        _require(type(source) is dict and len(source) >= 4 and
                 all(type(p) is str and p and _sha(h) for p, h in source.items()),
                 'Missing source closure')
        models = r.get('model_sha256')
        _require(type(models) is dict and set(models) == set(ROLES) and
                 all(_sha(v) for v in models.values()), 'Missing model identities')
        if arm.startswith('T'):
            _require(models['B1_DETAIL'] != models['B2_GIST'],
                     'Two-distinct control reuses B1 weight')
        else:
            _require(models['B1_DETAIL'] == models['B2_GIST'],
                     'Shared control is not shared weights')
        cfg = r.get('enable')
        _require(type(cfg) is dict and cfg.get('seed') == seed and
                 cfg.get('b2_control') == ('two_body' if arm.startswith('T')
                                           else 'shared_body_dual_state') and
                 cfg.get('b2_quote_select') == ('pointer' if arm.endswith('P') else 'off') and
                 cfg.get('offer_quote_context_chars') == 200 and
                 cfg.get('b1_recent_source_chars') == 600 and
                 cfg.get('b2_offer_body_state') is False,
                 'Control settings not the registered four-arm design')
        queried = r.get('queried_offers')
        _require(type(queried) is dict and type(queried.get('offers')) is int and
                 queried['offers'] > 0 and queried.get('with_question') == queried['offers'],
                 'JEF question arm not fully active')
        _require(r.get('step2_status') in ('UTILITY_FAIL', 'UTILITY_PASS_SCOPED') and
                 r.get('tool_status') in ('TOOL_UTILITY_FAIL', 'TOOL_UTILITY_PASS_SCOPED'),
                 'Incomplete native/tool replay evidence')
        _require(r.get('evidence_kind') in ('LINUX_NATIVE', 'REDMI_NATIVE',
                                             'SOFTWARE_SYNTHETIC'),
                 'Unclassified evidence')
        scores = r.get('episode_utility_tool')
        expected = {f'{fid}:{v}' for fid in ids for v in VARIANTS}
        _require(type(scores) is dict and set(scores) == expected and
                 all(_number(x) for x in scores.values()),
                 'Incomplete/nonfinite/misaligned paired utility')
        profiles = r.get('error_profile_tool')
        _require(type(profiles) is dict and
                 all(type(profiles.get(v)) is dict and
                     all(_number(profiles[v].get(f)) for f in
                         ('rule_fields_correct', 'option_fields_correct'))
                     for v in ('b1_only', 'b2_only')),
                 'Missing complementary error profile')
        identities.append((r['registration_sha256'], r['fixture_sha256'],
                           r['runner_sha256'], tuple(sorted(source.items())),
                           r['evidence_kind']))
    _require(set(found) == {(a, s) for a in ARMS for s in SEEDS},
             'Missing paired runs')
    _require(len(set(identities)) == 1, 'Unmatched source/fixture/runner/cohort')
    _require(len({r['raw_sha256'] for r in runs}) == 12,
             'Duplicate raw evidence digest (possible stale replay)')
    for s in SEEDS:
        for left, right in (('TC', 'TP'), ('SC', 'SP')):
            _require(found[left, s]['model_sha256'] == found[right, s]['model_sha256'],
                     'Pointer arm changed model identity')
        _require(len({found[a, s]['model_sha256']['C3_LANGUAGE'] for a in ARMS}) == 1,
                 'Different C3 consumer across arms')
    for arm in ARMS:
        _require(all(found[arm, s]['model_sha256'] == found[arm, SEEDS[0]]['model_sha256']
                     for s in SEEDS), 'Model changed between seeds')
    return found, ids


def _paired(found, ids, left, right, variant_left='both_exact',
            variant_right='both_exact', bootstrap=2000):
    # Bootstrap by episode: each episode keeps all three paired seed results.
    per = [sum(found[left, s]['episode_utility_tool'][f'{fid}:{variant_left}'] -
               found[right, s]['episode_utility_tool'][f'{fid}:{variant_right}']
               for s in SEEDS) / len(SEEDS) for fid in ids]
    mean = sum(per) / len(per)
    rng = random.Random(20261028)
    draws = sorted(sum(per[rng.randrange(len(per))] for _ in per) / len(per)
                   for _ in range(bootstrap))
    lo, hi = draws[int(.025 * bootstrap)], draws[int(.975 * bootstrap) - 1]
    return {'mean': mean, 'ci95': [lo, hi], 'episodes': len(ids), 'seeds': len(SEEDS)}


def mean_seed(found, arm, seed, ids, variant):
    return sum(found[arm, seed]['episode_utility_tool'][f'{fid}:{variant}']
               for fid in ids) / len(ids)


def analyze(runs, fixture_ids):
    found, ids = validate(runs, fixture_ids)
    def mean(arm, variant):
        return sum(found[arm, s]['episode_utility_tool'][f'{fid}:{variant}']
                   for s in SEEDS for fid in ids) / (len(SEEDS) * len(ids))
    best = max(('b1_only', 'b2_only'), key=lambda v: mean('TP', v))
    comparisons = {
        'tp_vs_best_single': _paired(found, ids, 'TP', 'TP', 'both_exact', best),
        'tp_vs_same_policy': _paired(found, ids, 'TP', 'TP', 'both_exact', 'same_policy_dual'),
        'tp_vs_prompt_only': _paired(found, ids, 'TP', 'TP', 'both_exact', 'prompt_only_dual'),
        'tp_vs_shared_pointer': _paired(found, ids, 'TP', 'SP'),
        'tp_vs_two_distinct_no_pointer': _paired(found, ids, 'TP', 'TC'),
        'sp_vs_shared_no_pointer': _paired(found, ids, 'SP', 'SC'),
    }
    profile = {v: {k: sum(found['TP', s]['error_profile_tool'][v][k]
                           for s in SEEDS) / len(SEEDS)
                   for k in ('rule_fields_correct', 'option_fields_correct')}
               for v in ('b1_only', 'b2_only')}
    body_wins = {v: any(found['TP', s]['episode_utility_tool'][f'{fid}:{v}'] >
                            found['TP', s]['episode_utility_tool'][f'{fid}:{other}']
                            for s in SEEDS for fid in ids)
                 for v, other in (('b1_only', 'b2_only'), ('b2_only', 'b1_only'))}
    checks = {
        'tp_beats_best_single': comparisons['tp_vs_best_single']['ci95'][0] > 0,
        'tp_beats_same_policy': comparisons['tp_vs_same_policy']['ci95'][0] > 0,
        'tp_beats_prompt_only': comparisons['tp_vs_prompt_only']['ci95'][0] > 0,
        'tp_beats_shared_pointer': comparisons['tp_vs_shared_pointer']['ci95'][0] > 0,
        'each_body_wins_an_episode': all(body_wins.values()),
        'complementary_profiles': (
            profile['b1_only']['option_fields_correct'] -
            profile['b2_only']['option_fields_correct'] >= .25 and
            profile['b2_only']['rule_fields_correct'] -
            profile['b1_only']['rule_fields_correct'] >= .25),
        'tp_beats_each_single_every_seed': all(
            mean_seed(found, 'TP', s, ids, 'both_exact') >
            max(mean_seed(found, 'TP', s, ids, 'b1_only'),
                mean_seed(found, 'TP', s, ids, 'b2_only')) for s in SEEDS),
    }
    proof_kind = runs[0]['evidence_kind']
    return {'status': 'FOUR_ARM_DIAGNOSTIC_ONLY',
            'evidence_kind': proof_kind, 'best_single': best,
            'comparisons': comparisons, 'profiles': profile, 'checks': checks,
            'candidate_supported': all(checks.values()),
            'canonical_gate_pass': False, 'step2_gate_promoted': False,
            'body_jepa_available': False, 'jepa_weight': 0,
            'claim_limit': 'No STEP2/B3/Body-JEPA/Redmi/whole-system promotion; raw bytes require independent verification'}
