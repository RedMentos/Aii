#!/usr/bin/env python3
"""WP-N11 runner parity: router captures of the HF reference body vs the
llama.cpp phone runner (scripts/native_moe_router_tap.cpp) on identical token ids.

  prepare  write ids.jsonl (same tokenisation as moe_router_bench.Body.ids)
  compare  HF fp32 captures vs one or more native tap directories (e.g. F16, Q4_K_M)

Measures how much routing changes from runner/quantisation alone and puts it
next to the receiver-native calibration from moe_router_bench (B3-H6): if
quantisation alone exceeds the thresholds, they must be re-derived on the
actual phone runner. Evidence level: Linux cloud, not Redmi.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import moe_router_monitor as M  # noqa: E402
import moe_router_bench as B  # noqa: E402


def texts():
    return [('en', t) for t in B.OLD_EN] + [('de', t) for t in B.OLD_DE]


def prepare(model, out):
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model)
    bos = [tok.bos_token_id] if tok.bos_token_id is not None else []
    lines = [json.dumps(bos + tok(t, add_special_tokens=False)['input_ids']) for _, t in texts()]
    Path(out).write_text('\n'.join(lines) + '\n')
    print('wrote', out, len(lines))


def compare(model, ids_path, natives, calib_json, out, threads):
    body = B.Body(model, threads)
    ids_rows = [json.loads(l) for l in Path(ids_path).read_text().splitlines() if l.strip()]
    cal = json.loads(Path(calib_json).read_text())['calib']['primary']
    res = {'schema': 'v13-moe-router-parity-v1', 'calibration_thresholds': cal['thresholds'], 'runners': {}}
    hf = [body.run(ids)[0] for ids in ids_rows]
    for label, d in natives:
        per = []
        for row, ids in enumerate(ids_rows):
            nat = M.load_native_tap(d, row, body.top_k)
            n = len(ids) - 1  # skip BOS position
            # HF residual is the raw stream, the native tap sees the normed attn_norm: compare routing only.
            a = M.Capture({i: M.LayerCapture(l.logits, l.router_input) for i, l in hf[row].tail(n).layers.items()}, body.top_k)
            b = M.Capture({i: M.LayerCapture(l.logits, l.router_input) for i, l in nat.tail(n).layers.items()}, body.top_k)
            agg = M.compare(a, b)['aggregate']
            per.append(agg)
        keys = [k for k in per[0] if not k.endswith('_mean')]
        summary = {k: {'mean': float(np.mean([p[k] for p in per])), 'p95': float(np.quantile([p[k] for p in per], .95))}
                   for k in keys}
        gate = M.router_stability_gate(dict({k: summary[k]['p95'] for k in keys}, residual_norm_shift=0.0), cal)
        gate['note'] = 'residual_norm_shift not comparable across runners (set 0 for this check)'
        res['runners'][label] = {'dir': str(d), 'summary': summary,
                                 'within_receiver_baseline_p95': gate['verdict'], 'reasons': gate['reasons']}
        print(label, json.dumps({k: round(v['mean'], 4) for k, v in summary.items()}), gate['verdict'], flush=True)
    Path(out).write_text(json.dumps(res, indent=1, sort_keys=True))
    print('wrote', out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--model', required=True)
    p.add_argument('--out', required=True)
    c = sub.add_parser('compare')
    c.add_argument('--model', required=True)
    c.add_argument('--ids', required=True)
    c.add_argument('--native', action='append', required=True, help='label=dir')
    c.add_argument('--calib', required=True, help='moe_router_bench result json')
    c.add_argument('--out', required=True)
    c.add_argument('--threads', type=int, default=4)
    a = ap.parse_args()
    if a.cmd == 'prepare':
        prepare(a.model, a.out)
    else:
        compare(a.model, a.ids, [tuple(x.split('=', 1)) for x in a.native], a.calib, a.out, a.threads)


if __name__ == '__main__':
    main()
