"""WP-W2c: recompute recorded extraction answers with the rule-anchored guard (no inference).

Inputs are the closed WP-W2 and WP-W2b reports (digest-checked rows). For every row whose model returned a
typed extraction (extract_tool, extract_span), the extracted rule and option values are fed to
v13.agi.eligibility.decide with the same evidence the model saw (current source + verified quotes). Model
quotes are ignored. Offline on exposed answers: shows what the deterministic guard changes, not new ability.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import calc_tool_span_ablation as span
from scripts import consumer_model_ablation as consumer
from v13.agi import eligibility as E
from v13.common import atomic_write, digest, dumps, file_hash
from v13.utility import score_decision
from scripts.calc_tool_ablation import decision_exact


def checked_rows(path):
    report = json.loads(Path(path).read_text())
    if report.get('status') != 'RECORDED_DIAGNOSIS': raise ValueError('report not closed: '+str(path))
    for r in report['rows']:
        if report['row_sha256'][r['fixture']+'/'+r['arm']] != digest(dumps(r)): raise ValueError('row changed')
    return report['rows']


def evidence(messages):
    user = json.loads(next(m['content'] for m in messages if m['role'] == 'user'))
    return user.get('current_source', ''), [q['text'] for a in user.get('analysts', []) for q in a.get('verified_quotes', [])]


def recompute(rows, inputs, report_name):
    out = []
    for r in rows:
        x = (r.get('tool') or {}).get('extracted')
        if not x: continue
        f = span.ALL_FIXTURES[r['fixture']]
        current, quotes = evidence(inputs[r['fixture']])
        d = E.decide({k: x[k] for k in ('budget', 'deadline', 'local_only')}, x['options'], current, quotes)
        score = score_decision(dumps({'project': x['project'], 'action': d['action'], 'options': d['options']}), f['oracle'])
        out.append({'report': report_name, 'fixture': r['fixture'], 'arm': r['arm'], 'set': r.get('set', 'recorded_exposed'),
                    'oracle_action': f['oracle']['action'], 'previous_action': r.get('action'), 'previous_decision_exact': r['decision_exact'],
                    'anchored_action': d['action'], 'anchored_decision_exact': decision_exact(score), 'rejected': d['rejected']})
    return out


def summary(rows):
    groups = {}
    for r in rows: groups.setdefault(r['report']+':'+r['arm']+':'+r['set'], []).append(r)
    res = {}
    for k, items in sorted(groups.items()):
        dec = [r for r in items if r['oracle_action'] in ('A', 'B')]; unk = [r for r in items if r['oracle_action'] == 'UNKNOWN']
        res[k] = {'rows': len(items), 'previous_decision_exact': sum(r['previous_decision_exact'] for r in items),
                  'anchored_decision_exact': sum(r['anchored_decision_exact'] for r in items),
                  'anchored_exact_on_decidable': sum(r['anchored_decision_exact'] for r in dec),
                  'anchored_unknown_ok': sum(r['anchored_action'] == 'UNKNOWN' for r in unk),
                  'wrong_non_unknown_on_missing': sum(r['anchored_action'] not in ('UNKNOWN',) for r in unk),
                  'changed_rows': [r['fixture'] for r in items if r['anchored_action'] != r['previous_action']]}
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rule-transport-report', type=Path, required=True)
    ap.add_argument('--w2-report', type=Path, required=True)
    ap.add_argument('--w2b-report', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    _, recorded = consumer.recorded_inputs(a.rule_transport_report)
    rows = recompute(checked_rows(a.w2_report), recorded, 'w2')
    rows += recompute(checked_rows(a.w2b_report), span.inputs_for(a.rule_transport_report), 'w2b')
    out = {'schema': 'ELIGIBILITY_OFFLINE_RECOMPUTE_V1', 'guard_revision': E.REVISION,
           'inputs_sha256': {str(p): file_hash(p) for p in (a.w2_report, a.w2b_report, a.rule_transport_report)},
           'guard_source_sha256': file_hash(Path(E.__file__)), 'evidence_level': 'OFFLINE_RECOMPUTE_OF_EXPOSED_RECORDED_ANSWERS',
           'rows': rows, 'summary': summary(rows), 'canonical_gate_pass': False}
    atomic_write(a.out, dumps(out))
    for k, v in out['summary'].items(): print(k, dumps(v))


if __name__ == '__main__': main()
