#!/usr/bin/env python3
"""WP-Z7 phone measurements §24.33 (scheduling / memory residency), §24.14 (control-fabric overhead) and the
proceduralization latency of repeated tasks, on the real Runtime with the installed models (Redmi via HANDY_PFLICHT.sh).

  schedules  one fresh home per observer_schedule arm (A_THEN_B_SEQUENTIAL, B_THEN_A_SEQUENTIAL, ALWAYS_BOTH_ASYNC,
             JEF_FIRST_THEN_BOTH, SAMPLED_OBSERVER); same tasks per arm (utility_bench2.tasks, seed 23, first N per kind)
  repeat     one session, the same task kind N times with fresh numbers (default config): does the per-turn latency fall
             (skills / fast path) without losing quality?
Per turn: pass (WP-T3b regex), time to first body offer, time to FINAL answer, wall time incl. post-commit observers,
llama-server RSS/HWM and major page faults (/proc), MemAvailable, battery temperature/percent. Per arm: the §24.14
control budget report (v13.control_budget.report) over the arm's turns.
It decides nothing and grants no authority; the evaluation happens afterwards in the cloud.
Usage: z7_residency_bench.py <installed_home> <out.json> [--mode schedules|repeat] [--per-kind 3] [--repeat 20] [--arms a,b]
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.common import atomic_write, file_hash  # noqa: E402
import utility_bench as U  # noqa: E402
import utility_bench2 as U2  # noqa: E402

SCHEDULES = ('A_THEN_B_SEQUENTIAL', 'B_THEN_A_SEQUENTIAL', 'ALWAYS_BOTH_ASYNC', 'JEF_FIRST_THEN_BOTH', 'SAMPLED_OBSERVER')
FINAL = ('FINAL', 'CANCELLED', 'DEADLINE', 'ERROR', 'INTERRUPTED')


def mean_known(values):
    values = [x for x in values if x is not None]
    return round(sum(values)/len(values), 2) if values else None


def selected_tasks(per_kind):
    kinds = {}
    for f in U2.tasks(seed=23): kinds.setdefault(f[0].rstrip('0123456789'), []).append(f)
    return [f for k in sorted(kinds) for f in kinds[k][:per_kind]]


def input_binding(installed, mode, arms, per_kind, repeat):
    """Bind this attempt's declared inputs; manifest hashes are not model-byte verification."""
    app = Path(__file__).resolve().parents[1]
    paths = list((app/'v13').rglob('*.py')) + list((app/'specs').glob('*.json'))
    paths += [Path(__file__), Path(U.__file__), Path(U2.__file__)]
    sources = {str(p.relative_to(app)): file_hash(p) for p in sorted(set(paths))}
    configs = {p.name: file_hash(p) for p in sorted((installed/'config').glob('*.json'))}
    tasks = selected_tasks(per_kind) if mode == 'schedules' else [f for f in U2.tasks(seed=29, per_kind=repeat) if f[0].startswith('summary')][:repeat]
    payload = {'mode': mode, 'arms': arms if mode == 'schedules' else [], 'per_kind': per_kind,
               'repeat': repeat, 'sources': sources, 'installed_config_sha256': configs,
               'tasks': tasks, 'benchmark_config': U2.BENCH_CFG,
               'model_verification': 'declared manifest only; not a model-byte verification'}
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return {'sha256': hashlib.sha256(raw.encode()).hexdigest(), 'inputs': payload}


class ProgressJournal:
    """Separate attempts; every completed row is durable before starting another turn.

    Replaying an incomplete arm is a new experiment, never a transparent resume.
    A SIGKILL can lose the current row, but cannot erase earlier fsynced rows.
    """
    def __init__(self, output, binding, new_attempt=False):
        self.output = Path(output)
        self.root = self.output.with_name(self.output.name+'.attempts')
        if (self.output.exists() or self.root.exists()) and not new_attempt:
            raise ValueError('Previous residency evidence exists; preserve it and use --new-attempt for an explicitly separate attempt')
        try: self.root.mkdir(parents=True, exist_ok=new_attempt)
        except FileExistsError as exc:
            raise ValueError('Residency attempt already claimed; preserve it and use --new-attempt for a separate attempt') from exc
        self.attempt_id = uuid.uuid4().hex
        self.directory = self.root/self.attempt_id
        self.directory.mkdir(parents=True)
        if self.output.exists():
            old = self.root/('previous-report-'+file_hash(self.output)+'.json')
            if not old.exists(): atomic_write(old, self.output.read_bytes())
        self.path = self.directory/'progress.jsonl'
        self.binding = binding; self.rows = 0
        self._state('RUNNING')
        self.append('START', {'binding': binding})

    def _state(self, status, **extra):
        atomic_write(self.directory/'state.json', json.dumps({'schema': 'V13_Z7_PROGRESS_V1', 'attempt_id': self.attempt_id,
                     'status': status, 'completed_rows': self.rows, 'binding': self.binding, **extra}, sort_keys=True))

    def append(self, kind, payload):
        record = {'kind': kind, 'attempt_id': self.attempt_id, 'binding_sha256': self.binding['sha256'], **payload}
        with self.path.open('a') as f:
            f.write(json.dumps(record, sort_keys=True, allow_nan=False)+'\n'); f.flush(); os.fsync(f.fileno())
        if kind == 'ROW': self.rows += 1
        self._state('RUNNING')

    def row(self, arm, row):
        self.append('ROW', {'arm': arm, 'row': row})

    def finish(self, status):
        self.append(status, {})
        self._state(status, journal_sha256=file_hash(self.path))

    def reference(self):
        return {'attempt_id': self.attempt_id, 'binding_sha256': self.binding['sha256'],
                'directory': str(self.directory), 'journal_sha256': file_hash(self.path), 'completed_rows': self.rows}


