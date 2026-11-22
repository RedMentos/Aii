#!/usr/bin/env python3
"""Smallest RAM that still runs the V13 model stack: ram_budget_bench scenarios under a hard memory cgroup.

Cloud only (needs a writable cgroup-v1 memory controller; Termux cannot do this). For each scenario and
limit the GGUF page cache is evicted (posix_fadvise DONTNEED) so the weights are charged to the test
cgroup, then ``ram_budget_bench.py --only <scenario>`` runs inside it. A memory cgroup charges anonymous
memory and page cache together and has no swap here, so the limit plays the role of the RAM that
Android leaves to V13 (canon §73: soft 3.0-3.4 GB, hard backoff 3.8 GB on the 6 GB Redmi).

Per limit: completed or not, OOM kills, peak usage, major faults (weights re-read from disk = thrash)
and decode/prefill speed against the unlimited run. ``--limits`` in MiB.
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def own_memcg():
    for line in Path('/proc/self/cgroup').read_text().splitlines():
        _, ctrl, path = line.split(':', 2)
        if 'memory' in ctrl.split(','): return Path('/sys/fs/cgroup/memory') / path.lstrip('/')
    raise RuntimeError('no cgroup-v1 memory controller')


def evict(paths):
    for p in paths:
        fd = os.open(p, os.O_RDONLY)
        try: os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        finally: os.close(fd)


def cg_read(cg, name):
    try: return (cg / name).read_text()
    except OSError: return ''


def run(args, scenario, limit_mib, models):
    cg = own_memcg() / f'v13-squeeze-{os.getpid()}'
    cg.mkdir(exist_ok=True)
    try:
        if limit_mib: (cg / 'memory.limit_in_bytes').write_text(str(limit_mib * 2**20))
        try: (cg / 'memory.memsw.limit_in_bytes').write_text(str(limit_mib * 2**20) if limit_mib else '-1')
        except OSError: pass
        evict(models)
        slug = ''.join(c if c.isalnum() else '_' for c in scenario)
        out = Path(args.out_dir) / f'{slug}-{limit_mib}.json'
        if out.exists(): out.unlink()
        cmd = [sys.executable, str(HERE / 'ram_budget_bench.py'), '--binary', args.binary, '--models-dir', args.models_dir,
               '--out', str(out), '--scenarios', 'single,variants,combo', '--only', scenario, '--turns', str(args.turns)]
        procs = cg / 'cgroup.procs'
        t0 = time.monotonic()
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout,
                           preexec_fn=lambda: procs.write_text(str(os.getpid())))
        wall = round(time.monotonic() - t0, 1)
        rep = json.loads(out.read_text()) if out.exists() else {'results': []}
        res = next((r for r in rep['results'] if r['scenario'] == scenario), {'error': (p.stderr or p.stdout)[-300:]})
        oom = dict(l.split() for l in cg_read(cg, 'memory.oom_control').splitlines() if l.strip())
        row = {'scenario': scenario, 'limit_mib': limit_mib, 'wall_s': wall, 'error': res.get('error'),
               'cg_max_usage_mib': round(int(cg_read(cg, 'memory.max_usage_in_bytes') or 0) / 2**20, 1),
               'cg_failcnt': int(cg_read(cg, 'memory.failcnt') or 0), 'oom_kill': int(oom.get('oom_kill', 0)),
               'peak_sum_mib': res.get('peak_sum_mib'), 'processes': []}
        for pr in res.get('processes', []):
            w = [x for x in pr['work'] if 'decode_tps' in x]
            row['processes'].append({'role': pr['role'], 'load_s': pr['load_s'], 'majflt': (pr['after_work'] or {}).get('majflt'),
                                     'decode_tps': [x['decode_tps'] for x in w], 'prompt_tps': [x['prompt_tps'] for x in w],
                                     'wall_s': [x.get('wall_s') for x in w]})
        return row
    finally:
        for pid in cg_read(cg, 'cgroup.procs').split():
            try: os.kill(int(pid), 9)
            except OSError: pass
        time.sleep(0.5)
        try: cg.rmdir()
        except OSError: pass


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--binary', required=True); ap.add_argument('--models-dir', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--scenarios', default='combo:C3+B1+B2 resident;combo:C3+B1+B2 resident no-repack;combo:C3 + B1/B2 sequential;combo:C3 + B1/B2 sequential no-repack')
    ap.add_argument('--limits', default='0,3500,2500,2000,1750,1500,1250,1000,750')
    ap.add_argument('--turns', type=int, default=3); ap.add_argument('--timeout', type=int, default=900)
    args = ap.parse_args()
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); args.out_dir = str(out.parent / 'squeeze-runs')
    Path(args.out_dir).mkdir(exist_ok=True)
    report = json.loads(out.read_text()) if out.exists() else {'schema': 'v13.ram_squeeze_bench/1', 'rows': []}
    sys.path.insert(0, str(HERE)); import ram_budget_bench as rb
    models = [str(p) for p in rb.model_paths(args.models_dir).values() if p.is_file()]
    done = {(r['scenario'], r['limit_mib']) for r in report['rows']}
    for sc in args.scenarios.split(';'):
        for lim in [int(x) for x in args.limits.split(',')]:
            if (sc, lim) in done: continue
            try: row = run(args, sc, lim, models)
            except subprocess.TimeoutExpired: row = {'scenario': sc, 'limit_mib': lim, 'error': 'TIMEOUT (thrash)'}
            report['rows'].append(row); out.write_text(json.dumps(report, indent=1))
            dec = [p['decode_tps'] for p in row.get('processes', [])]
            print(f"{sc:42s} {lim:5d} MiB  err={str(row.get('error'))[:40]:40s} oom={row.get('oom_kill')} max={row.get('cg_max_usage_mib')} "
                  f"majflt={[p['majflt'] for p in row.get('processes', [])]} dec={dec}", flush=True)
            if row.get('error') and lim:  # smaller limits will fail too
                break


if __name__ == '__main__': main()
