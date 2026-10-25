"""Run185: independent *diagnostic* exact-source support audit of Run181 B2 offers.

Does not replace Run181's preregistered scorer/verdict or activate Gist.
No model calls; consumes only a completed, source-bound 36x3 raw report.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ARMS = ('fixed960', 'event960', 'gist')
MODEL_SHA = '57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf'


def exact_key(text, key):
    """Avoid the original substring scorer's budget/owner/date partial matches."""
    if not isinstance(text, str) or not isinstance(key, str) or not key:
        return False
    return re.search(r'(?<!\w)' + re.escape(key) + r'(?!\w)', text, re.I) is not None


def _no_duplicate_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('duplicate JSON key')
        obj[key] = value
    return obj


def classify(row, raw):
    base = {'parsed': False, 'summary_hit': False, 'quote_support': False,
            'quotes_valid_nonempty': False, 'source_supported_hit': False,
            'mentions_stale': False, 'reason': 'INVALID_OR_UNSUPPORTED'}
    if not isinstance(raw, str):
        return base
    try:
        answer = json.loads(raw, object_pairs_hook=_no_duplicate_keys)
    except (TypeError, ValueError):
        return base
    if not isinstance(answer, dict):
        return base
    summary, quotes = answer.get('summary'), answer.get('quotes')
    if not isinstance(summary, str) or not isinstance(quotes, list):
        return base
    if not all(isinstance(q, str) for q in quotes):
        return base
    text, key = row['text'], row['key']
    if not isinstance(text, str) or not isinstance(key, str):
        return base
    valid = bool(quotes) and all(q and q in text for q in quotes)
    hit = exact_key(summary, key)
    supported = valid and any(exact_key(q, key) for q in quotes)
    stale = bool(row.get('stale')) and exact_key(summary, row['stale'])
    return {'parsed': True, 'summary_hit': hit, 'quote_support': supported,
            'quotes_valid_nonempty': valid, 'source_supported_hit': hit and supported,
            'mentions_stale': stale, 'reason': 'SOURCE_BOUND_DIAGNOSTIC_ONLY'}


def audit(report, corpus):
    if not isinstance(report, dict) or report.get('kind') != 'V13_G1B_GIST_UTILITY':
        raise ValueError('not the registered Run181 Gist report')
    if report.get('binding', {}).get('model_sha256') != MODEL_SHA:
        raise ValueError('model SHA mismatch')
    if 'not Redmi' not in report.get('claim_limit', ''):
        raise ValueError('Linux-only evidence boundary missing')
    if len(corpus) != 36:
        raise ValueError('registered corpus must have 36 memos')
    output = {}
    for arm in ARMS:
        records = report.get(arm)
        if not isinstance(records, list) or len(records) != 36:
            raise ValueError(f'{arm} missing/partial records')
        indices = [x.get('index') if isinstance(x, dict) else None for x in records]
        if set(indices) != set(range(36)) or len(indices) != len(set(indices)):
            raise ValueError(f'{arm} duplicated/missing indices')
        out = []
        for item in records:
            row = corpus[item['index']]
            if item.get('kind') != row['kind'] or type(item.get('prompt_tokens')) is not int or item['prompt_tokens'] <= 0:
                raise ValueError(f'{arm} row binding/prompt tokens invalid')
            c = classify(row, item.get('content'))
            out.append({'index': item['index'], 'kind': row['kind'], 'prompt_tokens': item['prompt_tokens'],
                        'original_hit': item.get('hit'), 'original_quotes_valid': item.get('quotes_valid'),
                        **c})
        output[arm] = sorted(out, key=lambda x: x['index'])
    summary = {}
    for arm in ARMS:
        rr = output[arm]
        summary[arm] = {'original_hits': sum(bool(x['original_hit']) for x in rr),
                        'exact_summary_hits': sum(x['summary_hit'] for x in rr),
                        'source_supported_hits': sum(x['source_supported_hit'] for x in rr),
                        'nonempty_valid_quote_rows': sum(x['quotes_valid_nonempty'] for x in rr),
                        'stale_mentions': sum(x['mentions_stale'] for x in rr),
                        'mean_prompt_tokens': round(sum(x['prompt_tokens'] for x in rr)/36, 1)}
    a, b = output['gist'], output['fixed960']
    wins = sum(x['source_supported_hit'] and not y['source_supported_hit'] for x, y in zip(a, b))
    losses = sum(y['source_supported_hit'] and not x['source_supported_hit'] for x, y in zip(a, b))
    diagnostics = {'source_supported_wins_gt_losses': wins > losses,
                   'nonempty_valid_quotes_not_lower': summary['gist']['nonempty_valid_quote_rows'] >= summary['fixed960']['nonempty_valid_quote_rows'],
                   'prompt_tokens_within_10pct': summary['gist']['mean_prompt_tokens'] <= 1.1 * summary['fixed960']['mean_prompt_tokens']}
    return {'schema': 'V13_RUN185_GIST_SOURCE_SUPPORT_POSTHOC_DIAGNOSTIC_V1',
            'evidence_class': 'READONLY_HISTORICAL_LINUX_NATIVE_B2_OFFER_IF_VERIFIED',
            'summary': summary, 'paired': {'wins': wins, 'losses': losses},
            'diagnostic_criteria': diagnostics,
            'diagnostic_only': 'SOURCE_SUPPORTED_GIST_BETTER' if all(diagnostics.values()) else 'NO_SUPPORTED_GIST_GAIN',
            'original_preregistered_verdict': report.get('decision', {}).get('verdict'),
            'rows': output, 'activation_authorized': False, 'step2_promoted': False,
            'b3_promoted': False, 'body_jepa_available': False, 'jepa_weight': 0,
            'redmi_proven': False, 'v13_complete': False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('report')
    p.add_argument('--output', required=True)
    args = p.parse_args()
    from gist_utility_bench import make
    data = Path(args.report).read_bytes()
    from v13.common import dumps, digest
    corpus = make()
    parsed = json.loads(data)
    if parsed.get('binding', {}).get('corpus_sha256') != digest(dumps(corpus)):
        raise ValueError('frozen corpus digest mismatch')
    result = audit(parsed, corpus)
    result['input_sha256'] = hashlib.sha256(data).hexdigest()
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, sort_keys=True))


if __name__ == '__main__':
    main()
