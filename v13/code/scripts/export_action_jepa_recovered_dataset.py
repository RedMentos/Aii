#!/usr/bin/env python3
"""Export the recovered 1875-row native action capture for the preregistered training.

Offline adapter; never starts a native model. The unchanged exporter re-hashes
the model GGUF, runner and shared libraries on disk. Those bytes are not present
in a fresh workspace, so this adapter binds them through the capture lineage
instead: the registration (whose SHA is embedded in every raw native batch and
in the NPZ checkpoint) must declare exactly the artifact hashes of the
preregistered export manifest. Rows, partitions and source-text bindings must be
identical to the preregistered dataset; only the native tap binding differs,
because the first capture's NPZ bytes (533ff0be...) were lost. The manifest
records this deviation explicitly. No authority is granted.
"""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture_action_jepa_taps as producer
from action_jepa_objective import SCHEMA, load_dataset
from export_action_jepa_dataset import ACTIONS, CAPTURE_SCHEMA, build_plan, corpus, json_sha, sha, text_sha

ADAPTER = 'v13-action-jepa-recovered-export-v1'


def reference(metadata_zip):
    """Preregistered export: encoder manifest and dataset (rows only use indices)."""
    with zipfile.ZipFile(metadata_zip) as saved:
        restore = json.loads(saved.read('RESTORE.json'))
        manifest_bytes = saved.read('encoder-binding.json')
        dataset_bytes = gzip.decompress(saved.read('dataset.json.gz'))
    if hashlib.sha256(dataset_bytes).hexdigest() != restore['dataset_uncompressed_sha256']:
        raise ValueError('Reference dataset bytes changed')
    manifest = json.loads(manifest_bytes)
    dataset = json.loads(dataset_bytes)
    if dataset['bindings']['encoder']['sha256'] != hashlib.sha256(manifest_bytes).hexdigest():
        raise ValueError('Reference manifest is not the one bound by the reference dataset')
    return restore, manifest, dataset