def proc_children(root=None):
    """Namespace-local PIDs of descendants, even with an ancestor-mounted /proc."""
    from v13.resources import process_memory
    root = os.getpid() if root is None else root
    visible = process_memory(root)['resolved_proc_pid']
    if visible is None: return []
    own_ns = os.readlink('/proc/self/ns/pid')
    parents, local = {}, {}
    for d in Path('/proc').iterdir():
        if d.name.isdigit():
            try:
                if os.readlink(d/'ns/pid') != own_ns: continue
                status = dict(l.split(':', 1) for l in (d/'status').read_text().splitlines() if ':' in l)
                if status.get('NSpid', '').split(): inner = int(status['NSpid'].split()[-1])
                elif visible == root: inner = int(d.name)
                else: continue
                ppid = int((d/'stat').read_text().rsplit(')', 1)[1].split()[1]); parents.setdefault(ppid, []).append(int(d.name)); local[int(d.name)] = inner
            except (OSError, ValueError, IndexError):
                continue
    out, todo = [], [visible]
    while todo:
        p = todo.pop()
        for c in parents.get(p, []): out.append(local[c]); todo.append(c)
    return out


def proc_stats(pid):
    from v13.resources import process_memory
    try:
        measured = process_memory(pid); visible = measured['resolved_proc_pid']
        if visible is None: return None
        path = Path('/proc/%d' % visible)
        before = (path/'stat').read_text().rsplit(')', 1)[1].split()
        status = dict(l.split(':', 1) for l in (path/'status').read_text().splitlines() if ':' in l)
        cmd = (path/'cmdline').read_bytes().split(b'\0')[0].decode(errors='replace')
        stat = (path/'stat').read_text().rsplit(')', 1)[1].split()
        if before[19] != stat[19]: return None  # PID was reused during the read.
        kb = lambda k: int(status[k].split()[0]) if k in status else None
        rss, hwm = kb('VmRSS'), kb('VmHWM')
        return {'pid': pid, 'name': Path(cmd).name, 'rss_mb': round(rss/1024, 1) if rss is not None else None, 'hwm_mb': round(hwm/1024, 1) if hwm is not None else None,
                'majflt': int(stat[9]), 'minflt': int(stat[7])}
    except (OSError, ValueError, IndexError):
        return None


def device_state(home):
    from v13.resources import snapshot
    s = snapshot(home)
    available = s['mem_available_bytes']
    return {'mem_available_mb': round(available/2**20) if available is not None else None, 'battery_temp_c': s['battery_temperature_c'],
            'battery_percent': s['battery_percent'], 'charging': s['charging']}


def fresh_runtime(installed, tmp, extra):
    from v13.config import initialize, save_config
    from v13.runtime import Runtime
    home = Path(tmp); cfg = initialize(home)
    for n in ('models', 'bin'):
        shutil.rmtree(home/n); (home/n).symlink_to(installed/n, target_is_directory=True)
    shutil.copyfile(installed/'config/models.json', home/'config/models.json')
    save_config(home, cfg | {'learning_mode': 'RECORD_ONLY', 'teacher_enabled': False, 'history_turns': 0} | U2.BENCH_CFG | extra)
    return Runtime(home)


