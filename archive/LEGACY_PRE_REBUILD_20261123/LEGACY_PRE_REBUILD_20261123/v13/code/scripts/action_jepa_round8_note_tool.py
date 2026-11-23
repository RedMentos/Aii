#!/usr/bin/env python3
"""Action-JEPA round 8: a non-arithmetic real tool, the sandboxed WRITE_LOCAL note.

World: a note whose state is the text "The note reads: <content>". Every action
is a real `sandbox_note` call through the V13 ToolRegistry in a throwaway
sandbox store: WRITE_LOCAL is PROPOSED by policy and then approved per call by
this experiment script acting as the user (IH-H29), executed as an IH-H14
action transaction, and `undo` uses the registry's compensating action. Before
each action a setup write restores the episode's content. The outcome text is
built from the note file read back from the sandbox after the call, never from
a model. Every transaction record (setup, action, undo) is bound as a source of
its row. Taps come from scripts/action_jepa_round5_tools.py capture (unchanged).
Read-only use of runtime modules; nothing in code/v13 is changed and no
authority is granted.
"""
import argparse
import itertools
import json
from pathlib import Path
import sys

import numpy as np

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from action_jepa_objective import SCHEMA, load_dataset
from export_action_jepa_dataset import sha, source_identity, text_sha
import action_jepa_round5_tools as r5

VERBS = ('call', 'email', 'visit', 'pay', 'thank', 'meet', 'ask', 'remind', 'help', 'invite')
OBJECTS = ('the plumber', 'the bank', 'the dentist', 'grandma', 'the landlord', 'the school', 'the neighbour',
           'the doctor', 'the team', 'the library')
WHEN = ('today', 'tomorrow', 'on Monday', 'on Friday', 'next week', 'this evening')
TEMPLATE = 'The note reads: {c}'
ACTIONS = ('append_done', 'prefix_urgent', 'uppercase', 'undo')
OUTCOME = {'append_done': 'After appending, the note reads: {c}', 'prefix_urgent': 'After adding a prefix, the note reads: {c}',
           'uppercase': 'After uppercasing, the note reads: {c}', 'undo': 'After undo, the note reads: {c}'}
SCRATCH = 'Scratch text.'


def written(action, content):
    """The text the action writes; for undo the scratch write that is then undone."""
    return {'append_done': content + ' Done.', 'prefix_urgent': 'Urgent: ' + content,
            'uppercase': content.upper(), 'undo': SCRATCH}[action]


def contents():
    return [f'{v.capitalize()} {o} {w}.' for v, o, w in itertools.product(VERBS, OBJECTS, WHEN)]


def record(tx):
    return {k: tx.get(k) for k in ('id', 'tool', 'risk', 'origin', 'args', 'intent', 'status', 'reason', 'contract',
                                   'result', 'error', 'action_tx', 'created')}


