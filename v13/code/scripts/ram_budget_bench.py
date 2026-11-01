#!/usr/bin/env python3
"""RAM budget bench for the V13 model slots (project question: does the stack need >= 8 GB RAM?).

Starts real llama-server processes with the same flags as ``v13/runners.py`` (LlamaRunner) and measures
per process and per scenario, from /proc only (stdlib, runs on Linux and on Termux/Android):

- smaps_rollup: Rss, Pss, Pss_Anon, Pss_File, Anonymous, Private_Dirty, SwapPss (zram on Android)
- VmHWM (peak RSS of the process), system MemAvailable before/after/minimum
- load time, prefill/decode tokens per second of a fixed workload

Anon is the part the kernel cannot drop: Android's LMK kills by it. File pages (mmap'ed GGUF) can be
dropped under pressure and re-read later (costs latency, not RAM). With weight repacking (llama.cpp
default, also on aarch64 with dotprod/i8mm) repacked tensors live in anonymous memory.

Scenarios (``--scenarios``):
  single   each role alone with the runner default flags
  variants per role: --no-repack, --no-mmap (load-mode none), ctx 1024/4096, KV cache q8_0
  combo    C3+B1+B2 resident at once (AG13 body_residency), +embedding, +C3 tap, sequential schedule
  quants   other quantizations of the same weights (from --quant-dir), RAM and speed only

Claim limit: cloud x86 numbers are a lower-bound calibration of what the phone needs (Android adds
ART/zygote/Termux overhead, aarch64 repack layouts differ). The same script on the Redmi is WP-R.
"""
import argparse, json, os, platform, re, signal, socket, subprocess, sys, threading, time, urllib.request
from pathlib import Path

# Canon §73 (Redmi Note 10 Pro, 6 GB): lab targets, not OS guarantees.
CANON_BUDGET_MB = {'weight_hot_max': 2048, 'total_rss_soft_max': 3482, 'total_rss_hard_backoff': 3891}
# v13/runners.py defaults (config.py): context_tokens 2048, threads 4, cache-ram 128, ctx-checkpoints 6
RUNNER_DEFAULTS = {'context_tokens': 2048, 'threads': 4, 'native_cache_ram_mb': 128, 'native_ctx_checkpoints': 6}
ROLE_FILES = {  # role -> (purpose, models.json key)
    'C3_LANGUAGE': ('generate', 'language'), 'B1_DETAIL': ('generate', 'body'), 'B2_GIST': ('generate', 'gist'),
    'EMBED': ('embed', 'embedding'), 'C3_TAP': ('tap', 'language')}
SMAPS_KEYS = ('Rss', 'Pss', 'Pss_Anon', 'Pss_File', 'Pss_Shmem', 'Anonymous', 'Private_Dirty', 'SwapPss', 'Swap')
PARAGRAPH = ("The river town kept a ledger of every boat that passed the lock. Each entry named the captain, "
             "the cargo, the weight in tonnes and the hour the gates opened. In spring the water rose and the "
             "keeper wrote longer notes about the current, the debris and which moorings had failed. ")


def mib(n): return None if n is None else round(n / 2**20, 1)


def smaps(pid):
    out = {}
    try:
        for line in Path(f'/proc/{pid}/smaps_rollup').read_text().splitlines():
            k, _, rest = line.partition(':')
            if k in SMAPS_KEYS: out[k] = int(rest.split()[0]) * 1024
        for line in Path(f'/proc/{pid}/status').read_text().splitlines():
            if line.startswith('VmHWM:'): out['VmHWM'] = int(line.split()[1]) * 1024
        out['majflt'] = int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[9])  # field 12: major faults
    except (FileNotFoundError, ProcessLookupError, PermissionError): return None
    return out


def meminfo():
    d = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        k, _, rest = line.partition(':')
        if k in ('MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree', 'Cached'): d[k] = int(rest.split()[0]) * 1024
    return d


class Sampler(threading.Thread):
    """Polls the given pids; keeps the peak of the scenario sums (Pss, Pss_Anon, Rss) and min MemAvailable."""
    def __init__(self, pids, interval=0.1):
        super().__init__(daemon=True); self.pids = pids; self.interval = interval; self.stop_ev = threading.Event()
        self.peak = {'Pss': 0, 'Pss_Anon': 0, 'Rss': 0}; self.min_avail = None; self.samples = 0
    def run(self):
        while not self.stop_ev.is_set():
            tot = {'Pss': 0, 'Pss_Anon': 0, 'Rss': 0}
            for p in list(self.pids):
                s = smaps(p) or {}
                for k in tot: tot[k] += s.get(k, 0)
            for k in tot: self.peak[k] = max(self.peak[k], tot[k])
            a = meminfo()['MemAvailable']; self.min_avail = a if self.min_avail is None else min(self.min_avail, a)
            self.samples += 1; self.stop_ev.wait(self.interval)
    def stop(self): self.stop_ev.set(); self.join()