def turn(r, text, nums, checks, budget=900):
    from v13.proofs import audit_event
    t0 = time.monotonic(); eid = r.submit(text); answer_s = first_offer_s = None; peak = {}; status = None; timed_out = False
    child_peak = None; child_samples = child_incomplete = 0
    # Poll once even when a short turn has already become idle after submit.
    while True:
        now = time.monotonic()-t0
        if first_offer_s is None and r.store.one("SELECT 1 FROM packets WHERE event_id=? AND kind='OfferPacket' LIMIT 1", (eid,)):
            first_offer_s = round(now, 2)
        m = r.store.one("SELECT status FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1", (eid,))
        if m:
            status = m['status']
            if answer_s is None and status == 'FINAL': answer_s = round(now, 2)
        children = proc_children(); rss = []
        for p in children:
            st = proc_stats(p)
            if st and st['rss_mb'] is not None:
                rss.append(st['rss_mb'])
                old = peak.get(p)
                if old:
                    st = dict(st, rss_mb=max(st['rss_mb'], old['rss_mb']),
                              hwm_mb=max(x for x in (st['hwm_mb'], old['hwm_mb']) if x is not None)
                              if st['hwm_mb'] is not None or old['hwm_mb'] is not None else None)
                peak[p] = st
        if children:
            if len(rss) == len(children):
                child_samples += 1; child_peak = max(child_peak or 0., sum(rss))
            else: child_incomplete += 1
        if r.idle(): break
        if now > budget:
            r.cancel(); timed_out = True; break
        time.sleep(.25)
    a = audit_event(r.store, eid); out = a.get('output') or ''
    ok, num = U.score(out, nums, checks)
    post = {json.loads(x['metrics']).get('id') for x in r.store.rows("SELECT metrics FROM telemetry WHERE kind='postcommit_offer' AND event_id=?", (eid,))}
    meta = a.get('output_metadata') or {}
    return {'pass': status == 'FINAL' and not timed_out and all(ok.values()) and all(num.values()), 'answer_s': answer_s, 'first_offer_s': first_offer_s,
            'wall_s': round(time.monotonic()-t0, 2), 'status': status, 'budget_exceeded': timed_out,
            'pre_offers': sorted({o['role'] for o in a.get('offers', []) if o.get('packet_id') not in post}), 'post_offers': len(post),
            'fast_forward': (meta.get('fast_forward') or {}).get('stage') if isinstance(meta.get('fast_forward'), dict) else None,
            'processes': list(peak.values()), 'children_rss_peak_mb': round(child_peak, 1) if child_peak is not None else None,
            'children_rss_samples': child_samples, 'children_rss_incomplete_samples': child_incomplete,
            'memory_method': 'sampled sum of live child RSS; shared mappings may be counted multiple times; not PSS',
            'timing_method': 'monotonic polling upper bound, 0.25-second polling interval', 'output': out[:300]}


def run_schedules(installed, arms, per_kind, journal=None):
    from v13 import control_budget as CB
    tasks = selected_tasks(per_kind); out = {}
    for arm in arms:
        with tempfile.TemporaryDirectory(prefix='v13-z7-') as tmp:
            r = fresh_runtime(installed, tmp, {'observer_schedule': arm}); rows = []
            try:
                for fid, text, nums, checks in tasks:
                    r.session = r.store.new_session(); before = device_state(r.home)
                    row = {'fixture': fid, **turn(r, text, nums, checks), 'device_before': before, 'device_after': device_state(r.home)}
                    rows.append(row)
                    if journal: journal.row(arm, row)
                    print(json.dumps({'arm': arm, 'fixture': fid, 'pass': row['pass'], 'answer_s': row['answer_s'], 'wall_s': row['wall_s']}), flush=True)
                    if row.get('budget_exceeded'): raise TimeoutError('Residency turn exceeded its budget; attempt stopped after preserving row')
                fabric = CB.report(r.store, r.home, r.cfg)
            finally:
                r.close()
        out[arm] = {'rows': rows, 'control_budget': fabric, 'summary': summarize(rows)}
        if journal: journal.append('ARM_COMPLETE', {'arm': arm, 'summary': out[arm]['summary'], 'control_budget': fabric})
    return out


