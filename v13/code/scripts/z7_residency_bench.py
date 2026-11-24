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
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.common import atomic_write  # noqa: E402
import utility_bench as U  # noqa: E402
import utility_bench2 as U2  # noqa: E402

SCHEDULES = ('A_THEN_B_SEQUENTIAL', 'B_THEN_A_SEQUENTIAL', 'ALWAYS_BOTH_ASYNC', 'JEF_FIRST_THEN_BOTH', 'SAMPLED_OBSERVER')
FINAL = ('FINAL', 'CANCELLED', 'DEADLINE', 'ERROR', 'INTERRUPTED')


def proc_children(root=None):
    """PIDs of all descendants of this process (llama-server, needle worker)."""
    root = root or os.getpid(); parents = {}
    for d in Path('/proc').iterdir():
        if d.name.isdigit():
            try:
                ppid = int((d/'stat').read_text().rsplit(')', 1)[1].split()[1]); parents.setdefault(ppid, []).append(int(d.name))
            except (OSError, ValueError, IndexError):
                continue
    out, todo = [], [root]
    while todo:
        p = todo.pop()
        for c in parents.get(p, []): out.append(c); todo.append(c)
    return out


def proc_stats(pid):
    try:
        status = dict(l.split(':', 1) for l in Path('/proc/%d/status' % pid).read_text().splitlines() if ':' in l)
        stat = Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()
        cmd = Path('/proc/%d/cmdline' % pid).read_bytes().split(b'\0')[0].decode(errors='replace')
        kb = lambda k: int(status[k].split()[0]) if k in status else None
        return {'pid': pid, 'name': Path(cmd).name, 'rss_mb': round((kb('VmRSS') or 0)/1024, 1), 'hwm_mb': round((kb('VmHWM') or 0)/1024, 1),
                'majflt': int(stat[9]), 'minflt': int(stat[7])}
    except (OSError, ValueError, IndexError):
        return None


