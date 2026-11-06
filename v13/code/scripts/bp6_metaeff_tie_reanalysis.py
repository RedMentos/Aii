#!/usr/bin/env python3
"""Post-hoc, read-only comparison of BP6's saved report and tie-stable meta_i.

This consumes the five existing DS3b input JSON files and the published report;
it does not write to either. Output is JSON on stdout, including input hashes.
No inference, new samples, or historical-result replacement is performed.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13.agi import metaeff

EXPECTED_INPUT_SHA256 = {
    'ds3b-41.json': '878f6f662cbff34dae627a277d2e9aea5355253fae28cde769fcb6d4779bead1',
    'ds3b-43.json': 'd689f2715df8a354a8e768a0b435cde97569550432590fbdb527f86f1efedcf5',
    'ds3b-47.json': 'd4c420797cf028fae271a5cf61cdba69adf74597752f190f3b72f985fcda0877',
    'ds3b-53.json': '134e6994401e76e8200d15c796061c307ba3e13f32990ac558d53920014383e4',
    'ds3b-59.json': '404b172e98f3b095e6846ac44db812f03700033b584a7449442ca2de70fd76c8',
}
EXPECTED_REPORT_SHA256 = '850304491a0aa490cb2e7660ef08815f64cd5c5843b30d986a51369e5ed7e834'


def load_json(path, expected_hash):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_hash:
        raise ValueError('unexpected source hash: %s' % path.name)
    return json.loads(data), digest


def legacy_meta_i(pairs, bins=5):
    """Reproduce the historical equal-count split solely for sensitivity analysis."""
    n = len(pairs)
    if n < 2:
        return None
    entropy = lambda p: 0.0 if p <= 0 or p >= 1 else -(p * math.log2(p) + (1 - p) * math.log2(1 - p))
    hy = entropy(sum(int(bool(y)) for _, y in pairs) / n)
    if hy == 0:
        return 0.0
    ordered = sorted(pairs, key=lambda pair: pair[0])
    count = max(1, min(bins, n))
    cells = [ordered[i * n // count:(i + 1) * n // count] for i in range(count)]
    hyc = sum(len(cell) / n * entropy(sum(int(bool(y)) for _, y in cell) / len(cell)) for cell in cells if cell)
    return max(0.0, (hy - hyc) / hy)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--fixture-dir', type=Path,
        default=Path(__file__).resolve().parents[2] / 'bench-results' / 'bp6-metaeff-20261101',
    )
    args = parser.parse_args()
    original, report_hash = load_json(args.fixture_dir / 'report.json', EXPECTED_REPORT_SHA256)
    rows, hashes = [], {}
    for seed in (41, 43, 47, 53, 59):
        name = 'ds3b-%d.json' % seed
        source, digest = load_json(args.fixture_dir / 'in' / name, EXPECTED_INPUT_SHA256[name])
        hashes[name] = digest
        rows.extend(source['rows'])
    if len(rows) != original['n'] or sum(bool(r['pass1']['pass']) for r in rows) != original['correct']:
        raise ValueError('saved rows do not match the original report counts')

    sources = {
        'mean_logprob': lambda x: math.exp(x['mean_logprob']),
        'min_logprob': lambda x: math.exp(x['min_logprob']),
        'p10_logprob': lambda x: math.exp(x['p10_logprob']),
        'digit_min_logprob': lambda x: math.exp(x['digit_min_logprob']),
        'share_above_half': lambda x: 1 - x['share_below_half'],
    }
    output = {
        'scope': 'post_hoc_original_saved_rows_not_a_new_model_run',
        'n': len(rows),
        'input_sha256': hashes,
        'original_report_sha256': report_hash,
        'settings': {'bins': 5, 'permutations': 500, 'bootstrap': 300, 'seed': 0},
        'sources': {},
    }
    for name, read_confidence in sources.items():
        pairs = [(read_confidence(r['pass1']['features']), int(bool(r['pass1']['pass']))) for r in rows]
        counts = Counter(confidence for confidence, _ in pairs)
        if round(legacy_meta_i(pairs), 4) != original['sources'][name]['meta']['meta_i']:
            raise AssertionError('historical point estimate did not replay: %s' % name)
        shuffled = pairs.copy()
        random.Random(1).shuffle(shuffled)
        corrected = metaeff.report(pairs, bins=5, perm=500, boot=300, seed=0)
        if corrected != metaeff.report(shuffled, bins=5, perm=500, boot=300, seed=0):
            raise AssertionError('report changed under input permutation: %s' % name)
        output['sources'][name] = {
            'original_reported': original['sources'][name]['meta'],
            'tie_stable_post_hoc': corrected,
            'distinct_confidences': len(counts),
            'rows_with_ties': sum(count for count in counts.values() if count > 1),
            'largest_tie': max(counts.values(), default=0),
            'abstain_gain_original': original['sources'][name]['abstain']['gain'],
        }
        if name == 'share_above_half':
            old_scores = []
            for seed in range(500):
                reordered = pairs.copy()
                random.Random(seed).shuffle(reordered)
                old_scores.append(legacy_meta_i(reordered))
            reference = original['sources']['min_logprob']['meta']['meta_i']
            output['sources'][name]['legacy_order_sensitivity'] = {
                'seeds': '0..499',
                'min': round(min(old_scores), 4),
                'max': round(max(old_scores), 4),
                'min_logprob_reference': reference,
                'count_below_reference': sum(score < reference for score in old_scores),
            }
    print(json.dumps(output, indent=2, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
