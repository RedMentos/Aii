#!/usr/bin/env python3
"""Preregister/export authentic WP-T17 action pairs; missing taps stay unavailable.

Planning and export are offline. This command never starts a native model.
Old train-10/test-6 topics are recorded separately; new train/calibration/
retention subdivide only the old training topics. Published test topics remain
test data, and are explicitly marked historically exposed rather than fresh.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import unicodedata

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from action_jepa_objective import SCHEMA, load_dataset

ACTIONS = ('translate_de', 'question', 'negate', 'summarize')
PLAN_SCHEMA = 'v13-action-jepa-export-plan-v1'
CAPTURE_SCHEMA = 'v13-action-native-taps-capture-v1'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as file:
        while chunk := file.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def text_sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def source_identity(text):
    return ' '.join(unicodedata.normalize('NFC', text).casefold().split())


def json_sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def corpus(sentences_path, actions_path):
    topics = json.loads(Path(sentences_path).read_text())
    outcomes = json.loads(Path(actions_path).read_text())
    if not isinstance(topics, dict) or len(topics) != 16:
        raise ValueError('Original sixteen-topic corpus required')
    rows = []
    for topic in sorted(topics):
        for position, sentence in enumerate(topics[topic]):
            if not isinstance(sentence, str) or not sentence.strip() or sentence not in outcomes:
                raise ValueError('Original action outcome missing for input sentence')
            if any(not isinstance(outcomes[sentence].get(a), str) or not outcomes[sentence][a].strip() for a in ACTIONS):
                raise ValueError('Four original nonempty observed action outputs required')
            rows.append({'topic': topic, 'position': position, 'input': sentence,
                         'outcomes': {a: outcomes[sentence][a] for a in ACTIONS}})
    texts = [r['input'] for r in rows] + [r['outcomes'][a] for a in ACTIONS for r in rows]
    return topics, rows, texts


def build_plan(sentences, actions, legacy_seed=13, partition_seed=20261011):
    topics, rows, texts = corpus(sentences, actions)
    order = np.random.default_rng(legacy_seed).permutation(sorted(topics)).tolist()
    old_train, old_test = order[:10], order[10:]
    division = np.random.default_rng(partition_seed).permutation(old_train).tolist()
    split = {'train': division[:6], 'calibration': division[6:8], 'retention': division[8:], 'test': old_test}
    part_of = {t: part for part, selected in split.items() for t in selected}
    # Input or outcome text shared across partitions would leak native state.
    text_parts = {}
    for row in rows:
        for text in [row['input'], *row['outcomes'].values()]:
            text_parts.setdefault(source_identity(text), set()).add(part_of[row['topic']])
    collisions = {s for s, parts in text_parts.items() if len(parts) > 1}
    kept, dropped = [], []
    seen = set()
    for index, row in enumerate(rows):
        sources = [source_identity(s) for s in [row['input'], *row['outcomes'].values()]]
        reason = 'cross_partition_source_text' if any(s in collisions for s in sources) else None
        identity = source_identity(row['input'])
        if identity in seen:
            reason = reason or 'duplicate_normalized_input_episode'
        seen.add(identity)
        if reason:
            dropped.append({'original_index': index, 'input_sha256': text_sha(row['input']), 'reason': reason})
        else:
            kept.append({'original_index': index, 'topic': row['topic'], 'partition': part_of[row['topic']],
                         'episode_id': text_sha(identity)})
    counts = {part: sum(r['partition'] == part for r in kept) for part in split}
    if any(n < 2 for n in counts.values()):
        raise ValueError('Source-disjoint corpus insufficient after fixed collision exclusion')
    return {'schema': PLAN_SCHEMA, 'sentences_sha256': sha(sentences), 'actions_sha256': sha(actions),
            'texts_sha256': json_sha(texts), 'actions': list(ACTIONS), 'native_text_order': 'all_inputs_then_action_major_outputs',
            'source_sentences': len(rows), 'native_rows': len(texts), 'legacy_split_seed': legacy_seed,
            'partition_seed': partition_seed, 'legacy_topics': {'train': old_train, 'test': old_test},
            'new_topics': split, 'kept_episodes': kept, 'excluded_episodes': dropped,
            'episodes_per_partition': counts,
            'source_identity_policy': 'NFC+casefold+whitespace; actual native text bytes stay unchanged',
            'exclusion_policy': 'Drop all episodes using normalized input/output text shared across partitions; deduplicate normalized input episodes before observing taps',
            'fresh_held_out_data': False, 'historical_test_topics_exposed': True,
            'candidate_hyperparameters_selected_without_new_test_scores': True,
            'canonical_architecture_complete': False, 'receiver_authority': 0}


def export_dataset(plan_path, sentences, actions, taps_path, manifest_path, out):
    plan = json.loads(Path(plan_path).read_text())
    expected = build_plan(sentences, actions, plan['legacy_split_seed'], plan['partition_seed'])
    if json_sha(plan) != json_sha(expected):
        raise ValueError('Preregistered plan or original corpus changed')
    _, rows, texts = corpus(sentences, actions)
    # Both missing/unbound features and insufficient capture metadata fail closed.
    if not Path(taps_path).is_file() or not Path(manifest_path).is_file():
        raise ValueError('Authentic native tap cache and capture manifest unavailable')
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text())
    if (manifest.get('schema') != CAPTURE_SCHEMA or manifest.get('native_extraction_observed') is not True
            or manifest.get('tap_kind') != 'llama.cpp-mean-last-layer-embedding'
            or manifest.get('plan_sha256') != sha(plan_path)
            or manifest.get('texts_sha256') != plan['texts_sha256']
            or manifest.get('taps_sha256') != sha(taps_path)):
        raise ValueError('Native extraction/corpus/cache binding unavailable or mismatched')
    artifacts = manifest['artifacts']
    if not all(name in artifacts for name in ('model_gguf', 'runner', 'extractor')) or 'runtime_libraries' not in manifest:
        raise ValueError('GGUF, runner, extractor and complete shared-library bindings required')
    for binding in list(artifacts.values()) + list(manifest['runtime_libraries'].values()):
        if sha(manifest_path.parent / binding['path']) != binding['sha256']:
            raise ValueError('Native artifact bytes changed or unavailable')
    runner = (manifest_path.parent / artifacts['runner']['path']).resolve()
    adjacent = {p.name: sha(p) for p in sorted(runner.parent.glob('*.so*')) if p.is_file()}
    declared = {name: binding['sha256'] for name, binding in manifest['runtime_libraries'].items()}
    if adjacent != declared:
        raise ValueError('Incomplete or changed adjacent shared-library inventory')
    # Existing captures must bind the original actual extractor, not this exporter.
    source = Path(__file__).with_name('jepa_ablation_bench.py')
    if artifacts['extractor']['sha256'] != sha(source):
        raise ValueError('Native extractor revision not supported')
    with np.load(taps_path, allow_pickle=False) as capture:
        raw = capture['x']
        actual_texts = capture['texts']
        if actual_texts.dtype.kind not in ('U', 'S') or actual_texts.tolist() != texts:
            raise ValueError('Actual native text order differs from original action cohort')
        if (raw.ndim != 2 or raw.dtype.kind != 'f' or raw.shape != (len(texts), 1024)
                or not np.isfinite(raw).all() or manifest.get('shape') != list(raw.shape)
                or manifest.get('dtype') != str(raw.dtype)):
            raise ValueError('Actual finite Qwen3.5 native 1024-D array/shape/dtype binding required')
    out = Path(out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Export destination must be empty; original proofs are preserved')
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(taps_path, out / 'native-taps.npz')
    if sha(out / 'native-taps.npz') != manifest['taps_sha256']:
        raise ValueError('Native tap cache changed during export')
    shutil.copyfile(manifest_path, out / 'encoder-binding.json')
    bindings = {'encoder': {'path': 'encoder-binding.json', 'sha256': sha(out/'encoder-binding.json')},
                'native_taps': {'path': 'native-taps.npz', 'sha256': sha(out/'native-taps.npz')}}
    source_dir = out / 'sources'
    source_dir.mkdir()

    def bind_text(text):
        key = 'text-' + text_sha(text)
        path = source_dir / (key + '.txt')
        if key not in bindings:
            path.write_bytes(text.encode())
            bindings[key] = {'path': path.relative_to(out).as_posix(), 'sha256': sha(path)}
        return key

    exported = []
    for episode in plan['kept_episodes']:
        i = episode['original_index']
        row = rows[i]
        for j, action in enumerate(ACTIONS):
            future_index = len(rows) * (j + 1) + i
            exported.append({'row_id': episode['episode_id'] + ':' + action,
                             'episode_id': episode['episode_id'], 'topic': row['topic'],
                             'partition': episode['partition'], 'action': action,
                             'source_ids': [bind_text(row['input']), bind_text(row['outcomes'][action])],
                             'context_artifact_index': i, 'future_artifact_index': future_index})
    dataset = {'schema': SCHEMA, 'provenance_kind': 'native_dense_tap', 'bindings': bindings,
               'state_artifact': {'binding_id': 'native_taps', 'array_key': 'x', 'transform': 'rms_normalize',
                                  'materialize_states_from_indices': True},
               'export_plan': plan, 'export_plan_sha256': sha(plan_path), 'rows': exported}
    destination = out / 'dataset.json'
    destination.write_text(json.dumps(dataset, ensure_ascii=False, allow_nan=False) + '\n')
    load_dataset(destination)  # Verify exact arrays and transitive provenance disjointness.
    receipt = {'status': 'EXPORTED', 'dataset_sha256': sha(destination), 'plan_sha256': sha(plan_path),
               'native_taps_sha256': sha(out/'native-taps.npz'), 'pairs': len(exported),
               'fresh_held_out_data': False, 'receiver_authority': 0,
               'semantic_quality_proven': False, 'canonical_architecture_complete': False}
    (out / 'export-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    commands = ap.add_subparsers(dest='command', required=True)
    plan = commands.add_parser('plan')
    plan.add_argument('--legacy-split-seed', type=int, default=13)
    plan.add_argument('--partition-seed', type=int, default=20261011)
    plan.add_argument('--out', required=True)
    export = commands.add_parser('export')
    export.add_argument('--plan', required=True)
    export.add_argument('--taps', required=True)
    export.add_argument('--capture-manifest', required=True)
    export.add_argument('--out', required=True)
    for sub in (plan, export):
        sub.add_argument('--sentences', required=True)
        sub.add_argument('--actions', required=True)
    args = ap.parse_args()
    try:
        if args.command == 'plan':
            value = build_plan(args.sentences, args.actions, args.legacy_split_seed, args.partition_seed)
            destination = Path(args.out)
            if destination.exists():
                raise ValueError('Plan already exists; do not overwrite preregistration')
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
            print(json.dumps({'status': 'PREREGISTERED', 'plan_sha256': sha(destination),
                              'episodes_per_partition': value['episodes_per_partition'],
                              'excluded_episodes': len(value['excluded_episodes'])}))
        else:
            print(json.dumps(export_dataset(args.plan, args.sentences, args.actions, args.taps, args.capture_manifest, args.out)))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'UNAVAILABLE', 'reason': str(error), 'receiver_authority': 0,
                          'canonical_architecture_complete': False}))
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
