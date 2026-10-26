"""Run554 pinned C3 native JEF goal + typed operator proof (Linux, not Redmi).

A synthetic failed first request only creates a USER goal; the later answer must
come from real pinned native C3 in native mode. Fixture mode is separately labeled
and never passes the native gate. No answer-correctness/JEPA/STEP2 claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from v13.common import atomic_write, dumps
from v13.runtime import Runtime
from v13.operator import Operator
from v13.agi import hub, live
from v13.models import ModelManager
from longrun_soak import attach_native_assets
from native_second_turn_probe_run315 import fixture_speaker, wait_idle, sha256_file

QUESTION = 'Explain the fictional Project RUN554-ORBIT plan briefly.'
GATES = {'STEP2': 'UTILITY_FAIL', 'B3_L1': 'FAIL',
         'Body_JEPA': 'UNAVAILABLE', 'jepa_weight': 0,
         'Redmi': 'UNMEASURED', 'V13': 'INCOMPLETE'}


def probe(home, models_from, out, native=True, timeout=140):
    home, out = Path(home), Path(out)
    home.mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {'schema': 'V13_RUN554_NATIVE_JEF_GOAL_V1',
              'evidence_level': 'LINUX_NATIVE_C3' if native else 'FIXTURE_ONLY',
              'native': bool(native), 'status': 'INCOMPLETE',
              'gates': dict(GATES), 'question': QUESTION,
              'claim_limit': 'Structural JEF/TTY goal lifecycle; no semantic answer accuracy, STEP2, JEPA or Redmi'}
    def save():
        atomic_write(out, (dumps(report) + '\n').encode())
    save()
    r = None
    try:
        if native:
            if models_from is None:
                raise ValueError('Native proof requires installed pinned public artifacts')
            attach_native_assets(home, models_from)
            specs = json.loads((ROOT / 'specs/models.json').read_text())
            model = ModelManager(home).path_for('C3_LANGUAGE')
            expected = specs['models']['language']['files'][0]['sha256']
            actual = sha256_file(model)
            server = home / 'bin/llama-server'
            report['model'] = {'model_id': specs['models']['language']['model_id'],
                               'revision': specs['models']['language']['revision'],
                               'sha256': actual, 'expected_sha256': expected}
            report['runner_sha256'] = sha256_file(server) if server.is_file() else None
            report['checks'] = {'model_hash': actual == expected,
                                'runner_present': server.is_file()}
            save()
            if not all(report['checks'].values()):
                raise ValueError('Pinned native artifact hash/runner unavailable')
        r = Runtime(home)
        r.sleep.cycle.set_policy('enabled', 'off')
        r.cfg.update(route_override='simple', observer_mode='off',
                     memory_embedding='off', duplex_mode='off',
                     history_turns=0, answer_tokens=32, deadline_seconds=90,
                     c3_decode_mode='server')
        r.session = r.store.new_session('Run554 JEF native')
        if not native:
            fixture_speaker(r)
        first = r.store.event(r.session, QUESTION)
        live.goal_turn(r, first, {}, 'ERROR')
        goals = [g for g in hub(r).goals.tree('OPEN') if 'event:' + first['event_id'] in g['evidence']]
        if len(goals) != 1:
            raise ValueError('Unresolved request did not create exactly one USER goal')
        gid = goals[0]['id']
        report['initial'] = {'event_id': first['event_id'], 'goal_id': gid,
                             'status': goals[0]['status'], 'origin': goals[0]['origin']}
        save()

        t0 = time.monotonic()
        eid = r.submit(QUESTION)
        if not wait_idle(r, timeout):
            r.cancel()
            wait_idle(r, 15)
            raise TimeoutError('Real C3 turn failed to settle')
        answer = r.last_answer()
        if not answer or answer['event_id'] != eid:
            raise ValueError('Missing terminal answer for native event')
        metadata = json.loads(answer['metadata'])
        receipt = r.store.one(
            "SELECT id,text,metadata FROM messages WHERE event_id=? AND session_id=? "
            "AND role='assistant' AND status='FINAL' ORDER BY id DESC LIMIT 1",
            (eid, r.session))
        g = hub(r).goals.get(gid)
        report['answer'] = {'event_id': eid, 'status': answer['status'],
                            'text': answer['text'][:500],
                            'elapsed_s': round(time.monotonic()-t0, 3),
                            'model_generated': metadata.get('model_generated'),
                            'model_revision': metadata.get('model_revision'),
                            'runner': metadata.get('runner', {})}
        report['goal_after_answer'] = {'id': gid, 'status': g['status'],
                                       'notes': g['notes'][-3:]}
        checks = report.setdefault('checks', {})
        checks['final'] = answer['status'] == 'FINAL'
        checks['native_generated'] = metadata.get('model_generated') is True if native else False
        checks['own_final_receipt'] = bool(receipt and receipt['text'].strip()
            and not json.loads(receipt['metadata']).get('reference_only'))
        checks['goal_done'] = g['status'] == 'DONE'
        checks['receipt_note'] = bool(receipt and any('message '+str(receipt['id']) in n for n in g['notes']))
        save()

        op = Operator(r)
        reopened = json.loads(op.run(':growth goal reopen '+gid))
        refused = False
        try:
            op.run(':growth goal done '+gid, origin='MODEL')
        except ValueError:
            refused = True
        completed = json.loads(op.run(':growth goal done '+gid))
        checks['reopened'] = reopened['status'] == 'OPEN' and reopened['changed'] is True
        checks['model_operator_refused'] = refused
        checks['manual_completed'] = completed['status'] == 'DONE' and completed['changed'] is True
        checks['integrity_clean'] = not r.store.integrity(True)
        report['operator'] = {'reopen': reopened, 'done': completed, 'model_refused': refused}
        save()
        r.close()
        checks['processes_reaped'] = not (r.pool.pids()+r.needle.pids())
        r = None

        restarted = Runtime(home)
        try:
            after = hub(restarted).goals.get(gid)
            checks['restart_persisted'] = after['status'] == 'DONE' and after['origin'] == 'USER'
            report['restart'] = {'status': after['status'], 'origin': after['origin'],
                                 'progress': after['progress']}
            checks['restart_integrity_clean'] = not restarted.store.integrity(True)
        finally:
            restarted.close()
        mandatory = [k for k in checks if k != 'native_generated'] if not native else list(checks)
        report['integration_pass'] = all(checks[k] for k in mandatory)
        report['status'] = 'COMPLETE' if report['integration_pass'] else 'INTEGRATION_FAIL'
        save()
        return report
    except BaseException as exc:
        report['status'] = 'ERROR'
        report['error'] = {'type': type(exc).__name__, 'message': str(exc)[:400]}
        save()
        raise
    finally:
        if r is not None:
            r.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--home', required=True)
    p.add_argument('--models-from')
    p.add_argument('--out', required=True)
    p.add_argument('--fixture', action='store_true')
    p.add_argument('--timeout', type=int, default=140)
    a = p.parse_args()
    report = probe(a.home, a.models_from, a.out, native=not a.fixture, timeout=a.timeout)
    print(dumps({'status': report['status'], 'native': report['native'],
                 'integration_pass': report['integration_pass'],
                 'checks': report['checks']}))
    if not report['integration_pass']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
