#!/usr/bin/env python3
"""Run51: source-backed F1/F5 second-attempt C3 native witness, default-off."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import time

from v13.common import atomic_write, dumps
from v13.config import initialize, save_config
from v13.runtime import Runtime
from v13.memory import Memory
from v13.source_consumer import verified_recall_messages
from scripts.run47_jef_c3_typed_receiver_native import CONFIG, NEGATIVE, sha
from tests.integration_step2_utility import installed_artifacts, installed_links

FIXTURE_SHA256 = '160128b2f5df2a5798ae7ec62687e6be5a8e61f6c6b2dad43f1ad253ee592ecc'
PROJECTS = ('Cypress', 'Lark', 'Delta')


def load_fixture(path):
    raw = Path(path).read_bytes()
    if sha(raw) != FIXTURE_SHA256:
        raise ValueError('RUN51_FIXTURE_SHA')
    data = json.loads(raw)
    if (data.get('schema') != 'v13.run51.f1f5_second_attempt_seed467.v1'
            or data.get('seed') != 467
            or [f.get('id') for f in data.get('fixtures', [])] != list(PROJECTS)):
        raise ValueError('RUN51_COHORT')
    for f in data['fixtures']:
        if (set(f) != {'id', 'first_query', 'correction_event', 'key', 'value', 'followup', 'oracle_amount'}
                or f['key'] != 'Project ' + f['id'] + ' budget'
                or f['value'] != str(f['oracle_amount']) + ' Euro'
                or f['id'] not in f['first_query'] or f['id'] not in f['followup']
                or f['id'] not in f['correction_event']):
            raise ValueError('RUN51_FIXTURE_SHAPE')
    return data


def score(answer, amount, project):
    if type(answer) is not str or len(answer) > 4096:
        return 0
    nums = re.findall(r'(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])', answer)
    named = re.findall(r'\bProject\s+([A-Za-z][A-Za-z0-9_-]*)\b', answer, re.I)
    return int(nums == [str(amount)] and all(x.lower() == project.lower() for x in named))


def run_row(home, installed, fixture):
    initialize(home)
    save_config(home, CONFIG)
    installed_links(home, installed)
    r = Runtime(home)
    row = {'fixture': fixture['id'], 'status': 'ERROR',
           'first_query_sha256': sha(fixture['first_query'].encode()),
           'correction_event_sha256': sha(fixture['correction_event'].encode()),
           'followup_sha256': sha(fixture['followup'].encode()),
           'oracle_visible_to_native_as_oracle': False,
           'native_answer': '', 'native_c3_final': False,
           'native_model_calls': 0, 'baseline_model_calls': 0,
           'process_releases': [], 'processes_reaped': False,
           'score': {'correct': 0}}
    start = time.monotonic()
    try:
        mem = Memory(r.store, CONFIG)
        first = r.store.event(r.session, fixture['first_query'])
        baseline = verified_recall_messages(CONFIG, fixture['first_query'], r.session, mem)
        row['first_source_ref'] = first['source_ref']
        row['baseline_decision'] = baseline['decision']['status']
        row['baseline_reason'] = baseline['decision']['reason']
        row['baseline_has_messages'] = baseline['messages'] is not None
        correction = r.store.event(r.session, fixture['correction_event'])
        row['correction_source_ref'] = correction['source_ref']
        mid = mem.feedback(correction['event_id'], 'fact', fixture['value'],
                           permission='record', key=fixture['key'], scope='session')
        row['memory_id'] = mid
        row['memory_row'] = r.store.one('SELECT * FROM memories WHERE id=?', (mid,))
        row['feedback_row'] = r.store.one('SELECT * FROM feedback WHERE event_id=? AND kind=?',
                                          (correction['event_id'], 'fact'))
        row['f1f5_packets'] = r.store.rows(
            "SELECT id,kind,event_id,generation_id,payload FROM packets "
            "WHERE event_id=? AND kind IN ('MemoryRecord','HumanDecision')",
            (correction['event_id'],))
        followup = r.store.event(r.session, fixture['followup'])
        row['followup_source_ref'] = followup['source_ref']
        admitted = verified_recall_messages(CONFIG, fixture['followup'], r.session, mem)
        row['second_decision'] = admitted['decision']['status']
        row['second_reason'] = admitted['decision']['reason']
        row['second_source'] = admitted['decision'].get('source')
        if admitted['messages'] is None:
            raise ValueError('RUN51_NO_SOURCE_BOUND_PROMPT')
        msgs = admitted['messages']
        row['native_prompt'] = msgs
        row['native_prompt_sha256'] = sha(dumps(msgs).encode())
        runner = r.pool.get('C3_LANGUAGE')
        row['native_model_calls'] += 1
        row['native_answer'] = ''.join(runner.generate(
            msgs, r.cancel_event, time.monotonic() + 90, 96, None, seed=13))
        row['native_c3_metrics'] = dict(runner.last_metrics)
        row['native_c3_final'] = runner.last_metrics.get('status') == 'FINAL'
        r.pool.unload()
        row['score']['correct'] = score(row['native_answer'], fixture['oracle_amount'], fixture['id'])
        row['status'] = ('RECORDED' if row['baseline_decision'] == 'CLARIFY'
                         and not row['baseline_has_messages']
                         and row['second_decision'] == 'ADMITTED'
                         and row['native_c3_final']
                         and row['native_model_calls'] == 1 else 'STRUCTURAL_FAIL')
    except (Exception, KeyboardInterrupt) as exc:
        row['error_type'] = type(exc).__name__
        row['error'] = str(exc)[:500]
        row['status'] = 'INTERRUPTED' if isinstance(exc, KeyboardInterrupt) else 'ERROR'
    finally:
        try:
            r.close()
        except Exception as exc:
            row['close_error_type'] = type(exc).__name__
            row['status'] = 'STRUCTURAL_FAIL'
        row['process_releases'] = list(r.pool.release_history)
        row['processes_reaped'] = bool(row['process_releases']) and all(
            x.get('process_reaped') is True for x in row['process_releases'])
        if row['status'] == 'RECORDED' and not row['processes_reaped']:
            row['status'] = 'STRUCTURAL_FAIL'
        if row['status'] != 'RECORDED':
            row['score']['correct'] = 0
        row['elapsed_seconds'] = round(time.monotonic() - start, 3)
    return row


def run(installed, out, fixture_path):
    data = load_fixture(fixture_path)
    if out.exists():
        raise FileExistsError('RUN51_OUTPUT_EXISTS')
    out.mkdir(parents=True)
    binding = installed_artifacts(installed)
    report = {'schema': 'v13.run51.f1f5_second_attempt_native_result.v1',
              'fixture_sha256': FIXTURE_SHA256, 'seed': 467,
              'binding': binding, 'registered': True, 'rows': [],
              'row_sha256': {}, 'status': 'RUNNING', 'negative_gates': NEGATIVE}
    atomic_write(out / 'report.json', dumps(report))
    for f in data['fixtures']:
        home = out / f['id']
        if home.exists():
            raise FileExistsError('RUN51_HOME_EXISTS')
        row = run_row(home, installed, f)
        report['rows'].append(row)
        report['row_sha256'][f['id']] = sha(dumps(row).encode())
        atomic_write(out / 'report.json', dumps(report))
        print(dumps({'fixture': f['id'], 'status': row['status'],
                     'correct': row['score']['correct']}), flush=True)
    report['installed_binding_unchanged'] = installed_artifacts(installed) == binding
    structural = all(r['status'] == 'RECORDED' for r in report['rows'])
    correct = sum(r['score']['correct'] for r in report['rows'])
    report['second_attempt_signal'] = (structural and correct >= 2
                                       and report['installed_binding_unchanged'])
    report['status'] = ('SOURCE_BACKED_SECOND_ATTEMPT_SIGNAL_ONLY' if report['second_attempt_signal']
                        else 'UTILITY_FAIL' if structural else 'STRUCTURAL_RED')
    atomic_write(out / 'report.json', dumps(report))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--home', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--fixture', type=Path, required=True)
    args = p.parse_args()
    report = run(args.home, args.out, args.fixture)
    print(dumps({'status': report['status'], 'second_attempt_signal': report['second_attempt_signal']}))


if __name__ == '__main__':
    main()