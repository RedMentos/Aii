#!/usr/bin/env python3
"""Quality proxy for quantization variants: llama-perplexity on the first N chunks of wikitext-2 test.

Only a relative proxy (same weights, different quantization; Q8_0 is the near-lossless reference). It does
not measure V13 task quality (STEP2/C3 benches do that) and English text only.
"""
import argparse, json, re, subprocess, time
from pathlib import Path


def ppl(binary, model, text, chunks, ctx, threads):
    t0 = time.monotonic()
    p = subprocess.run([binary, '-m', str(model), '-f', str(text), '-c', str(ctx), '--chunks', str(chunks), '-t', str(threads),
                        '-b', str(ctx), '--no-warmup'], capture_output=True, text=True, timeout=3600)
    m = re.search(r'Final estimate: PPL = ([0-9.]+) \+/- ([0-9.]+)', p.stdout + p.stderr)
    return {'model': Path(model).name, 'file_mib': round(Path(model).stat().st_size / 2**20, 1),
            'ppl': float(m.group(1)) if m else None, 'ppl_err': float(m.group(2)) if m else None,
            'wall_s': round(time.monotonic() - t0, 1), 'error': None if m else (p.stderr or p.stdout)[-300:]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--binary', required=True); ap.add_argument('--text', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--chunks', type=int, default=40); ap.add_argument('--ctx', type=int, default=512); ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('models', nargs='+')
    a = ap.parse_args()
    rows = [ppl(a.binary, m, a.text, a.chunks, a.ctx, a.threads) for m in a.models]
    for r in rows: print(f"{r['model']:45s} {r['file_mib']:8} MiB  PPL {r['ppl']} ± {r['ppl_err']}", flush=True)
    Path(a.out).write_text(json.dumps({'schema': 'v13.quant_ppl_probe/1', 'chunks': a.chunks, 'ctx': a.ctx, 'rows': rows}, indent=1))


if __name__ == '__main__': main()
