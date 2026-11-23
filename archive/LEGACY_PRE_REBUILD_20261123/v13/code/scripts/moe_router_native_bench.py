#!/usr/bin/env python3
"""WP-N11 part 2: native (llama.cpp, the phone runner) router suite for one or
more MoE bodies, without HF model code (tokenizer only).

Per body and runner file (e.g. F16 and Q4_K_M):
  calib    receiver-native baseline variation on the runner itself: identical
           text tokens after neutral preambles P0/P1/P2 (as moe_router_bench)
  parity   F16 vs quantised routing on identical P0 tokens
  rss      peak RSS of the tap process (VmHWM; mmap pages actually touched)
Optional --pair: run the first runner of every body at the same time and
report the summed peak RSS (both halves resident together on this host).

Evidence level: Linux cloud CPU, not Redmi. Uses scripts/native_moe_router_tap.cpp.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import moe_router_monitor as M  # noqa: E402
from moe_router_bench import OLD_EN, OLD_DE, PREAMBLES  # noqa: E402


def write_ids(tokenizer_dir, path):
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(tokenizer_dir)  # no trust_remote_code: tokenizer files only
    bos = [tok.bos_token_id] if tok.bos_token_id is not None else []
    rows, meta = [], []
    for lang, t in [('en', x) for x in OLD_EN] + [('de', x) for x in OLD_DE]:
        body = tok(t, add_special_tokens=False)['input_ids']
        for p, pre in enumerate(PREAMBLES):
            ids = bos + (tok(pre, add_special_tokens=False)['input_ids'] if pre else []) + body
            rows.append(json.dumps(ids))
            meta.append({'lang': lang, 'preamble': p, 'n_text': len(body)})
    Path(path).write_text('\n'.join(rows) + '\n')
    return meta


TAP_NAMES = {'ffn_norm': 'ffn_moe_logits,ffn_norm,attn_norm', 'layer_input': 'ffn_moe_logits,l_out'}


def run_tap(binary, gguf, ids, out_dir, threads, names=None):
    """Run the tap and sample VmHWM of the child until it exits."""
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    env = dict(os.environ)
    if names is not None:
        env['V13_TAP_NAMES'] = names
    proc = subprocess.Popen([binary, str(gguf), str(ids), str(out_dir), str(threads)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    hwm = [0]

    def sample():
        while proc.poll() is None:
            try:
                for line in Path(f'/proc/{proc.pid}/status').read_text().splitlines():
                    if line.startswith('VmHWM:'):
                        hwm[0] = max(hwm[0], int(line.split()[1]))
            except OSError:
                pass
            time.sleep(0.05)
    th = threading.Thread(target=sample, daemon=True)
    th.start()
    out, err = proc.communicate()
    th.join()
    if proc.returncode != 0:
        raise RuntimeError(f'tap failed {proc.returncode}: {err[-500:]}')
    return {'seconds': round(time.time() - t0, 1), 'vmhwm_mb': round(hwm[0] / 1024, 1), 'stdout': out.strip()}


def calib_and_p0(tap_dir, meta, top_k, router_input):
    """Streamed: baseline variation per text (P0 vs P1/P2), keep only P0 captures
    (float32) for the parity step, then delete the raw tap files."""
    var, p0 = [], {}
    for row, m in enumerate(meta):
        if m['preamble'] != 0:
            continue
        c = [M.load_native_tap(tap_dir, row + j, top_k, router_input=router_input).tail(m['n_text']) for j in range(3)]
        for j in (1, 2):
            var.append(M.compare(c[0], c[j])['aggregate'])
        p0[row] = c[0]
    shutil.rmtree(tap_dir)
    cal = M.calibrate(var, source='native runner: identical text tokens after neutral preambles P0/P1/P2')
    return cal, p0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--body', action='append', required=True,
                    help='name:tokenizer_dir:top_k:router_input:label=gguf[,label=gguf] (first gguf = reference)')
    ap.add_argument('--tap', required=True)
    ap.add_argument('--work', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--pair', action='store_true')
    a = ap.parse_args()
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    res = {'schema': 'v13-moe-router-native-v1', 'evidence_level': 'Linux cloud CPU llama.cpp; not Redmi',
           'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'bodies': {}}
    pair_jobs = []
    for spec in a.body:
        name, tokdir, top_k, rin, files = spec.split(':', 4)
        top_k = int(top_k)
        runners = [tuple(x.split('=', 1)) for x in files.split(',')]
        ids = work / f'{name}.ids.jsonl'
        meta = write_ids(tokdir, ids)
        body = {'top_k': top_k, 'router_input': rin, 'texts': len(meta) // 3, 'runners': {}}
        caps = {}
        for label, gguf in runners:
            d = work / f'{name}-{label}'
            info = run_tap(a.tap, gguf, ids, d, a.threads, TAP_NAMES[rin])
            cal, caps[label] = calib_and_p0(d, meta, top_k, rin)
            body['runners'][label] = {'gguf': gguf, 'run': info, 'calibration': cal}
            print(name, label, info, json.dumps({k: round(v, 4) for k, v in cal['thresholds'].items()}), flush=True)
        ref = runners[0][0]
        for label, _ in runners[1:]:
            per = [M.compare(caps[ref][r], caps[label][r])['aggregate'] for r in caps[ref]]
            keys = [k for k in per[0] if not k.endswith('_mean')]
            summary = {k: {'mean': float(np.mean([p[k] for p in per])), 'p95': float(np.quantile([p[k] for p in per], .95))}
                       for k in keys}
            gate = M.router_stability_gate({k: summary[k]['p95'] for k in keys}, body['runners'][label]['calibration'])
            body[f'parity_{ref}_vs_{label}'] = {'summary': summary, 'within_runner_baseline_p95': gate['verdict'],
                                                 'reasons': gate['reasons']}
            print(name, f'parity {ref}->{label}', json.dumps({k: round(v['mean'], 4) for k, v in summary.items()}),
                  gate['verdict'], flush=True)
        res['bodies'][name] = body
        pair_jobs.append((name, runners[-1][1], ids))
        del caps
    if a.pair and len(pair_jobs) > 1:
        results = {}

        def job(n, g, i):
            results[n] = run_tap(a.tap, g, i, work / f'pair-{n}', max(1, a.threads // len(pair_jobs)), '')
            shutil.rmtree(work / f'pair-{n}', ignore_errors=True)
        ths = [threading.Thread(target=job, args=j) for j in pair_jobs]
        for t in ths:
            t.start()
        for t in ths:
            t.join()
        res['pair'] = {'files': {n: g for n, g, _ in pair_jobs}, 'runs': results,
                       'sum_vmhwm_mb': round(sum(r['vmhwm_mb'] for r in results.values()), 1),
                       'note': 'two plain inference processes at once (no tap, n_ctx 2048, ubatch 128, last-token output), CPU only, mmap; not phone RSS'}
        print('pair', json.dumps(res['pair']), flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1, sort_keys=True))
    print('wrote', a.out)


if __name__ == '__main__':
    main()
