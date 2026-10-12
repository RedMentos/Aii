#!/usr/bin/env python3
"""Action-JEPA round 5: real tool actions instead of model-written text rewrites.

World: a counter whose state is the text "The counter shows N.". Each action is a
real `calc` call through the V13 ToolRegistry (IH-H29 policy, IH-H14 action
transaction) in a throwaway sandbox store; the observed outcome text is built
from the tool's returned result, never from a model. Every transaction record
is bound as a source of its row. B2 taps come from scripts/native_layer_taps.cpp.
Partitions are disjoint sets of start values; episodes whose normalized text
crosses partitions are dropped before any tap is read. Read-only use of runtime
modules; nothing in code/v13 is changed and no authority is granted.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from action_jepa_objective import SCHEMA, load_dataset
from export_action_jepa_dataset import sha, source_identity, text_sha

ACTIONS = {'double': '{n}*2', 'add_15': '{n}+15', 'quarter': '{n}/4', 'subtract_7': '{n}-7'}
TEMPLATE = 'The counter shows {n}.'
PARTS = (('train', .5), ('calibration', .15), ('retention', .15), ('test', .2))


def now():
    return datetime.now(timezone.utc).isoformat()


def world(args):
    """Draw start values, run every action as a real calc tool call, keep the transaction records."""
    from v13.store import Store
    from v13.agi.tools import ToolRegistry
    rng = np.random.default_rng(args.seed)
    values = sorted(rng.choice(np.arange(1, 1000), size=args.states, replace=False).tolist())
    order = rng.permutation(values).tolist()
    cuts, start, part_of = [], 0, {}
    for name, share in PARTS:
        n = int(round(share * len(order))) if name != 'test' else len(order) - start
        for v in order[start:start + n]:
            part_of[v] = name
        start += n
    out = Path(args.out)
    (out / 'tx').mkdir(parents=True, exist_ok=True)
    home = out / 'sandbox-store'
    (home / 'data/db').mkdir(parents=True)
    (home / 'data/blobs').mkdir(parents=True)
    store = Store(home)
    try:
        tools = ToolRegistry(store)
        tools.enable('calc')
        episodes = []
        for v in values:
            row = {'value': v, 'partition': part_of[v], 'input': TEMPLATE.format(n=v), 'outcomes': {}, 'tx': {}}
            for action, expr in ACTIONS.items():
                tx = tools.call('calc', {'expression': expr.format(n=v)}, origin='USER', intent='round5:' + action)
                if tx['status'] != 'EXECUTED' or tx['error']:
                    raise RuntimeError('Tool call did not execute: %s' % tx['status'])
                record = {k: tx[k] for k in ('id', 'tool', 'risk', 'origin', 'args', 'intent', 'status', 'reason',
                                             'result', 'error', 'action_tx', 'created')}
                path = out / 'tx' / (tx['id'] + '.json')
                path.write_text(json.dumps(record, sort_keys=True) + '\n')
                row['outcomes'][action] = TEMPLATE.format(n=tx['result'])
                row['tx'][action] = {'path': 'tx/' + path.name, 'sha256': sha(path)}
            episodes.append(row)
    finally:
        store.close()
    doc = {'schema': 'v13-action-jepa-round5-world-v1', 'utc': now(), 'seed': args.seed, 'states': len(values),
           'template': TEMPLATE, 'actions': ACTIONS, 'tool': 'calc via v13.agi.tools.ToolRegistry (sandbox store)',
           'episodes': episodes}
    (out / 'world.json').write_text(json.dumps(doc, indent=1) + '\n')
    texts = [e['input'] for e in episodes] + [e['outcomes'][a] for a in ACTIONS for e in episodes]
    (out / 'texts.json').write_text(json.dumps(texts) + '\n')
    return {'states': len(values), 'texts': len(texts), 'world_sha256': sha(out / 'world.json'),
            'partitions': {p: sum(e['partition'] == p for e in episodes) for p, _ in PARTS}}


def capture(args):
    texts = json.loads(Path(args.texts).read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'inputs.txt').write_text('\n'.join(texts) + '\n')
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS=str(args.threads))
    proc = subprocess.run([str(Path(args.tool).resolve()), str(Path(args.model).resolve()), args.layers,
                           str(out / 'inputs.txt'), str(out / 'taps'), str(args.threads)],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    (out / 'tool.log').write_bytes(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError('native tap tool failed with %d' % proc.returncode)
    layers = [int(v) for v in args.layers.split(',')]
    meta = json.loads((out / 'taps.json').read_text())
    raw = np.fromfile(out / 'taps.bin', dtype=np.float32)
    if meta['texts'] != len(texts) or raw.size != len(texts) * len(layers) * 2 * meta['n_embd'] or not np.isfinite(raw).all():
        raise ValueError('Tap file shape/finiteness mismatch')
    raw = raw.reshape(len(texts), len(layers), 2, meta['n_embd'])
    arms = {}
    for i, layer in enumerate(layers):
        for k, kind in enumerate(('last', 'mean')):
            path = out / f'taps-l{layer}_{kind}.npz'
            np.savez(path, x=raw[:, i, k, :].astype(np.float64), texts=np.asarray(texts))
            arms[f'l{layer}_{kind}'] = {'path': path.name, 'sha256': sha(path)}
    report = {'schema': 'v13-action-jepa-round5-capture-v1', 'utc': now(), 'rows': len(texts), 'layers': layers,
              'tool_sha256': sha(args.tool), 'model_sha256': sha(args.model), 'raw_bin_sha256': sha(out / 'taps.bin'),
              'texts_sha256': sha(args.texts), 'arms': arms, 'tool_exit': proc.returncode}
    (out / 'capture-report.json').write_text(json.dumps(report, indent=1) + '\n')
    return report


def export(args):
    wdir = Path(args.world)
    w = json.loads((wdir / 'world.json').read_text())
    episodes = w['episodes']
    texts = [e['input'] for e in episodes] + [e['outcomes'][a] for a in ACTIONS for e in episodes]
    with np.load(args.taps, allow_pickle=False) as z:
        if z['texts'].tolist() != texts:
            raise ValueError('Tap texts differ from world')
    owner = {}
    for e in episodes:
        for t in [e['input'], *e['outcomes'].values()]:
            owner.setdefault(source_identity(t), set()).add(e['partition'])
    crossing = {t for t, parts in owner.items() if len(parts) > 1}
    out = Path(args.out)
    if out.exists() and any(out.iterdir()):
        raise ValueError('Export destination must be empty')
    (out / 'sources').mkdir(parents=True)
    (out / 'native-taps.npz').write_bytes(Path(args.taps).read_bytes())
    encoder = {'schema': 'v13-action-jepa-round5-encoder-v1', 'tap_arm': args.arm,
               'capture_report': json.loads(Path(args.capture_report).read_text()), 'world_sha256': sha(wdir / 'world.json')}
    (out / 'encoder-binding.json').write_text(json.dumps(encoder, indent=1) + '\n')
    bindings = {'encoder': {'path': 'encoder-binding.json', 'sha256': sha(out / 'encoder-binding.json')},
                'native_taps': {'path': 'native-taps.npz', 'sha256': sha(out / 'native-taps.npz')}}

    def bind(text):
        key = 'text-' + text_sha(text)
        if key not in bindings:
            p = out / 'sources' / (key + '.txt')
            p.write_bytes(text.encode())
            bindings[key] = {'path': p.relative_to(out).as_posix(), 'sha256': sha(p)}
        return key

    rows, dropped, n = [], [], len(episodes)
    for i, e in enumerate(episodes):
        if any(source_identity(t) in crossing for t in [e['input'], *e['outcomes'].values()]):
            dropped.append(e['value'])
            continue
        episode = 'counter-%d' % e['value']
        for j, action in enumerate(ACTIONS):
            tx_src = wdir / e['tx'][action]['path']
            if sha(tx_src) != e['tx'][action]['sha256']:
                raise ValueError('Tool transaction record changed')
            key = 'tx-' + Path(tx_src).stem
            target = out / 'sources' / (key + '.json')
            target.write_bytes(tx_src.read_bytes())
            bindings[key] = {'path': target.relative_to(out).as_posix(), 'sha256': sha(target)}
            rows.append({'row_id': episode + ':' + action, 'episode_id': episode, 'topic': 'counter',
                         'partition': e['partition'], 'action': action,
                         'source_ids': [bind(e['input']), bind(e['outcomes'][action]), key],
                         'context_artifact_index': i, 'future_artifact_index': n * (j + 1) + i})
    dataset = {'schema': SCHEMA, 'provenance_kind': 'native_dense_tap', 'bindings': bindings,
               'state_artifact': {'binding_id': 'native_taps', 'array_key': 'x', 'transform': 'rms_normalize',
                                  'materialize_states_from_indices': True},
               'export_plan': {'schema': 'v13-action-jepa-round5-plan-v1', 'world_sha256': sha(wdir / 'world.json'),
                               'tap_arm': args.arm, 'dropped_crossing_values': dropped,
                               'episodes': {p: len({r['episode_id'] for r in rows if r['partition'] == p}) for p, _ in PARTS}},
               'rows': rows}
    (out / 'dataset.json').write_text(json.dumps(dataset, ensure_ascii=False) + '\n')
    load_dataset(out / 'dataset.json')
    return {'arm': args.arm, 'dataset_sha256': sha(out / 'dataset.json'), 'pairs': len(rows),
            'episodes': dataset['export_plan']['episodes'], 'dropped': len(dropped), 'receiver_authority': 0}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    w = sub.add_parser('world')
    w.add_argument('--out', required=True)
    w.add_argument('--states', type=int, default=400)
    w.add_argument('--seed', type=int, default=20261012)
    c = sub.add_parser('capture')
    for name in ('--tool', '--model', '--texts', '--layers', '--out'):
        c.add_argument(name, required=True)
    c.add_argument('--threads', type=int, default=4)
    e = sub.add_parser('export')
    for name in ('--world', '--taps', '--capture-report', '--arm', '--out'):
        e.add_argument(name, required=True)
    args = ap.parse_args()
    print(json.dumps({'world': world, 'capture': capture, 'export': export}[args.command](args)))


if __name__ == '__main__':
    main()
