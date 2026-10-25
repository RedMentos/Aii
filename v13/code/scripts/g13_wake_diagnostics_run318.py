"""Run318 read-only instrumentation of the original G13 native longrun soak.

The original soak, scheduler, Runtime, SleepRuntime and acceptance checks are
unchanged. A red native G13 verdict remains red. All observations are diagnostic.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import longrun_soak as L
from v13.common import atomic_write, dumps
from v13.sleep import SleepRuntime

START_UTC = 1792925474.0  # 2026-10-25 10:51:14Z, preregistered
SCHEMA = 'V13_RUN318_G13_WAKE_DIAG_V1'


def snapshot(r):
    """Read-only, content-free observation; no resource guard update or queue dispatch."""
    try:
        st = r.sleep.scheduler.pending()
        pending = dict(Counter(x.get('status', 'UNKNOWN') + ':' + x.get('kind', 'UNKNOWN') for x in st))
    except Exception as exc:
        pending = {'UNAVAILABLE:' + type(exc).__name__: 1}
    try:
        idle = bool(r.idle())
    except Exception:
        idle = None
    try:
        jobs = r.jobs.qsize()
    except Exception:
        jobs = None
    return {'idle': idle, 'jobs_qsize': jobs,
            'guard_state_readonly': getattr(getattr(r, 'guard', None), 'state', None),
            'pending_status_kind_counts': pending}


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raise FileExistsError('Run318 journal exists: refuse overwrite')
        self.lock = threading.Lock()
        self.n = 0
        self.wait_timeouts = 0
        self.tick_none_busy = 0
        self.guard_states = Counter()

    def append(self, row):
        with self.lock:
            self.n += 1
            row['seq'] = self.n
            if row.get('kind') == 'wait_idle' and not row.get('success'):
                self.wait_timeouts += 1
            if row.get('kind') == 'tick' and row.get('returned') is None and row.get('before', {}).get('idle') is False:
                self.tick_none_busy += 1
            if row.get('kind') == 'tick':
                self.guard_states[str(row.get('before', {}).get('guard_state_readonly'))] += 1
            with self.path.open('a', encoding='utf-8') as stream:
                stream.write(dumps(row) + '\n')
                stream.flush()
                os.fsync(stream.fileno())


@contextmanager
def instrument(journal):
    original_tick = SleepRuntime.tick
    original_wait = L.wait_idle

    def tick(self, force=False):
        before = snapshot(self.r)
        start = time.monotonic()
        event = None
        error = None
        try:
            event = original_tick(self, force=force)
            return event
        except BaseException as exc:
            error = type(exc).__name__
            raise
        finally:
            journal.append({
                'kind': 'tick', 'force': bool(force),
                'elapsed_s': round(time.monotonic() - start, 4),
                'returned': event.get('kind') if isinstance(event, dict) else None,
                'event_id': event.get('id') if isinstance(event, dict) else None,
                'error': error, 'before': before, 'after': snapshot(self.r),
            })

    def wait_idle(r, timeout=60.):
        before = snapshot(r)
        start = time.monotonic()
        ok = False
        error = None
        try:
            ok = original_wait(r, timeout)
            return ok
        except BaseException as exc:
            error = type(exc).__name__
            raise
        finally:
            journal.append({
                'kind': 'wait_idle', 'timeout_s': timeout, 'success': bool(ok),
                'elapsed_s': round(time.monotonic() - start, 4),
                'error': error, 'before': before, 'after': snapshot(r),
            })

    SleepRuntime.tick = tick
    L.wait_idle = wait_idle
    try:
        yield
    finally:
        SleepRuntime.tick = original_tick
        L.wait_idle = original_wait


def run(home, out_dir, native=False, models_from=None, days=2, turns=2):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    trace = out_dir / 'RUN318_TRACE.jsonl'
    summary_path = out_dir / 'RUN318_SUMMARY.json'
    if trace.exists() or summary_path.exists():
        raise FileExistsError('Run318 raw evidence already exists; refuse overwrite')
    journal = Journal(trace)
    summary = {
        'schema': SCHEMA,
        'evidence_level': 'LINUX_NATIVE_G13' if native else 'FIXTURE_ONLY',
        'native': bool(native), 'simulated_start_utc': START_UTC,
        'days_requested': days, 'turns_per_day': turns,
        'status': 'INCOMPLETE', 'soak_verdict': None,
        'original_gates': {'STEP2': 'UTILITY_FAIL', 'B3_L1': 'FAIL',
                           'Body_JEPA': 'UNAVAILABLE', 'jepa_weight': 0,
                           'V13': 'INCOMPLETE'},
        'claim_limit': 'Instrumentation only; unchanged original soak checks; not Redmi or native training',
    }
    def save():
        atomic_write(summary_path, (dumps(summary) + '\n').encode())
    save()
    try:
        with instrument(journal):
            report = L.soak(home, days=days, turns=turns, native=native,
                            models_from=models_from, start=START_UTC)
        summary['soak_verdict'] = report['verdict']
        summary['days'] = [{k: d.get(k) for k in ('day', 'checks', 'wake_order',
                           'seconds', 'error', 'job_errors', 'scheduler')} for d in report['days']]
        summary['status'] = 'CAPTURE_COMPLETE'
    except BaseException as exc:
        summary['status'] = 'CAPTURE_INTERRUPTED'
        summary['error'] = {'type': type(exc).__name__, 'message': str(exc)[:300]}
    finally:
        summary['trace_rows'] = journal.n
        summary['wait_idle_timeouts'] = journal.wait_timeouts
        summary['tick_none_while_busy'] = journal.tick_none_busy
        summary['observed_guard_states'] = dict(journal.guard_states)
        summary['trace_path'] = str(trace)
        save()
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--home', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--native', action='store_true')
    ap.add_argument('--models-from')
    ap.add_argument('--days', type=int, default=2)
    ap.add_argument('--turns', type=int, default=2)
    args = ap.parse_args()
    if args.native and not args.models_from:
        ap.error('native requires --models-from')
    report = run(args.home, args.out_dir, native=args.native,
                 models_from=args.models_from, days=args.days, turns=args.turns)
    print(dumps({'status': report['status'], 'soak_verdict': report['soak_verdict'],
                 'trace_rows': report['trace_rows'],
                 'wait_idle_timeouts': report['wait_idle_timeouts'],
                 'tick_none_while_busy': report['tick_none_while_busy']}))
    if report['status'] != 'CAPTURE_COMPLETE' or report['soak_verdict'] != 'PASS':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
