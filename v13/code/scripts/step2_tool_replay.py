"""STEP2 with the eligibility tool: replay the recorded STEP2 W1 consumer messages through C3 in extract mode.

Input: the complete STEP2 re-binding report of arm `w1` (scripts/step2_wire_rebind.py, 70 rows, real B1/B2
offers and verified quotes, byte-identical and digest-bound). For every row C3 receives the same messages with
the WP-W2 EXTRACT_SCHEMA (typed values only); v13.agi.eligibility.decide (WP-W2c rule-anchored guard, current
rules override, missing rule -> UNKNOWN) makes the decision. The recorded W1 answers of the same rows are the
no-tool baseline (same messages, same seed, same wire). The unchanged STEP2 paired_utility gate is evaluated on
the tool answers. Question: once C3 arithmetic is removed, do two bodies beat the best single body?
Diagnosis only (SHADOW tool, Linux cloud, no Redmi); STEP2 canonical gate is not promoted by this script.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tests'))
from scripts import calc_tool_ablation as w2
from v13.agi import eligibility as E
from v13.common import atomic_write, digest, dumps, file_hash
from v13.config import initialize, save_config
from v13.runtime import Runtime
from v13.utility import paired_utility, score_decision
import integration_step2_utility as step2

ROOT = Path(__file__).resolve().parents[1]
SEED = 13


def recorded(report_path):
    report = json.loads(Path(report_path).read_text())
    if report.get('wire_arm', {}).get('arm') != 'w1' or report.get('status') not in ('UTILITY_FAIL', 'UTILITY_PASS_SCOPED'):
        raise ValueError('Need the complete w1 STEP2 re-binding report')
    if not report.get('all_structural_checks_passed'): raise ValueError('Input report has structural failures')
    for row in report['rows']:
        if report['row_sha256'][row['fixture']+':'+row['variant']] != digest(dumps(row)): raise ValueError('Recorded STEP2 row changed')
    return report


def evidence(messages):
    user = json.loads(next(m['content'] for m in messages if m['role'] == 'user'))
    return user['current_source'], [q for a in user.get('analysts', []) for q in a.get('verified_quotes', [])]


def tool_answer(raw, messages):
    try: x = json.loads(raw)
    except ValueError: return None, {'error': 'invalid_json'}
    if not isinstance(x, dict) or set(x) != set(w2.EXTRACT_SCHEMA['required']): return None, {'error': 'extract_schema'}
    current, quotes = evidence(messages)
    d = E.decide({k: x[k] for k in ('budget', 'deadline', 'local_only')}, x['options'], current, quotes)
    return dumps({'project': x['project'], 'action': d['action'], 'options': d['options']}), {'extracted': x, 'rejected': d['rejected'], 'revision': d['revision']}


def binding(installed):
    return {'installed': step2.installed_artifacts(Path(installed)),
            'source_sha256': {str(p.relative_to(ROOT)): file_hash(p) for p in
                              (Path(__file__).resolve(), Path(E.__file__).resolve(), ROOT/'scripts/calc_tool_ablation.py', ROOT/'v13/utility.py', ROOT/'v13/runners.py')}}


def preregistration(installed, report_path):
    report = recorded(report_path)
    return {'schema': 'STEP2_TOOL_REPLAY_PREREGISTRATION_V1',
            'source_report': {'path': str(Path(report_path).resolve()), 'sha256': file_hash(report_path), 'rows': len(report['rows'])},
            'consumer_messages_sha256': {r['fixture']+':'+r['variant']: digest(dumps(r['consumer_messages'])) for r in report['rows']},
            'fixture_sha256': report['fixture_sha256'], 'extract_schema_sha256': digest(dumps(w2.EXTRACT_SCHEMA)), 'guard': E.REVISION,
            'consumer_role': 'C3_LANGUAGE', 'seed': SEED, 'wire': 'WP-W1 runners.wire_json', 'config': report['config'],
            'primary': 'unchanged STEP2 paired_utility gate (scoped_utility_gate_pass) on the tool answers',
            'secondary': 'per variant: decision_exact rows (all fields except project), wrong committed decisions (A/B/NONE != oracle), UNKNOWN; same counts for the recorded no-tool W1 answers',
            'expectation_recorded_before_inference': 'override episodes (Cygnus, Equinox, Gemini, Indigo) and Juno become solvable in every variant; '
                                                     'retain-prior episodes need the earlier rule as a verified quote, which reached C3 in only 8/70 W1 rows, '
                                                     'so mostly UNKNOWN there and no two-body gain: gate FAIL expected',
            'canonical_gate_pass': False, 'binding': binding(installed)}


def run(installed, report_path, out_path):
    reg = preregistration(installed, report_path); reg_path = out_path.with_suffix('.preregistration.json')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if reg_path.exists():
        if json.loads(reg_path.read_text()) != reg: raise ValueError('Preregistration binding changed; use a fresh output path')
    else: atomic_write(reg_path, dumps(reg))
    report = recorded(report_path); fixtures = {f['id']: f for f in report['fixtures']}
    out = {'schema': 'STEP2_TOOL_REPLAY_V1', 'status': 'RUNNING', 'preregistration_sha256': file_hash(reg_path), 'rows': [], 'row_sha256': {},
           'canonical_gate_pass': False, 'phone_measured': False}
    home = out_path.with_suffix('.checkpoint')
    if home.exists(): shutil.rmtree(home)
    cfg = dict(report['config']); initialize(home); save_config(home, cfg); step2.installed_links(home, Path(installed).resolve())
    r = Runtime(home)
    try:
        for src in report['rows']:
            f = fixtures[src['fixture']]; messages = src['consumer_messages']
            row = {'fixture': src['fixture'], 'variant': src['variant'], 'raw_answer': '', 'status': 'RUNNING', 'oracle_visible_to_native': False,
                   'consumer_messages_sha256': digest(dumps(messages))}
            started = time.monotonic()
            try:
                runner = r.pool.get('C3_LANGUAGE'); deadline = time.monotonic()+cfg['deadline_seconds']
                for chunk in runner.generate(messages, r.cancel_event, deadline, cfg['answer_tokens'], w2.EXTRACT_SCHEMA, seed=SEED):
                    row['raw_answer'] += chunk
                row['consumer_metrics'] = dict(runner.last_metrics)
                answer, row['tool'] = tool_answer(row['raw_answer'], messages)
                row['answer'] = answer or row['raw_answer']
                row['score'] = score_decision(row['answer'], f['oracle'])
                row['status'] = 'RECORDED' if runner.last_metrics.get('status') == 'FINAL' else 'STRUCTURAL_FAIL'
            except Exception as exc:
                row.update(status='ERROR', error_type=type(exc).__name__, error=str(exc)[:500], score={'utility': 0., 'exact': False, 'contradictions': ['inference_failed']})
            row['elapsed_s'] = time.monotonic()-started
            out['rows'].append(row); out['row_sha256'][row['fixture']+':'+row['variant']] = digest(dumps(row)); atomic_write(out_path, dumps(out))
            print(dumps({'fixture': row['fixture'], 'variant': row['variant'], 'status': row['status'], 'utility': row['score']['utility']}), flush=True)
    finally:
        r.close()
    shutil.rmtree(home, ignore_errors=True)
    out['installed_artifacts_unchanged'] = binding(installed) == reg['binding']
    out['paired_tool'] = paired_utility(out['rows'], [f['id'] for f in report['fixtures']])
    out['summary'] = {'tool': summarize(out['rows'], fixtures), 'no_tool_w1': summarize(report['rows'], fixtures)}
    ok = out['installed_artifacts_unchanged'] and all(x['status'] == 'RECORDED' for x in out['rows'])
    out['status'] = ('TOOL_UTILITY_PASS_SCOPED' if out['paired_tool']['scoped_utility_gate_pass'] else 'TOOL_UTILITY_FAIL') if ok else 'STRUCTURAL_FAIL'
    atomic_write(out_path, dumps(out)); return out


def action_of(row):
    try: return json.loads(row.get('answer') or row.get('raw_answer') or '').get('action')
    except (ValueError, AttributeError): return None


def summarize(rows, fixtures):
    res = {}
    for v in sorted({x['variant'] for x in rows}):
        items = [x for x in rows if x['variant'] == v]; acts = [action_of(x) for x in items]
        res[v] = {'rows': len(items), 'decision_exact': sum(w2.decision_exact(x['score']) for x in items),
                  'wrong_committed': sum(a in ('A', 'B', 'NONE') and a != fixtures[x['fixture']]['oracle']['action'] for a, x in zip(acts, items)),
                  'unknown': acts.count('UNKNOWN'), 'mean_utility': sum(x['score']['utility'] for x in items)/len(items),
                  'exact_fixtures': sorted(x['fixture'] for x in items if w2.decision_exact(x['score']))}
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--installed-home', type=Path, required=True); ap.add_argument('--step2-report', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True); ap.add_argument('--register-only', action='store_true')
    a = ap.parse_args()
    if a.register_only:
        reg = preregistration(a.installed_home, a.step2_report); p = a.out.with_suffix('.preregistration.json'); a.out.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(p, dumps(reg)); print(dumps({'status': 'PREREGISTERED_NO_INFERENCE', 'path': str(p), 'sha256': file_hash(p)})); return
    out = run(a.installed_home, a.step2_report, a.out)
    print(json.dumps({'status': out['status'], 'mean_utility': out['paired_tool']['mean_utility'], 'summary': out['summary']}, indent=1))


if __name__ == '__main__': main()
