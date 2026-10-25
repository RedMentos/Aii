"""Run187 independent read-only auditor of Run186 C3 final-answer raw 36x3 cohort.

Never performs native inference, changes a model, or promotes any V13 gate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ARMS = ('fixed960', 'event960', 'gist')
SOURCE_SHA = 'ea379b52c7b95c2bb30cd6725f539f443521a64210fdf6bf6fa726c413126880'
B2_SHA = '57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf'
C3_SHA = '3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d'
SERVER_SHA = '79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39'


def _exact(text, key):
    return isinstance(text, str) and isinstance(key, str) and bool(key) and bool(
        re.search(r'(?<!\w)' + re.escape(key) + r'(?!\w)', text, re.I))


def _no_duplicates(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise ValueError('duplicate JSON key')
        d[k] = v
    return d


def _offer_source_quotes(source, row):
    try:
        obj = json.loads(source, object_pairs_hook=_no_duplicates)
    except (TypeError, ValueError):
        return []
    if not isinstance(obj, dict):
        return []
    quotes = obj.get('quotes', [])
    if not isinstance(quotes, list):
        return []
    return [q for q in quotes if isinstance(q, str) and q and len(q) <= 500 and q in row['text']][:3]


def _recompute(row, raw, forwarded):
    zero = {'parsed': False, 'answer_hit': False, 'quote_valid': False,
            'quote_support': False, 'supported_hit': False, 'stale_without_new': False}
    try:
        obj = json.loads(raw, object_pairs_hook=_no_duplicates)
    except (TypeError, ValueError):
        return zero
    if not isinstance(obj, dict):
        return zero
    answer, quote = obj.get('answer'), obj.get('evidence_quote')
    if not isinstance(answer, str) or not isinstance(quote, str):
        return zero
    hit = _exact(answer, row['key'])
    valid = bool(quote) and quote in row['text']
    support = valid and _exact(quote, row['key']) and any(quote in q for q in forwarded)
    stale = bool(row.get('stale')) and _exact(answer, row['stale']) and not hit
    return {'parsed': True, 'answer_hit': hit, 'quote_valid': valid,
            'quote_support': support, 'supported_hit': hit and support,
            'stale_without_new': stale}


def audit(native, source, corpus):
    if len(corpus) != 36 or native.get('schema') != 'V13_RUN186_C3_FINAL_GIST_UTILITY_V1':
        raise ValueError('not complete registered Run186 cohort')
    bind = native.get('binding', {})
    for key, expected in {'source_sha256': SOURCE_SHA, 'b2_sha256': B2_SHA,
                          'c3_sha256': C3_SHA, 'server_sha256': SERVER_SHA,
                          'corpus_rows': 36, 'seed': 13, 'temperature': 0}.items():
        if bind.get(key) != expected:
            raise ValueError('Run186 binding mismatch ' + key)
    if source.get('binding', {}).get('model_sha256') != B2_SHA:
        raise ValueError('Run181 model mismatch')
    if any(native.get(k) is not False for k in ('activation_authorized', 'step2_promoted', 'b3_promoted', 'redmi_proven', 'v13_complete')):
        raise ValueError('unexpected authority/gate promotion')
    if native.get('jepa_weight') != 0 or native.get('body_jepa_available') is not False:
        raise ValueError('JEPA gate unexpectedly promoted')
    rows = {}
    for arm in ARMS:
        observed = native.get(arm)
        b2 = source.get(arm)
        if not isinstance(observed, list) or len(observed) != 36 or not isinstance(b2, list) or len(b2) != 36:
            raise ValueError('incomplete arm ' + arm)
        indices = [r.get('index') for r in observed]
        if sorted(indices) != list(range(36)):
            raise ValueError('duplicate/missing native index ' + arm)
        b2_by = {r['index']: r for r in b2}
        if set(b2_by) != set(range(36)) or len(b2) != len(b2_by):
            raise ValueError('invalid B2 source arm ' + arm)
        rows[arm] = []
        for item in observed:
            i = item['index']
            row = corpus[i]
            if item.get('kind') != row['kind'] or type(item.get('prompt_tokens')) is not int or item['prompt_tokens'] <= 0:
                raise ValueError('native row metadata mismatch')
            forwarded = _offer_source_quotes(b2_by[i]['content'], row)
            if item.get('source_quote_count') != len(forwarded):
                raise ValueError('source quote count mismatch')
            expected = _recompute(row, item.get('content'), forwarded)
            for k, v in expected.items():
                if item.get(k) != v:
                    raise ValueError(f'{arm} index {i} score mismatch {k}')
            rows[arm].append({'index': i, 'kind': row['kind'], 'prompt_tokens': item['prompt_tokens'], **expected})
        rows[arm].sort(key=lambda x: x['index'])
    stats = {}
    for arm in ARMS:
        rr = rows[arm]
        stats[arm] = {'answer_hits': sum(x['answer_hit'] for x in rr),
                      'supported_hits': sum(x['supported_hit'] for x in rr),
                      'invalid_quotes': sum(not x['quote_valid'] for x in rr),
                      'stale_without_new': sum(x['stale_without_new'] for x in rr),
                      'mean_prompt_tokens': round(sum(x['prompt_tokens'] for x in rr)/36, 1)}
    g, f = rows['gist'], rows['fixed960']
    wins = sum(x['supported_hit'] and not y['supported_hit'] for x, y in zip(g, f))
    losses = sum(y['supported_hit'] and not x['supported_hit'] for x, y in zip(g, f))
    criteria = {'paired_supported_wins_gt_losses': wins > losses,
                'invalid_quotes_not_more': stats['gist']['invalid_quotes'] <= stats['fixed960']['invalid_quotes'],
                'prompt_tokens_within_10pct': stats['gist']['mean_prompt_tokens'] <= 1.1 * stats['fixed960']['mean_prompt_tokens']}
    verdict = 'C3_GIST_FINAL_UTILITY_CANDIDATE' if all(criteria.values()) else 'C3_GIST_FINAL_NO_GAIN'
    if native.get('summary') != stats or native.get('paired') != {'wins': wins, 'losses': losses} or native.get('criteria') != criteria or native.get('diagnostic') != verdict:
        raise ValueError('Run186 aggregate result mismatch')
    return {'status': 'RUN187_INDEPENDENT_C3_FINAL_AUDIT_PASS', 'evidence_class': 'LINUX_NATIVE_C3_IF_RAW_VERIFIED',
            'n_per_arm': 36, 'summary': stats, 'paired': {'wins': wins, 'losses': losses},
            'diagnostic': verdict, 'activation_authorized': False, 'step2_promoted': False,
            'b3_promoted': False, 'body_jepa_available': False, 'jepa_weight': 0,
            'redmi_proven': False, 'v13_complete': False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--native-report', required=True)
    p.add_argument('--b2-report', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    from gist_utility_bench import make
    nbytes = Path(args.native_report).read_bytes()
    sbytes = Path(args.b2_report).read_bytes()
    if hashlib.sha256(sbytes).hexdigest() != SOURCE_SHA:
        raise ValueError('Run181 original report bytes changed')
    result = audit(json.loads(nbytes), json.loads(sbytes), make())
    result['native_sha256'] = hashlib.sha256(nbytes).hexdigest()
    result['b2_source_sha256'] = hashlib.sha256(sbytes).hexdigest()
    Path(args.output).write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