class Server:
    """One llama-server with the LlamaRunner command line of v13/runners.py plus variant flags."""
    def __init__(self, binary, model, purpose='generate', role='X', extra=(), cfg=RUNNER_DEFAULTS, log_dir=None):
        self.binary, self.model, self.purpose, self.role, self.extra, self.cfg = binary, Path(model), purpose, role, list(extra), cfg
        self.log_dir = log_dir; self.proc = None; self.port = None; self.load_s = None
    def cmd(self):
        batch = 512 if (self.purpose == 'tap' and self.role.startswith('C3')) or self.purpose == 'embed' else 128
        c = [self.binary, '-m', str(self.model), '--host', '127.0.0.1', '--port', str(self.port),
             '-c', str(512 if self.purpose == 'embed' else self.cfg['context_tokens']), '-np', '1',
             '-t', str(self.cfg['threads']), '-tb', str(self.cfg['threads']), '-b', str(batch), '-ub', str(batch),
             '-ngl', '0', '--no-warmup', '--no-webui', '--log-disable',
             '--cache-ram', str(self.cfg['native_cache_ram_mb']), '--ctx-checkpoints', str(self.cfg['native_ctx_checkpoints'])]
        if self.purpose == 'tap': c += ['--embedding', '--pooling', 'none']
        elif self.purpose == 'embed': c += ['--embedding', '--no-repack']
        # later flags win in llama.cpp's parser, so variants may override defaults (e.g. -c)
        return c + self.extra
    def start(self, timeout=300):
        with socket.socket() as s: s.bind(('127.0.0.1', 0)); self.port = s.getsockname()[1]
        log = open(Path(self.log_dir) / f'{self.role}-{self.port}.log', 'wb') if self.log_dir else subprocess.DEVNULL
        t0 = time.monotonic()
        self.proc = subprocess.Popen(self.cmd(), stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        while time.monotonic() - t0 < timeout:
            if self.proc.poll() is not None: raise RuntimeError(f'{self.role}: llama-server exited {self.proc.returncode}')
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{self.port}/health', timeout=2) as r:
                    if r.status == 200: self.load_s = round(time.monotonic() - t0, 2); return self
            except Exception: pass
            time.sleep(0.1)
        raise TimeoutError(self.role)
    def post(self, path, body, timeout=600):
        req = urllib.request.Request(f'http://127.0.0.1:{self.port}{path}', json.dumps(body).encode(), {'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())
    def work(self, prompt_words, n_predict, turns):
        """Fixed workload: `turns` requests; turn k extends the same conversation (prompt cache), last one is a fresh prefix."""
        stats = []
        for k in range(turns):
            if self.purpose == 'embed':
                r = self.post('/embedding', {'content': ' '.join(PARAGRAPH.split()[:120])}); stats.append({'embed': True}); continue
            if self.purpose == 'tap':
                r = self.post('/embedding', {'content': ' '.join((PARAGRAPH * 8).split()[:prompt_words])}); stats.append({'tap': True}); continue
            fresh = k == turns - 1 and turns > 1
            body = (('Unrelated log. ' if fresh else '') + PARAGRAPH * 40).split()[:prompt_words * (1 if fresh else k + 1)]
            text = ' '.join(body) + '\nQuestion: what did the keeper write in spring?\nAnswer:'
            t0 = time.monotonic()
            r = self.post('/completion', {'prompt': text, 'n_predict': n_predict, 'temperature': 0, 'cache_prompt': True, 'ignore_eos': True})
            t = r.get('timings', {})
            stats.append({'wall_s': round(time.monotonic() - t0, 2), 'prompt_n': t.get('prompt_n'), 'prompt_tps': round(t.get('prompt_per_second') or 0, 1),
                          'predicted_n': t.get('predicted_n'), 'decode_tps': round(t.get('predicted_per_second') or 0, 1)})
        return stats
    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.send_signal(signal.SIGTERM)
            try: self.proc.wait(20)
            except subprocess.TimeoutExpired: self.proc.kill(); self.proc.wait()


def summarize(s):
    return {k: v if k == 'majflt' else mib(v) for k, v in (s or {}).items()}


def run_scenario(name, specs, args, sequential=False):
    """specs: list of (role, model_path, purpose, extra). Resident: all start, then each works, measured together.
    Sequential: C3 stays, each body is loaded, works, unloaded (canon §73 'B1/B2 physical scheduling = sequential first')."""
    log_dir = Path(args.out).parent / 'logs'; log_dir.mkdir(parents=True, exist_ok=True)
    m0 = meminfo(); servers = []; pids = []; sampler = Sampler(pids); sampler.start(); res = {'scenario': name, 'sequential': sequential}
    try:
        per = []
        for i, (role, path, purpose, extra) in enumerate(specs):
            sv = Server(args.binary, path, purpose, role, extra, log_dir=log_dir).start()
            servers.append(sv); pids.append(sv.proc.pid)
            idle = smaps(sv.proc.pid)
            work = sv.work(args.prompt_words, args.n_predict, args.turns)
            after = smaps(sv.proc.pid)
            per.append({'role': role, 'model': Path(path).name, 'file_mib': mib(Path(path).stat().st_size), 'purpose': purpose,
                        'extra': extra, 'load_s': sv.load_s, 'idle': summarize(idle), 'after_work': summarize(after), 'work': work})
            if sequential and i > 0:
                sv.stop(); pids.remove(sv.proc.pid); servers.remove(sv)
        time.sleep(0.3)
        end = {sv.role: summarize(smaps(sv.proc.pid)) for sv in servers}
    finally:
        sampler.stop()
        for sv in servers: sv.stop()
    m1 = meminfo()
    res.update({'processes': per, 'end_state': end,
                'peak_sum_mib': {k: mib(v) for k, v in sampler.peak.items()},
                'mem_available_before_mib': mib(m0['MemAvailable']), 'mem_available_min_mib': mib(sampler.min_avail),
                'mem_available_drop_max_mib': mib(m0['MemAvailable'] - (sampler.min_avail or m0['MemAvailable'])),
                'mem_available_after_mib': mib(m1['MemAvailable']), 'samples': sampler.samples})
    pk = res['peak_sum_mib']
    res['budget'] = {'pss_vs_soft': 'PASS' if pk['Pss'] <= CANON_BUDGET_MB['total_rss_soft_max'] else 'FAIL',
                     'pss_vs_hard': 'PASS' if pk['Pss'] <= CANON_BUDGET_MB['total_rss_hard_backoff'] else 'FAIL',
                     'anon_vs_soft': 'PASS' if pk['Pss_Anon'] <= CANON_BUDGET_MB['total_rss_soft_max'] else 'FAIL'}
    return res


def python_runtime_probe(code_dir):
    """RSS of a Python process that imports the V13 runtime (the controller next to the runners)."""
    src = ("import sys,json;sys.path.insert(0,sys.argv[1]);import numpy;import v13.runtime;"
           "d={l.split(':')[0]:int(l.split()[1]) for l in open('/proc/self/status') if l.startswith(('VmRSS','VmHWM'))};print(json.dumps(d))")
    try:
        out = subprocess.run([sys.executable, '-c', src, str(code_dir)], capture_output=True, text=True, timeout=120)
        d = json.loads(out.stdout.strip().splitlines()[-1]); return {'VmRSS_mib': round(d['VmRSS'] / 1024, 1), 'VmHWM_mib': round(d['VmHWM'] / 1024, 1)}
    except Exception as e: return {'error': repr(e)[:200]}


def environment(binary):
    cpu = ''
    try: cpu = next((l.split(':', 1)[1].strip() for l in open('/proc/cpuinfo') if l.lower().startswith(('model name', 'hardware'))), '')
    except Exception: pass
    flags = ''
    try: flags = next((l for l in open('/proc/cpuinfo') if l.lower().startswith(('flags', 'features'))), '')
    except Exception: pass
    return {'platform': platform.platform(), 'machine': platform.machine(), 'cpu': cpu, 'nproc': os.cpu_count(),
            'cpu_dotprod_or_avx2': bool(re.search(r'\b(asimddp|avx2)\b', flags)), 'cpu_i8mm': 'i8mm' in flags,
            'mem_total_mib': mib(meminfo()['MemTotal']), 'swap_total_mib': mib(meminfo()['SwapTotal']), 'binary': binary,
            'android': os.path.exists('/system/build.prop'), 'python': sys.version.split()[0]}


def model_paths(models_dir):
    spec = json.loads((Path(__file__).resolve().parents[1] / 'specs/models.json').read_text())['models']
    return {role: Path(models_dir) / spec[key]['main_file'] for role, (_, key) in ROLE_FILES.items()}


def plan(args, paths):
    P = lambda r: (r, str(paths[r]), ROLE_FILES[r][0], [])
    sc = []
    if 'single' in args.scenarios:
        for r in ('C3_LANGUAGE', 'B1_DETAIL', 'B2_GIST', 'EMBED', 'C3_TAP'): sc.append((f'single:{r}', [P(r)], False))
    if 'variants' in args.scenarios:
        for r in ('C3_LANGUAGE', 'B1_DETAIL', 'B2_GIST'):
            for vname, extra in (('no-repack', ['--no-repack']), ('no-mmap', ['--load-mode', 'none']),
                                 ('no-repack+no-mmap', ['--no-repack', '--load-mode', 'none']),
                                 ('ctx1024', ['-c', '1024']), ('ctx4096', ['-c', '4096']),
                                 ('kv-q8', ['-fa', 'on', '-ctk', 'q8_0', '-ctv', 'q8_0']),
                                 ('cache-ram-default', ['--cache-ram', '8192', '--ctx-checkpoints', '32'])):
                sc.append((f'variant:{r}:{vname}', [(r, str(paths[r]), 'generate', extra)], False))
    if 'combo' in args.scenarios:
        three = [P('C3_LANGUAGE'), P('B1_DETAIL'), P('B2_GIST')]
        nr = lambda s: [(r, p, pu, e + ['--no-repack']) for r, p, pu, e in s]
        sc += [('combo:C3+B1+B2 resident', three, False),
               ('combo:C3+B1+B2 resident no-repack', nr(three), False),
               ('combo:C3+B1+B2+EMBED resident', three + [P('EMBED')], False),
               ('combo:C3+B1+B2+EMBED+C3_TAP resident', three + [P('EMBED'), P('C3_TAP')], False),
               ('combo:C3 + B1/B2 sequential', three, True),
               ('combo:C3 + B1/B2 sequential no-repack', nr(three), True)]
    if 'quants' in args.scenarios and args.quant_dir:
        role_of = lambda n: 'B1_DETAIL' if n.startswith('LFM2.5-1.2B') else 'B2_GIST' if n.startswith('Qwen3.5-0.8B') else 'C3_LANGUAGE'
        for f in sorted(Path(args.quant_dir).glob('*.gguf')):
            for vname, extra in (('default', []), ('no-repack', ['--no-repack'])):
                sc.append((f'quant:{role_of(f.name)}:{f.name}:{vname}', [(role_of(f.name), str(f), 'generate', extra)], False))
    return sc


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--binary', required=True); ap.add_argument('--models-dir', required=True); ap.add_argument('--quant-dir')
    ap.add_argument('--out', required=True); ap.add_argument('--scenarios', default='single,variants,combo,quants')
    ap.add_argument('--only', default='', help='substring filter on scenario names')
    ap.add_argument('--prompt-words', type=int, default=400); ap.add_argument('--n-predict', type=int, default=64)
    ap.add_argument('--turns', type=int, default=3)
    args = ap.parse_args(); args.scenarios = set(args.scenarios.split(','))
    paths = model_paths(args.models_dir)
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    report = json.loads(out.read_text()) if out.exists() else {'results': []}
    report.update({'schema': 'v13.ram_budget_bench/1', 'canon_budget_mib': CANON_BUDGET_MB, 'runner_defaults': RUNNER_DEFAULTS,
                   'environment': environment(args.binary), 'python_runtime': python_runtime_probe(Path(__file__).resolve().parents[1]),
                   'workload': {'prompt_words': args.prompt_words, 'n_predict': args.n_predict, 'turns': args.turns}})
    done = {r['scenario'] for r in report['results'] if 'error' not in r}
    for name, specs, seq in plan(args, paths):
        if args.only and args.only not in name or name in done: continue
        if any(not Path(p).is_file() for _, p, _, _ in specs): continue
        try: r = run_scenario(name, specs, args, seq)
        except Exception as e: r = {'scenario': name, 'error': repr(e)[:300]}
        report['results'] = [x for x in report['results'] if x['scenario'] != name] + [r]
        out.write_text(json.dumps(report, indent=1))  # resumable: a killed run keeps finished scenarios
        pk = r.get('peak_sum_mib', {})
        print(f"{name:60s} PSS {pk.get('Pss')} anon {pk.get('Pss_Anon')} MiB {r.get('error', '')}", flush=True)


if __name__ == '__main__': main()