def run_repeat(installed, n, journal=None):
    from v13 import control_budget as CB
    fx = [f for f in U2.tasks(seed=29, per_kind=max(n, 1)) if f[0].startswith('summary')][:n]
    with tempfile.TemporaryDirectory(prefix='v13-z7r-') as tmp:
        r = fresh_runtime(installed, tmp, {}); r.session = r.store.new_session(); rows = []
        try:
            for i, (fid, text, nums, checks) in enumerate(fx):
                row = {'index': i, 'fixture': fid, **turn(r, text, nums, checks)}; rows.append(row)
                if journal: journal.row('repeat', row)
                print(json.dumps({'repeat': i, 'pass': row['pass'], 'answer_s': row['answer_s'], 'ff': row['fast_forward']}), flush=True)
                if row.get('budget_exceeded'): raise TimeoutError('Repeat turn exceeded its budget; attempt stopped after preserving row')
            fabric = CB.report(r.store, r.home, r.cfg)
        finally:
            r.close()
    k = max(1, n//4)
    head, tail = rows[:k], rows[-k:]
    def quarter(xs):
        return {'answer_s': mean_known([x['answer_s'] for x in xs]), 'answer_samples': sum(x['answer_s'] is not None for x in xs),
                'n': len(xs), 'passed': sum(x['pass'] for x in xs)}
    return {'rows': rows, 'control_budget': fabric, 'first_quarter': quarter(head), 'last_quarter': quarter(tail)}


def summarize(rows):
    hwm = {}
    for r in rows:
        for p in r['processes']:
            if p['hwm_mb'] is not None: hwm[p['name']] = max(hwm.get(p['name'], 0), p['hwm_mb'])
    temps = [r['device_after']['battery_temp_c'] for r in rows if r['device_after']['battery_temp_c'] is not None]
    mem = [r['device_after']['mem_available_mb'] for r in rows if r['device_after']['mem_available_mb'] is not None]
    child_rss = [r['children_rss_peak_mb'] for r in rows if r.get('children_rss_peak_mb') is not None]
    return {'n': len(rows), 'passed': sum(r['pass'] for r in rows), 'answer_s': mean_known([r['answer_s'] for r in rows]),
            'answer_samples': sum(r['answer_s'] is not None for r in rows), 'answer_missing': sum(r['answer_s'] is None for r in rows),
            'first_offer_s': mean_known([r['first_offer_s'] for r in rows]), 'wall_s': mean_known([r['wall_s'] for r in rows]),
            'hwm_mb_by_process': hwm, 'majflt_max': max([p['majflt'] for r in rows for p in r['processes']], default=None),
            'children_rss_peak_mb': max(child_rss, default=None), 'children_rss_turns_measured': len(child_rss),
            'mem_available_min_mb': min(mem, default=None), 'mem_available_samples': len(mem),
            'battery_temp_max_c': max(temps) if temps else None,
            'battery_drop_percent': (rows[0]['device_before']['battery_percent'] or 0)-(rows[-1]['device_after']['battery_percent'] or 0)
            if rows and rows[0]['device_before']['battery_percent'] is not None and rows[-1]['device_after']['battery_percent'] is not None else None}


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('installed'); ap.add_argument('out')
    ap.add_argument('--mode', choices=('schedules', 'repeat'), default='schedules'); ap.add_argument('--per-kind', type=int, default=3)
    ap.add_argument('--repeat', type=int, default=20); ap.add_argument('--arms', default=','.join(SCHEDULES))
    ap.add_argument('--new-attempt', action='store_true', help='Preserve earlier evidence and explicitly start a separate attempt; never resume partial runtime state')
    a = ap.parse_args(argv)
    if a.per_kind < 1 or a.repeat < 1: ap.error('task counts must be positive')
    installed = Path(a.installed).expanduser().resolve(); t0 = time.time()
    from v13.resources import device
    arms = a.arms.split(',')
    if any(x not in SCHEDULES for x in arms) or len(set(arms)) != len(arms): ap.error('unknown or duplicate schedule')
    binding = input_binding(installed, a.mode, arms, a.per_kind, a.repeat)
    try: journal = ProgressJournal(a.out, binding, a.new_attempt)
    except ValueError as exc: ap.error(str(exc))
    try:
        if a.mode == 'schedules':
            res = {'arms': run_schedules(installed, arms, a.per_kind, journal)}
        else:
            res = run_repeat(installed, a.repeat, journal)
        if input_binding(installed, a.mode, arms, a.per_kind, a.repeat) != binding:
            raise RuntimeError('Residency source/config binding changed during attempt; rows retained, final report refused')
    except BaseException:
        journal.finish('INTERRUPTED')
        raise
    journal.finish('COLLECTION_COMPLETE')
    doc = {'kind': 'V13_Z7_RESIDENCY_BENCH', 'mode': a.mode, 'device': device(), 'seconds': round(time.time()-t0, 1), **res,
           'progress': journal.reference(), 'authority': 0, 'canonical_gate_pass': False,
           'claim_limit': 'measurement only; generated English tasks; decided afterwards against preregistered rules'}
    raw = json.dumps(doc, indent=1, allow_nan=False)
    atomic_write(journal.directory/'report.json', raw)
    atomic_write(Path(a.out), raw)
    journal._state('COMPLETE', journal_sha256=file_hash(journal.path), report_sha256=file_hash(journal.directory/'report.json'))
    print(json.dumps({'mode': a.mode, 'seconds': doc['seconds'], 'attempt_id': journal.attempt_id}), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
