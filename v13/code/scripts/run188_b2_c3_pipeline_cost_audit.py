"""Run188 independent paired *total B2+C3* token/latency cost audit.

Consumes frozen Run181 B2 and Run186 C3 Linux-native raw reports; no inference.
The sum of per-request seconds excludes model startup, routing, energy and Redmi.
"""
import argparse
import hashlib
import json
from pathlib import Path

ARMS = ('fixed960', 'event960', 'gist')
B2_REPORT_SHA = 'ea379b52c7b95c2bb30cd6725f539f443521a64210fdf6bf6fa726c413126880'
C3_REPORT_SHA = '2d9828c2e688b65e50df1849a77fc9bbaf4dd56f59ae423e7b62722f7fc10219'


def audit(b2, c3, corpus):
    if len(corpus) != 36 or b2.get('kind') != 'V13_G1B_GIST_UTILITY' or c3.get('schema') != 'V13_RUN186_C3_FINAL_GIST_UTILITY_V1':
        raise ValueError('wrong or incomplete frozen cohorts')
    if any(c3.get(k) is not False for k in ('activation_authorized', 'step2_promoted', 'b3_promoted', 'redmi_proven', 'v13_complete')):
        raise ValueError('unexpected authority or gate promotion')
    per_arm = {}
    rows = {}
    for arm in ARMS:
        aa, bb = b2.get(arm), c3.get(arm)
        if not isinstance(aa, list) or not isinstance(bb, list) or len(aa) != 36 or len(bb) != 36:
            raise ValueError('incomplete paired arm ' + arm)
        if sorted(x.get('index') for x in aa) != list(range(36)) or sorted(x.get('index') for x in bb) != list(range(36)):
            raise ValueError('duplicate/missing paired IDs ' + arm)
        source = {x['index']: x for x in aa}
        target = {x['index']: x for x in bb}
        records = []
        for i, row in enumerate(corpus):
            x, y = source[i], target[i]
            if x.get('kind') != row['kind'] or y.get('kind') != row['kind']:
                raise ValueError('kind mismatch')
            for item in (x, y):
                if type(item.get('prompt_tokens')) is not int or item['prompt_tokens'] <= 0:
                    raise ValueError('invalid prompt tokens')
                if type(item.get('seconds')) not in (int, float) or not 0 <= item['seconds'] < 600:
                    raise ValueError('invalid seconds')
            records.append({'index': i, 'kind': row['kind'], 'b2_prompt_tokens': x['prompt_tokens'],
                            'c3_prompt_tokens': y['prompt_tokens'],
                            'total_prompt_tokens': x['prompt_tokens'] + y['prompt_tokens'],
                            'b2_seconds': x['seconds'], 'c3_seconds': y['seconds'],
                            'sum_request_seconds': round(x['seconds'] + y['seconds'], 3),
                            'c3_supported_hit': y['supported_hit'], 'c3_quote_valid': y['quote_valid']})
        rows[arm] = records
        per_arm[arm] = {'c3_supported_hits': sum(x['c3_supported_hit'] for x in records),
                        'mean_total_prompt_tokens': round(sum(x['total_prompt_tokens'] for x in records)/36, 1),
                        'mean_sum_request_seconds': round(sum(x['sum_request_seconds'] for x in records)/36, 2),
                        'invalid_c3_quotes': sum(not x['c3_quote_valid'] for x in records),
                        'supported_hits_per_1000_total_prompt_tokens': round(1000*sum(x['c3_supported_hit'] for x in records)/sum(x['total_prompt_tokens'] for x in records), 4)}
    g, f = rows['gist'], rows['fixed960']
    wins = sum(x['c3_supported_hit'] and not y['c3_supported_hit'] for x, y in zip(g, f))
    losses = sum(y['c3_supported_hit'] and not x['c3_supported_hit'] for x, y in zip(g, f))
    criteria = {'paired_supported_wins_gt_losses': wins > losses,
                'total_prompt_tokens_within_10pct': per_arm['gist']['mean_total_prompt_tokens'] <= 1.1*per_arm['fixed960']['mean_total_prompt_tokens'],
                'sum_request_seconds_within_10pct': per_arm['gist']['mean_sum_request_seconds'] <= 1.1*per_arm['fixed960']['mean_sum_request_seconds'],
                'invalid_c3_quotes_not_more': per_arm['gist']['invalid_c3_quotes'] <= per_arm['fixed960']['invalid_c3_quotes']}
    return {'schema': 'V13_RUN188_B2_C3_TOTAL_COST_DIAGNOSTIC_V1',
            'evidence_class': 'HISTORICAL_LINUX_NATIVE_B2_PLUS_C3_SUM_OF_REQUESTS',
            'per_arm': per_arm, 'paired': {'wins': wins, 'losses': losses}, 'criteria': criteria,
            'diagnostic': 'PIPELINE_TOTAL_COST_CANDIDATE' if all(criteria.values()) else 'PIPELINE_TOTAL_COST_NO_GAIN',
            'claim_limit': 'Sequential request seconds summed across separate native B2/C3 jobs; not true end-to-end wall time, energy, Redmi or statistical significance.',
            'rows': rows, 'activation_authorized': False, 'step2_promoted': False,
            'b3_promoted': False, 'body_jepa_available': False, 'jepa_weight': 0,
            'redmi_proven': False, 'v13_complete': False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--b2-report', required=True)
    p.add_argument('--c3-report', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    from gist_utility_bench import make
    from run187_c3_final_independent_audit import audit as independent_c3
    b2raw, c3raw = Path(args.b2_report).read_bytes(), Path(args.c3_report).read_bytes()
    if hashlib.sha256(b2raw).hexdigest() != B2_REPORT_SHA or hashlib.sha256(c3raw).hexdigest() != C3_REPORT_SHA:
        raise ValueError('native source report hash mismatch')
    b2, c3, corpus = json.loads(b2raw), json.loads(c3raw), make()
    independent_c3(c3, b2, corpus)
    result = audit(b2, c3, corpus)
    result['b2_report_sha256'], result['c3_report_sha256'] = B2_REPORT_SHA, C3_REPORT_SHA
    Path(args.output).write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, sort_keys=True))


if __name__ == '__main__':
    main()