def export(restored, metadata_zip, plan_path, sentences, actions, out):
    restored, out = Path(restored), Path(out).resolve()
    plan = json.loads(Path(plan_path).read_text())
    if json_sha(plan) != json_sha(build_plan(sentences, actions, plan['legacy_split_seed'], plan['partition_seed'])):
        raise ValueError('Preregistered plan or original corpus changed')
    registry_bytes = (restored / 'registration.json').read_bytes()
    registry = json.loads(registry_bytes)
    registry_sha = hashlib.sha256(registry_bytes).hexdigest()
    if (registry['plan']['sha256'] != sha(plan_path) or registry['sentences']['sha256'] != sha(sentences)
            or registry['actions']['sha256'] != sha(actions)):
        raise ValueError('Capture registration is bound to a different plan/corpus')
    _, rows, texts = corpus(sentences, actions)
    if not json_sha(texts) == registry['texts_sha256'] == plan['texts_sha256']:
        raise ValueError('Native input order differs from plan')
    # Verifies every raw native batch against the floats and the registration.
    x, records = producer.load_checkpoint(restored, texts, registry_sha)
    if x.shape != (len(texts), 1024):
        raise ValueError('Complete 1875-row capture required; no partial training')

    restore, ref_manifest, ref_dataset = reference(metadata_zip)
    if ref_manifest.get('schema') != CAPTURE_SCHEMA or ref_manifest['registration_sha256'] != registry_sha:
        raise ValueError('Recovered capture is not the preregistered registration')
    declared = lambda m: ({k: v['sha256'] for k, v in m['artifacts'].items()},
                          {k: v['sha256'] for k, v in m['runtime_libraries'].items()})
    if declared(ref_manifest) != declared(registry):
        raise ValueError('Native model/runner/library hashes differ from preregistered export')
    if ref_manifest['artifacts']['extractor']['sha256'] != sha(Path(__file__).with_name('jepa_ablation_bench.py')):
        raise ValueError('Native extractor revision not supported')
    if ref_dataset['export_plan_sha256'] != sha(plan_path) or ref_dataset['export_plan'] != plan:
        raise ValueError('Reference dataset used another plan')

    if out.exists() and any(out.iterdir()):
        raise ValueError('Export destination must be empty')
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(restored / 'taps.npz', out / 'native-taps.npz')
    taps_sha = sha(out / 'native-taps.npz')
    manifest = copy.deepcopy(ref_manifest)
    manifest.update({
        'taps_sha256': taps_sha, 'shape': list(x.shape), 'dtype': str(x.dtype),
        'completed_batches': len(records), 'completed_rows': len(x),
        'recovered_export': {
            'adapter': ADAPTER, 'adapter_source_sha256': sha(__file__),
            'superseded_taps_sha256': ref_manifest['taps_sha256'],
            'superseded_taps_bytes_available': False,
            'reference_manifest_sha256': ref_dataset['bindings']['encoder']['sha256'],
            'reference_dataset_sha256': restore['dataset_uncompressed_sha256'],
            'artifact_bytes_rehashed_locally': False,
            'artifact_binding_verified_via': 'registration_sha256 embedded in every raw native batch and the NPZ checkpoint; registration artifact/library hashes equal the preregistered manifest',
            'raw_batches_verified_against_floats': len(records)}})
    (out / 'encoder-binding.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    bindings = {'encoder': {'path': 'encoder-binding.json', 'sha256': sha(out / 'encoder-binding.json')},
                'native_taps': {'path': 'native-taps.npz', 'sha256': taps_sha}}
    (out / 'sources').mkdir()

    def bind_text(text):
        key = 'text-' + text_sha(text)
        path = out / 'sources' / (key + '.txt')
        if key not in bindings:
            path.write_bytes(text.encode())
            bindings[key] = {'path': path.relative_to(out).as_posix(), 'sha256': sha(path)}
        return key

    exported = []
    for episode in plan['kept_episodes']:
        i = episode['original_index']
        row = rows[i]
        for j, action in enumerate(ACTIONS):
            exported.append({'row_id': episode['episode_id'] + ':' + action,
                             'episode_id': episode['episode_id'], 'topic': row['topic'],
                             'partition': episode['partition'], 'action': action,
                             'source_ids': [bind_text(row['input']), bind_text(row['outcomes'][action])],
                             'context_artifact_index': i, 'future_artifact_index': len(rows) * (j + 1) + i})
    if exported != ref_dataset['rows']:
        raise ValueError('Rows differ from preregistered dataset')
    texts_only = lambda b: {k: v for k, v in b.items() if k.startswith('text-')}
    if texts_only(bindings) != texts_only(ref_dataset['bindings']):
        raise ValueError('Source text bindings differ from preregistered dataset')
    dataset = {'schema': SCHEMA, 'provenance_kind': 'native_dense_tap', 'bindings': bindings,
               'state_artifact': ref_dataset['state_artifact'], 'export_plan': plan,
               'export_plan_sha256': sha(plan_path), 'rows': exported}
    destination = out / 'dataset.json'
    destination.write_text(json.dumps(dataset, ensure_ascii=False, allow_nan=False) + '\n')
    load_dataset(destination)
    receipt = {'status': 'EXPORTED_FROM_RECOVERED_CAPTURE', 'adapter': ADAPTER,
               'dataset_sha256': sha(destination), 'plan_sha256': sha(plan_path),
               'native_taps_sha256': taps_sha, 'pairs': len(exported),
               'rows_identical_to_preregistered_dataset': True,
               'preregistered_dataset_sha256': restore['dataset_uncompressed_sha256'],
               'superseded_taps_sha256': ref_manifest['taps_sha256'],
               'fresh_held_out_data': False, 'receiver_authority': 0,
               'semantic_quality_proven': False, 'canonical_architecture_complete': False}
    (out / 'export-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--restored', required=True, help='output folder of action_jepa_delta_storage.py restore')
    ap.add_argument('--reference-metadata', required=True, help='preregistered dataset-metadata.zip')
    ap.add_argument('--plan', required=True)
    ap.add_argument('--sentences', required=True)
    ap.add_argument('--actions', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    print(json.dumps(export(a.restored, a.reference_metadata, a.plan, a.sentences, a.actions, a.out)))


if __name__ == '__main__':
    main()
