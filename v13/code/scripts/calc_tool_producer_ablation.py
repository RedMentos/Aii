"""WP-W2d: the eligibility tool with real producer handoffs (no wholesale upper bound).

Replays the recorded consumer messages of the rule-transport ablation arms `current` and `earlier_quotes`
(real B2 offers and verified quotes, byte-identical, digest-bound) to C3/B2/B1 on the WP-W1 wire:
  action_first      reviewed SCHEMA, the model decides
  extract_anchored  the model extracts typed values (WP-W2 EXTRACT_SCHEMA); v13.agi.eligibility.decide
                    (rule-anchored guard, current-rule conflicts refused) decides
Question: with realistic (incomplete, truncated) rule transport, does the tool add correct decisions or
only refuse safely? Diagnosis only: Linux cloud, no Redmi, no model choice, STEP2 UTILITY_FAIL unchanged.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import calc_tool_ablation as w2
from scripts import consumer_model_ablation as consumer
from scripts.rule_transport_ablation import FIXTURES
from tests.integration_step2_utility import installed_links
from v13.agi import eligibility as E
from v13.common import atomic_write, digest, dumps, file_hash
from v13.config import initialize, save_config
from v13.runtime import Runtime
from v13.utility import score_decision

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ARMS = ('current', 'earlier_quotes')
MODES = ('action_first', 'extract_anchored')
ARMS = tuple(m+'/'+s+'/'+o for m in consumer.MODELS for s in SOURCE_ARMS for o in MODES)
CONFIG = consumer.CONFIG


def recorded_inputs(report_path):
    report = json.loads(Path(report_path).read_text())
    if report.get('status') != 'RECORDED_DIAGNOSIS': raise ValueError('Rule-transport ablation is not a complete recorded diagnosis')
    out = {}
    for arm in SOURCE_ARMS:
        rows = {r['fixture']: r for r in report['rows'] if r['arm'] == arm}
        if set(rows) != {f['id'] for f in FIXTURES}: raise ValueError('inputs incomplete: '+arm)
        for fid, row in rows.items():
            if report['row_sha256'][fid+'/'+arm] != digest(dumps(row)): raise ValueError('Recorded consumer row changed')
            out[(arm, fid)] = row['consumer_messages']
    return out


def evidence(messages):
    user = json.loads(next(m['content'] for m in messages if m['role'] == 'user'))
    return user.get('current_source', ''), [q['text'] for a in user.get('analysts', []) for q in a.get('verified_quotes', [])]


def run_anchored(raw, messages):
    try: x = json.loads(raw)
    except ValueError: return None, {'error': 'invalid_json'}
    if not isinstance(x, dict) or set(x) != set(w2.EXTRACT_SCHEMA['required']): return None, {'error': 'extract_schema'}
    current, quotes = evidence(messages)
    d = E.decide({k: x[k] for k in ('budget', 'deadline', 'local_only')}, x['options'], current, quotes)
    return dumps({'project': x['project'], 'action': d['action'], 'options': d['options']}), {'extracted': x, 'rejected': d['rejected'], 'revision': d['revision']}


def binding(installed):
    found = w2.binding(installed)
    for p in (Path(__file__).resolve(), Path(E.__file__).resolve()):
        found['source_sha256'][str(p.relative_to(ROOT))] = file_hash(p)
    found['source_scope'] += '_PLUS_PRODUCER_FOLLOW_UP'
    return found


def preregistration(installed, report_path):
    inputs = recorded_inputs(report_path)
    return {'schema': 'CALC_TOOL_PRODUCER_ABLATION_PREREGISTRATION_V1',
            'source_report': {'path': str(Path(report_path).resolve()), 'sha256': file_hash(report_path), 'arms': list(SOURCE_ARMS)},
            'consumer_messages_sha256': {a+'/'+f: digest(dumps(v)) for (a, f), v in sorted(inputs.items())},
            'fixtures_sha256': digest(dumps(FIXTURES)), 'arm_order': list(ARMS), 'guard': E.REVISION,
            'schemas_sha256': {'action_first': digest(dumps(w2.schema('action_first'))), 'extract_anchored': digest(dumps(w2.EXTRACT_SCHEMA))},
            'wire': 'WP-W1 runners.wire_json', 'config': CONFIG, 'consumer_sampling_seed': 13, 'native_oracle_visibility': False,
            'primary_metric': 'per arm: decision-exact rows (all fields except project) and WRONG COMMITTED decisions (action A/B/NONE different from the oracle)',
            'decision_rule': 'the tool counts as safe with real handoffs if extract_anchored has 0 wrong committed decisions in every model/source arm; it counts as useful only if it also has more decision-exact rows than action_first of the same model/source',
            'expectation_recorded_before_inference': 'real B2 handoffs rarely carry complete rules (earlier BEFUND: 0/4 and 2/4 transport), so mostly UNKNOWN is expected',
            'scope': 'TOOL_WITH_REAL_PRODUCER_DIAGNOSIS_ONLY_NOT_STEP2', 'canonical_gate_pass': False, 'binding': binding(installed)}


def run_arm(home, installed, arm, inputs, rows_done):
    model_role, source, mode = arm.split('/')
    initialize(home); save_config(home, CONFIG); installed_links(home, installed)
    r = Runtime(home)
    try:
        target = r.models.path_for(model_role)
        r.models.router = lambda role: target if role == 'C3_LANGUAGE' else None
        for fixture in FIXTURES:
            if (fixture['id'], arm) in rows_done: continue
            messages = inputs[(source, fixture['id'])]
            row = {'fixture': fixture['id'], 'arm': arm, 'control': fixture['control'], 'consumer_model_role': model_role,
                   'consumer_model_sha256': file_hash(target), 'source_arm': source, 'mode': mode, 'raw_answer': '',
                   'status': 'RUNNING', 'oracle_visible_to_native': False}
            started = time.monotonic()
            schema = w2.EXTRACT_SCHEMA if mode == 'extract_anchored' else w2.schema('action_first')
            try:
                runner = r.pool.get('C3_LANGUAGE'); deadline = time.monotonic()+CONFIG['deadline_seconds']
                for chunk in runner.generate(messages, r.cancel_event, deadline, CONFIG['answer_tokens'], schema, seed=13):
                    row['raw_answer'] += chunk
                row['consumer_metrics'] = dict(runner.last_metrics)
                answer = row['raw_answer']
                if mode == 'extract_anchored': answer, row['tool'] = run_anchored(answer, messages)
                row['answer'] = answer or row['raw_answer']
                row['score'] = score_decision(row['answer'], fixture['oracle'])
                row['status'] = 'RECORDED' if runner.last_metrics.get('status') == 'FINAL' else 'STRUCTURAL_FAIL'
            except (Exception, KeyboardInterrupt) as exc:
                row.update(status='INTERRUPTED' if isinstance(exc, KeyboardInterrupt) else 'ERROR', error_type=type(exc).__name__,
                           error=str(exc)[:500], score={'utility': 0., 'exact': False, 'contradictions': ['inference_failed']})
            row['decision_exact'] = w2.decision_exact(row['score'])
            row['elapsed_s'] = time.monotonic()-started
            try: row['action'] = json.loads(row.get('answer') or '').get('action')
            except (ValueError, AttributeError): row['action'] = None
            row['wrong_committed'] = row['action'] in ('A', 'B', 'NONE') and row['action'] != fixture['oracle']['action']
            yield row
            if row['status'] == 'INTERRUPTED': return
    finally:
        r.close()


def aggregate(rows):
    res = {}
    for arm in ARMS:
        items = [r for r in rows if r['arm'] == arm]
        res[arm] = {'rows': len(items), 'decision_exact': sum(bool(r['decision_exact']) for r in items),
                    'wrong_committed': sum(bool(r.get('wrong_committed')) for r in items),
                    'unknown': sum(r.get('action') == 'UNKNOWN' for r in items), 'actions': [r.get('action') for r in items],
                    'mean_strict_utility': sum(r['score']['utility'] for r in items)/len(items) if items else None,
                    'structural_failures': sum(r['status'] != 'RECORDED' for r in items)}
    for m in consumer.MODELS:
        for s in SOURCE_ARMS:
            a, t = res[m+'/'+s+'/action_first'], res[m+'/'+s+'/extract_anchored']
            res[m+'/'+s+'/verdict'] = {'safe': t['rows'] == 8 and t['wrong_committed'] == 0,
                                       'useful': t['rows'] == 8 and t['wrong_committed'] == 0 and t['decision_exact'] > a['decision_exact']}
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--installed-home', type=Path, required=True)
    ap.add_argument('--rule-transport-report', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--register-only', action='store_true')
    a = ap.parse_args()
    registration = preregistration(a.installed_home, a.rule_transport_report)
    path = a.out.with_suffix('.preregistration.json'); a.out.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if json.loads(path.read_text()) != registration: raise ValueError('Preregistration binding changed; use a fresh output path')
    else: atomic_write(path, dumps(registration))
    sha = file_hash(path)
    if a.register_only:
        print(dumps({'status': 'PREREGISTERED_NO_INFERENCE', 'path': str(path), 'sha256': sha})); return
    inputs = recorded_inputs(a.rule_transport_report)
    if a.out.exists():
        out = json.loads(a.out.read_text())
        if out.get('preregistration_sha256') != sha: raise ValueError('Resume preregistration changed')
        if out.get('row_sha256') != {r['fixture']+'/'+r['arm']: digest(dumps(r)) for r in out['rows']}: raise ValueError('Resume recorded row bytes changed')
    else:
        out = {'schema': 'CALC_TOOL_PRODUCER_ABLATION_V1', 'status': 'RUNNING', 'rows': [], 'row_sha256': {},
               'preregistration_sha256': sha, 'canonical_gate_pass': False, 'phone_measured': False}
        atomic_write(a.out, dumps(out))
    done = {(r['fixture'], r['arm']) for r in out['rows']}
    work = a.out.with_suffix('.checkpoint'); work.mkdir(exist_ok=True)
    for arm in ARMS:
        if all((f['id'], arm) in done for f in FIXTURES): continue
        if binding(a.installed_home) != registration['binding']:
            out['status'] = 'ARTIFACT_CHANGED'; atomic_write(a.out, dumps(out)); raise ValueError('Binding changed during ablation')
        home = work/arm.replace('/', '-')
        if home.exists(): shutil.rmtree(home)
        for row in run_arm(home, a.installed_home, arm, inputs, done):
            out['rows'].append(row); out['row_sha256'][row['fixture']+'/'+arm] = digest(dumps(row))
            out['summary'] = aggregate(out['rows']); atomic_write(a.out, dumps(out))
            print(dumps({'fixture': row['fixture'], 'arm': arm, 'action': row.get('action'), 'decision_exact': row['decision_exact'],
                         'wrong_committed': row['wrong_committed']}), flush=True)
            if row['status'] == 'INTERRUPTED':
                out['status'] = 'INTERRUPTED'; atomic_write(a.out, dumps(out)); raise KeyboardInterrupt
        shutil.rmtree(home, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    out['installed_artifacts_unchanged'] = binding(a.installed_home) == registration['binding']
    out['status'] = ('RECORDED_DIAGNOSIS' if all(r['status'] == 'RECORDED' for r in out['rows']) else 'STRUCTURAL_FAIL') if out['installed_artifacts_unchanged'] else 'ARTIFACT_CHANGED'
    out['summary'] = aggregate(out['rows']); atomic_write(a.out, dumps(out))


if __name__ == '__main__': main()
