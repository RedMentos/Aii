"""Summarize a finished STEP2 private pilot run directory (read-only)."""
import json, sys
from collections import defaultdict
from pathlib import Path
run = Path(sys.argv[1]); rep = json.loads((run / 'report.json').read_text())
arms = defaultdict(list); fields = defaultdict(int); rows = []
for r in rep['rows']:
    s = r.get('score') or {}; fc = s.get('field_checks', {})
    rss = max((c.get('metrics', {}).get('memory', {}).get('rss_bytes') or 0) for c in r['calls']) if r['calls'] else 0
    try: ans = json.loads(r.get('raw_answer') or '')
    except ValueError: ans = None
    row = {'fixture': r['fixture'], 'variant': r['variant'], 'status': r['status'], 'error': r.get('error'),
           'exact': bool(s.get('exact')), 'utility': s.get('utility'), 'action_ok': bool(fc.get('action')),
           'answer_action': ans.get('action') if isinstance(ans, dict) else None,
           'failed_fields': sorted(k for k, v in fc.items() if not v), 'delivered_quotes': len(r.get('delivered_quotes') or []),
           'calls': [c['role'] + ':' + c['status'] for c in r['calls']], 'elapsed_s': round(r['elapsed_s'], 2),
           'peak_rss_mb': round(rss / 2**20)}
    rows.append(row); arms[r['variant']].append(row)
    for f in row['failed_fields']: fields[f.split('.')[-1]] += 1
summary = {'schema': 'V13_STEP2_PRIVATE_PILOT_SUMMARY_V1', 'run_status': rep['status'],
           'coverage_complete': rep.get('coverage_complete'), 'final_bindings_unchanged': rep.get('final_bindings_unchanged'),
           'registration_sha256': rep['registration_sha256'], 'rows': rows,
           'per_arm': {a: {'rows': len(v), 'recorded': sum(x['status'] == 'RECORDED' for x in v),
                           'exact': sum(x['exact'] for x in v), 'action_ok': sum(x['action_ok'] for x in v),
                           'mean_utility': round(sum(x['utility'] or 0 for x in v) / len(v), 3)} for a, v in arms.items()},
           'failed_field_counts': dict(sorted(fields.items(), key=lambda kv: -kv[1])),
           'answer_actions': sorted({str(x['answer_action']) for x in rows}),
           'total_elapsed_s': round(sum(x['elapsed_s'] for x in rows), 1),
           'max_peak_rss_mb': max(x['peak_rss_mb'] for x in rows),
           'gate_promotion': False, 'historical_step2_utility': 'UTILITY_FAIL_UNCHANGED'}
print(json.dumps(summary, indent=2, sort_keys=True))