def device_state(home):
    from v13.resources import snapshot
    s = snapshot(home)
    return {'mem_available_mb': round((s['mem_available_bytes'] or 0)/2**20), 'battery_temp_c': s['battery_temperature_c'],
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
    t0 = time.monotonic(); eid = r.submit(text); answer_s = first_offer_s = None; peak = {}
    while not r.idle():
        now = time.monotonic()-t0
        if first_offer_s is None and r.store.one("SELECT 1 FROM packets WHERE event_id=? AND kind='OfferPacket' LIMIT 1", (eid,)):
            first_offer_s = round(now, 2)
        if answer_s is None:
            m = r.store.one("SELECT status FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1", (eid,))
            if m and m['status'] in FINAL: answer_s = round(now, 2)
        for p in proc_children():
            st = proc_stats(p)
            if st and st['rss_mb'] >= peak.get(st['name'], {}).get('rss_mb', -1): peak[st['name']] = st
        if now > budget:
            r.cancel(); break
        time.sleep(.25)
    a = audit_event(r.store, eid); out = a.get('output') or ''
    ok, num = U.score(out, nums, checks)
    post = {json.loads(x['metrics']).get('id') for x in r.store.rows("SELECT metrics FROM telemetry WHERE kind='postcommit_offer' AND event_id=?", (eid,))}
    meta = a.get('output_metadata') or {}
    return {'pass': all(ok.values()) and all(num.values()), 'answer_s': answer_s, 'first_offer_s': first_offer_s,
            'wall_s': round(time.monotonic()-t0, 2), 'status': a.get('status'),
            'pre_offers': sorted({o['role'] for o in a.get('offers', []) if o.get('packet_id') not in post}), 'post_offers': len(post),
            'fast_forward': (meta.get('fast_forward') or {}).get('stage') if isinstance(meta.get('fast_forward'), dict) else None,
            'processes': list(peak.values()), 'output': out[:300]}


def run_schedules(installed, arms, per_kind):
    from v13 import control_budget as CB
    fx = U2.tasks(seed=23); kinds = {}
    for f in fx: kinds.setdefault(f[0].rstrip('0123456789'), []).append(f)
    tasks = [f for k in sorted(kinds) for f in kinds[k][:per_kind]]; out = {}
    for arm in arms:
        with tempfile.TemporaryDirectory(prefix='v13-z7-') as tmp:
            r = fresh_runtime(installed, tmp, {'observer_schedule': arm}); rows = []
            try:
                for fid, text, nums, checks in tasks:
                    r.session = r.store.new_session(); before = device_state(r.home)
                    row = {'fixture': fid, **turn(r, text, nums, checks), 'device_before': before, 'device_after': device_state(r.home)}
                    rows.append(row); print(json.dumps({'arm': arm, 'fixture': fid, 'pass': row['pass'], 'answer_s': row['answer_s'], 'wall_s': row['wall_s']}), flush=True)
                fabric = CB.report(r.store, r.home, r.cfg)
            finally:
                r.close()
        out[arm] = {'rows': rows, 'control_budget': fabric, 'summary': summarize(rows)}
    return out


def run_repeat(installed, n):
    from v13 import control_budget as CB
    fx = [f for f in U2.tasks(seed=29, per_kind=max(n, 1)) if f[0].startswith('summary')][:n]
    with tempfile.TemporaryDirectory(prefix='v13-z7r-') as tmp:
        r = fresh_runtime(installed, tmp, {}); r.session = r.store.new_session(); rows = []
        try:
            for i, (fid, text, nums, checks) in enumerate(fx):
                row = {'index': i, 'fixture': fid, **turn(r, text, nums, checks)}; rows.append(row)
                print(json.dumps({'repeat': i, 'pass': row['pass'], 'answer_s': row['answer_s'], 'ff': row['fast_forward']}), flush=True)
            fabric = CB.report(r.store, r.home, r.cfg)
        finally:
            r.close()
    k = max(1, n//4)
    head, tail = rows[:k], rows[-k:]
    mean = lambda xs: round(sum(xs)/len(xs), 2) if xs else None
    return {'rows': rows, 'control_budget': fabric, 'first_quarter': {'answer_s': mean([x['answer_s'] or 0 for x in head]), 'passed': sum(x['pass'] for x in head)},
            'last_quarter': {'answer_s': mean([x['answer_s'] or 0 for x in tail]), 'passed': sum(x['pass'] for x in tail)}}


def summarize(rows):
    mean = lambda xs: round(sum(xs)/len(xs), 2) if xs else None
    hwm = {}
    for r in rows:
        for p in r['processes']: hwm[p['name']] = max(hwm.get(p['name'], 0), p['hwm_mb'])
    temps = [r['device_after']['battery_temp_c'] for r in rows if r['device_after']['battery_temp_c'] is not None]
    return {'n': len(rows), 'passed': sum(r['pass'] for r in rows), 'answer_s': mean([r['answer_s'] or 0 for r in rows]),
            'first_offer_s': mean([r['first_offer_s'] for r in rows if r['first_offer_s'] is not None]), 'wall_s': mean([r['wall_s'] for r in rows]),
            'hwm_mb_by_process': hwm, 'majflt_max': max([p['majflt'] for r in rows for p in r['processes']], default=None),
            'mem_available_min_mb': min([r['device_after']['mem_available_mb'] for r in rows], default=None),
            'battery_temp_max_c': max(temps) if temps else None,
            'battery_drop_percent': (rows[0]['device_before']['battery_percent'] or 0)-(rows[-1]['device_after']['battery_percent'] or 0)
            if rows and rows[0]['device_before']['battery_percent'] is not None and rows[-1]['device_after']['battery_percent'] is not None else None}


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('installed'); ap.add_argument('out')
    ap.add_argument('--mode', choices=('schedules', 'repeat'), default='schedules'); ap.add_argument('--per-kind', type=int, default=3)
    ap.add_argument('--repeat', type=int, default=20); ap.add_argument('--arms', default=','.join(SCHEDULES)); a = ap.parse_args(argv)
    installed = Path(a.installed).expanduser().resolve(); t0 = time.time()
    from v13.resources import device
    if a.mode == 'schedules':
        arms = a.arms.split(',')
        if any(x not in SCHEDULES for x in arms): ap.error('unknown schedule')
        res = {'arms': run_schedules(installed, arms, a.per_kind)}
    else:
        res = run_repeat(installed, a.repeat)
    doc = {'kind': 'V13_Z7_RESIDENCY_BENCH', 'mode': a.mode, 'device': device(), 'seconds': round(time.time()-t0, 1), **res,
           'authority': 0, 'claim_limit': 'measurement only; generated English tasks; decided afterwards against preregistered rules'}
    atomic_write(Path(a.out), json.dumps(doc, indent=1)); print(json.dumps({'mode': a.mode, 'seconds': doc['seconds']}), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