def world(args):
    from v13.store import Store
    from v13.agi.tools import ToolRegistry
    rng = np.random.default_rng(args.seed)
    pool = contents()
    picked = sorted(rng.choice(len(pool), size=args.states, replace=False).tolist())
    order = rng.permutation(picked).tolist()
    part_of, start = {}, 0
    for name, share in r5.PARTS:
        n = int(round(share * len(order))) if name != 'test' else len(order) - start
        for i in order[start:start + n]:
            part_of[i] = name
        start += n
    out = Path(args.out)
    (out / 'tx').mkdir(parents=True, exist_ok=True)
    home = out / 'sandbox-store'
    (home / 'data/db').mkdir(parents=True)
    (home / 'data/blobs').mkdir(parents=True)
    store = Store(home)
    counts = {'proposed': 0, 'approved_executed': 0, 'undone': 0}

    def save(kind, data):
        path = out / 'tx' / (kind + '-' + data['id'] + '.json')
        path.write_text(json.dumps(data, sort_keys=True, default=str) + '\n')
        return {'path': 'tx/' + path.name, 'sha256': sha(path)}

    try:
        tools = ToolRegistry(store)
        tools.enable('sandbox_note')

        def write(note, text, intent):
            tx = tools.call('sandbox_note', {'name': note, 'text': text}, origin='USER', intent=intent)
            if tx['status'] != 'PROPOSED' or tx['reason'] != 'NEEDS_PER_CALL_APPROVAL':
                raise RuntimeError('WRITE_LOCAL must need per-call approval: %s' % tx['status'])
            counts['proposed'] += 1
            done = tools.approve(tx['id'])
            if done['status'] != 'EXECUTED' or done['error']:
                raise RuntimeError('Approved note write did not execute: %s' % done['status'])
            counts['approved_executed'] += 1
            return done

        def read(note):
            return (home / 'data' / 'tool_sandbox' / (note + '.txt')).read_text()

        episodes = []
        for i in picked:
            content, note = pool[i], 'ep%03d' % i
            row = {'index': i, 'partition': part_of[i], 'content': content, 'input': TEMPLATE.format(c=content),
                   'outcomes': {}, 'tx': {}}
            for action in ACTIONS:
                setup = write(note, content, 'round8:setup')
                if read(note) != content:
                    raise RuntimeError('Setup write not observed')
                main = write(note, written(action, content), 'round8:' + action)
                files = [save('setup', record(setup)), save('action', record(main))]
                if action == 'undo':
                    undo = tools.undo(main['id'])
                    counts['undone'] += 1
                    files.append(save('undo', dict(undo, id=main['id'] + '-undo')))
                observed = read(note)
                expected = content if action == 'undo' else written(action, content)
                if observed != expected:
                    raise RuntimeError('Observed note differs from tool contract')
                row['outcomes'][action] = OUTCOME[action].format(c=observed)
                row['tx'][action] = files
            episodes.append(row)
    finally:
        store.close()
    doc = {'schema': 'v13-action-jepa-round8-world-v1', 'utc': r5.now(), 'seed': args.seed, 'states': len(picked),
           'template': TEMPLATE, 'outcome_templates': OUTCOME, 'actions': list(ACTIONS), 'scratch': SCRATCH,
           'tool': 'sandbox_note (WRITE_LOCAL, reversible) via v13.agi.tools.ToolRegistry, per-call approval by the experiment script, undo via registry',
           'counts': counts, 'episodes': episodes}
    (out / 'world.json').write_text(json.dumps(doc, indent=1) + '\n')
    texts = [e['input'] for e in episodes] + [e['outcomes'][a] for a in ACTIONS for e in episodes]
    (out / 'texts.json').write_text(json.dumps(texts) + '\n')
    return {'states': len(picked), 'texts': len(texts), 'counts': counts, 'world_sha256': sha(out / 'world.json'),
            'partitions': {p: sum(e['partition'] == p for e in episodes) for p, _ in r5.PARTS}}


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
    encoder = {'schema': 'v13-action-jepa-round8-encoder-v1', 'tap_arm': args.arm,
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
            dropped.append(e['index'])
            continue
        episode = 'note-%03d' % e['index']
        for j, action in enumerate(ACTIONS):
            keys = []
            for f in e['tx'][action]:
                src = wdir / f['path']
                if sha(src) != f['sha256']:
                    raise ValueError('Tool transaction record changed')
                key = 'tx-' + Path(src).stem
                target = out / 'sources' / (key + '.json')
                target.write_bytes(src.read_bytes())
                bindings[key] = {'path': target.relative_to(out).as_posix(), 'sha256': sha(target)}
                keys.append(key)
            rows.append({'row_id': episode + ':' + action, 'episode_id': episode, 'topic': 'note',
                         'partition': e['partition'], 'action': action,
                         'source_ids': [bind(e['input']), bind(e['outcomes'][action]), *keys],
                         'context_artifact_index': i, 'future_artifact_index': n * (j + 1) + i})
    dataset = {'schema': SCHEMA, 'provenance_kind': 'native_dense_tap', 'bindings': bindings,
               'state_artifact': {'binding_id': 'native_taps', 'array_key': 'x', 'transform': 'rms_normalize',
                                  'materialize_states_from_indices': True},
               'export_plan': {'schema': 'v13-action-jepa-round8-plan-v1', 'world_sha256': sha(wdir / 'world.json'),
                               'tap_arm': args.arm, 'dropped_crossing_indices': dropped,
                               'episodes': {p: len({r['episode_id'] for r in rows if r['partition'] == p}) for p, _ in r5.PARTS}},
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
    w.add_argument('--seed', type=int, default=20261014)
    e = sub.add_parser('export')
    for name in ('--world', '--taps', '--capture-report', '--arm', '--out'):
        e.add_argument(name, required=True)
    args = ap.parse_args()
    print(json.dumps({'world': world, 'export': export}[args.command](args)))


if __name__ == '__main__':
    main()
