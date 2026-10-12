#!/usr/bin/env python3
"""Action-JEPA round 7: fresh capture for the round-6 objective (no exposed test data).

Text: the round-3 pipeline (scripts/action_jepa_round3.py generate/capture/export)
runs unchanged with new preregistered topics; round-4 taps come from
scripts/action_jepa_round4.py. Tools: this script draws a new counter world whose
start values never occurred in the round-5 world and runs the same real `calc`
tool calls as scripts/action_jepa_round5_tools.py; capture and export of that
world use the round-5 script unchanged. Read-only use of runtime modules; no
authority is granted.
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import action_jepa_round5_tools as r5


def fresh_values(previous_world, states, seed):
    used = {e['value'] for e in json.loads(Path(previous_world).read_text())['episodes']}
    pool = np.asarray([v for v in range(1, 1000) if v not in used])
    if len(pool) < states:
        raise ValueError('Not enough unused start values')
    rng = np.random.default_rng(seed)
    values = sorted(rng.choice(pool, size=states, replace=False).tolist())
    return values, rng.permutation(values).tolist(), sorted(used)


def world(args):
    """Same tool calls, templates and partition shares as round 5; only the start values are new."""
    from v13.store import Store
    from v13.agi.tools import ToolRegistry
    values, order, used = fresh_values(args.previous_world, args.states, args.seed)
    part_of, start = {}, 0
    for name, share in r5.PARTS:
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
            row = {'value': v, 'partition': part_of[v], 'input': r5.TEMPLATE.format(n=v), 'outcomes': {}, 'tx': {}}
            for action, expr in r5.ACTIONS.items():
                tx = tools.call('calc', {'expression': expr.format(n=v)}, origin='USER', intent='round7:' + action)
                if tx['status'] != 'EXECUTED' or tx['error']:
                    raise RuntimeError('Tool call did not execute: %s' % tx['status'])
                record = {k: tx[k] for k in ('id', 'tool', 'risk', 'origin', 'args', 'intent', 'status', 'reason',
                                             'result', 'error', 'action_tx', 'created')}
                path = out / 'tx' / (tx['id'] + '.json')
                path.write_text(json.dumps(record, sort_keys=True) + '\n')
                row['outcomes'][action] = r5.OUTCOME[action].format(n=tx['result'])
                row['tx'][action] = {'path': 'tx/' + path.name, 'sha256': r5.sha(path)}
            episodes.append(row)
    finally:
        store.close()
    doc = {'schema': 'v13-action-jepa-round7-world-v1', 'utc': r5.now(), 'seed': args.seed, 'states': len(values),
           'template': r5.TEMPLATE, 'outcome_templates': r5.OUTCOME, 'protocol': 'round5-v2 with fresh values',
           'actions': r5.ACTIONS, 'tool': 'calc via v13.agi.tools.ToolRegistry (sandbox store)',
           'previous_world_sha256': r5.sha(args.previous_world), 'excluded_previous_values': len(used),
           'episodes': episodes}
    (out / 'world.json').write_text(json.dumps(doc, indent=1) + '\n')
    texts = [e['input'] for e in episodes] + [e['outcomes'][a] for a in r5.ACTIONS for e in episodes]
    (out / 'texts.json').write_text(json.dumps(texts) + '\n')
    return {'states': len(values), 'texts': len(texts), 'world_sha256': r5.sha(out / 'world.json'),
            'partitions': {p: sum(e['partition'] == p for e in episodes) for p, _ in r5.PARTS}}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    w = sub.add_parser('world')
    w.add_argument('--previous-world', required=True)
    w.add_argument('--out', required=True)
    w.add_argument('--states', type=int, default=400)
    w.add_argument('--seed', type=int, default=20261013)
    args = ap.parse_args()
    print(json.dumps(world(args)))


if __name__ == '__main__':
    main()
