#!/usr/bin/env python3
"""Seal complete native action-JEPA evidence into lossless restoreable archives."""
import argparse
import gzip
import io
import json
from pathlib import Path
import shutil
import sys
import zipfile
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_action_jepa_dataset import sha
from action_jepa_objective import load_dataset
from capture_action_jepa_taps import load_checkpoint


def deterministic_zip(path, entries):
    if path.exists():
        raise ValueError('Sealed archive already exists; never overwrite original evidence')
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, raw in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise ValueError('Sealed archive CRC failed: ' + bad)
        for name, raw in entries.items():
            if archive.read(name) != raw:
                raise ValueError('Archive roundtrip bytes changed: ' + name)


def seal(capture, dataset, out):
    capture, dataset, out = Path(capture).resolve(), Path(dataset).resolve(), Path(out).resolve()
    manifest = json.loads((capture/'capture-manifest.json').read_text())
    registry = json.loads((capture/'registration.json').read_text())
    if manifest.get('native_extraction_observed') is not True or manifest.get('worker_reaped') is not True:
        raise ValueError('Complete reaped actual native capture required')
    if sha(capture/'taps.npz') != manifest['taps_sha256']:
        raise ValueError('Native cache bytes changed before sealing')
    with np.load(capture/'taps.npz', allow_pickle=False) as cache:
        texts = cache['texts'].tolist()
    x, records = load_checkpoint(capture, texts, sha(capture/'registration.json'))
    if len(x) != registry['expected_rows'] or manifest['completed_rows'] != len(x):
        raise ValueError('Partial native capture cannot be sealed as complete')
    doc, *_ = load_dataset(dataset)
    artifact = doc['bindings'][doc['state_artifact']['binding_id']]
    if artifact['sha256'] != manifest['taps_sha256']:
        raise ValueError('Evaluated dataset is not this actual native cache')
    if out.exists() and any(out.iterdir()):
        raise ValueError('Sealed evidence destination must be empty')
    out.mkdir(parents=True, exist_ok=True)
    raw_entries = {r['path']: (capture/r['path']).read_bytes() for r in records}
    for name in ('registration.json', 'capture-manifest.json', 'capture-state.json'):
        raw_entries[name] = (capture/name).read_bytes()
    for pattern in ('failed-attempt-*.json', 'native-server-*.log', '*observer*.json'):
        for p in capture.glob(pattern):
            raw_entries[p.name] = p.read_bytes()
    deterministic_zip(out/'native-raw-batches.zip', raw_entries)
    raw = dataset.read_bytes()
    buffer = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=buffer, compresslevel=9, mtime=0) as stream:
        stream.write(raw)
    compressed = buffer.getvalue()
    if gzip.decompress(compressed) != raw:
        raise ValueError('Compressed dataset roundtrip bytes changed')
    gzip_path = out/'dataset.json.gz'
    if gzip_path.exists():
        raise ValueError('Sealed dataset already exists')
    gzip_path.write_bytes(compressed)
    metadata = {'dataset.json.gz': compressed}
    for name, binding in doc['bindings'].items():
        if name == doc['state_artifact']['binding_id']:
            continue
        path = dataset.parent / binding['path']
        # All retained metadata paths must stay inside the portable dataset root.
        relative = path.resolve().relative_to(dataset.parent)
        metadata[relative.as_posix()] = path.read_bytes()
    if (dataset.parent/'export-receipt.json').exists():
        metadata['export-receipt.json'] = (dataset.parent/'export-receipt.json').read_bytes()
    restore = {'schema': 'v13-action-jepa-evidence-restore-v1',
               'dataset_uncompressed_sha256': sha(dataset), 'dataset_gzip_sha256': sha(gzip_path),
               'native_taps_sha256': manifest['taps_sha256'],
               'native_taps_filename_in_restored_dataset': artifact['path'],
               'raw_batch_records': records, 'pair_count': len(doc['rows']),
               'instructions': ['Extract dataset-metadata.zip into an empty folder.',
                                'Copy the separately supplied exact native taps NPZ into native-taps.npz in that folder.',
                                'Decompress dataset.json.gz into dataset.json, retaining exact bytes.',
                                'Verify SHA256 of dataset.json and native-taps.npz against this manifest.',
                                'Run scripts/action_jepa_objective.py train --dataset RESTORED/dataset.json --out NEW_OUT.',
                                'For capture resume, extract native-raw-batches.zip into the original capture folder and retain original taps.npz/registration bindings.'],
               'semantic_quality_proven': False, 'receiver_authority': 0, 'canonical_architecture_complete': False}
    metadata['RESTORE.json'] = (json.dumps(restore, indent=2) + '\n').encode()
    deterministic_zip(out/'dataset-metadata.zip', metadata)
    shutil.copyfile(capture/'taps.npz', out/'native-taps.npz')
    receipt = restore | {'archives': {p.name: {'sha256': sha(p), 'bytes': p.stat().st_size}
                                     for p in out.iterdir() if p.is_file()},
                         'capture_rows': len(x), 'actual_batch_count': len(records),
                         'failed_attempts_preserved': manifest.get('failed_attempts_preserved', [])}
    (out/'sealed-evidence.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--capture', required=True)
    ap.add_argument('--dataset', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    print(json.dumps(seal(args.capture, args.dataset, args.out)))


if __name__ == '__main__':
    main()
