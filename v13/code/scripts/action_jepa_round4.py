#!/usr/bin/env python3
"""Action-JEPA round 4: same rows and partitions as round 3, other native taps.

Round 3 used llama-server mean-pooled final embeddings. Here the read-only
native tool scripts/native_layer_taps.cpp copies the residual stream l_out-L
per text (last token and token mean) for preregistered layers. Each tap arm
gets its own dataset: the round-3 dataset rows unchanged, only the bound
native array is replaced. No runtime code, weights or authority change.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from action_jepa_objective import load_dataset
from export_action_jepa_dataset import sha


def capture(args):
    with np.load(args.round3_taps, allow_pickle=False) as z:
        texts = z['texts'].tolist()
    if any('\n' in t or '\r' in t for t in texts):
        raise ValueError('Line-based tap tool needs single-line texts')
    layers = [int(v) for v in args.layers.split(',')]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'inputs.txt').write_text('\n'.join(texts) + '\n')
    env = {k: v for k, v in os.environ.items() if k not in ('LD_PRELOAD',)}
    env.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS=str(args.threads))
    started = datetime.now(timezone.utc).isoformat()
    proc = subprocess.run([str(Path(args.tool).resolve()), str(Path(args.model).resolve()), args.layers,
                           str(out / 'inputs.txt'), str(out / 'taps'), str(args.threads)],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    (out / 'tool.log').write_bytes(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError('native tap tool failed with %d' % proc.returncode)
    meta = json.loads((out / 'taps.json').read_text())
    d = meta['n_embd']
    raw = np.fromfile(out / 'taps.bin', dtype=np.float32)
    if meta['texts'] != len(texts) or raw.size != len(texts) * len(layers) * 2 * d or not np.isfinite(raw).all():
        raise ValueError('Tap file shape/finiteness mismatch')
    raw = raw.reshape(len(texts), len(layers), 2, d)
    arms = {}
    for i, layer in enumerate(layers):
        for k, kind in enumerate(('last', 'mean')):
            name = f'l{layer}_{kind}'
            path = out / f'taps-{name}.npz'
            np.savez(path, x=raw[:, i, k, :].astype(np.float64), texts=np.asarray(texts))
            arms[name] = {'path': path.name, 'sha256': sha(path)}
    report = {'schema': 'v13-action-jepa-round4-capture-v1', 'started_utc': started,
              'finished_utc': datetime.now(timezone.utc).isoformat(), 'rows': len(texts), 'layers': layers,
              'n_layer': meta['n_layer'], 'tool_sha256': sha(args.tool), 'model_sha256': sha(args.model),
              'libraries': {p.name: sha(p) for p in sorted(Path(args.tool).resolve().parent.glob('*.so*')) if p.is_file()},
              'raw_bin_sha256': sha(out / 'taps.bin'), 'meta_sha256': sha(out / 'taps.json'),
              'texts_sha256': hashlib.sha256(json.dumps(texts, ensure_ascii=False).encode()).hexdigest(),
              'arms': arms, 'tool_exit': proc.returncode}
    (out / 'capture-report.json').write_text(json.dumps(report, indent=1) + '\n')
    return report


def export(args):
    """Copy the round-3 export and replace only the native tap binding."""
    src, out = Path(args.round3_export), Path(args.out)
    if out.exists() and any(out.iterdir()):
        raise ValueError('Export destination must be empty')
    doc = json.loads((src / 'dataset.json').read_text())
    taps = Path(args.taps)
    with np.load(taps, allow_pickle=False) as z, np.load(src / 'native-taps.npz', allow_pickle=False) as old:
        if z['texts'].tolist() != old['texts'].tolist() or z['x'].shape != old['x'].shape:
            raise ValueError('Tap arm texts/shape differ from round-3 capture')
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src / 'sources', out / 'sources')
    shutil.copyfile(taps, out / 'native-taps.npz')
    encoder = {'schema': 'v13-action-jepa-round4-encoder-v1', 'tap_kind': 'llama.cpp-l_out-residual',
               'tap_arm': args.arm, 'capture_report': json.loads(Path(args.capture_report).read_text()),
               'round3_dataset_sha256': sha(src / 'dataset.json'), 'taps_sha256': sha(taps)}
    (out / 'encoder-binding.json').write_text(json.dumps(encoder, indent=1) + '\n')
    doc['bindings']['encoder'] = {'path': 'encoder-binding.json', 'sha256': sha(out / 'encoder-binding.json')}
    doc['bindings']['native_taps'] = {'path': 'native-taps.npz', 'sha256': sha(out / 'native-taps.npz')}
    doc['export_plan'] = dict(doc['export_plan'], round4_tap_arm=args.arm)
    (out / 'dataset.json').write_text(json.dumps(doc, ensure_ascii=False, allow_nan=False) + '\n')
    load_dataset(out / 'dataset.json')
    return {'arm': args.arm, 'dataset_sha256': sha(out / 'dataset.json'), 'pairs': len(doc['rows']),
            'taps_sha256': sha(taps), 'receiver_authority': 0}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    c = sub.add_parser('capture')
    for name in ('--tool', '--model', '--round3-taps', '--layers', '--out'):
        c.add_argument(name, required=True)
    c.add_argument('--threads', type=int, default=4)
    e = sub.add_parser('export')
    for name in ('--round3-export', '--taps', '--capture-report', '--arm', '--out'):
        e.add_argument(name, required=True)
    args = ap.parse_args()
    print(json.dumps((capture if args.command == 'capture' else export)(args)))


if __name__ == '__main__':
    main()
