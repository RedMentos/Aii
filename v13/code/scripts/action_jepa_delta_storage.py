#!/usr/bin/env python3
"""Seal hash-bound raw batch deltas; restore the exact original NPZ bytes.

Storage only: the collector, native parameters, and authority are untouched.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture_action_jepa_taps as producer
from checkpoint_action_jepa_prefix import checkpoint
from seal_action_jepa_evidence import deterministic_zip

SCHEMA = 'v13-native-exact-prefix-delta-v1'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe(name):
    p = Path(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name:
        raise ValueError('Unsafe evidence path')
    return p


def regenerate(x, texts, registry_sha, records):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        producer.write_checkpoint(root, x, texts, registry_sha, records)
        return (root/'taps.npz').read_bytes()


def seal(capture, destination, base_rows):
    capture, destination = Path(capture), Path(destination)
    if type(base_rows) is not int or base_rows < 0:
        raise ValueError('Invalid base row boundary')
    # The existing validator freezes NPZ once and verifies every raw response.
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary)/'validated-prefix.zip'
        checkpoint(capture, archive)
        with zipfile.ZipFile(archive) as saved:
            entries = {name: saved.read(name) for name in saved.namelist()}
    npz = entries['taps.npz']
    registry = json.loads(entries['registration.json'])
    with np.load(io.BytesIO(npz), allow_pickle=False) as saved:
        x, texts = saved['x'], saved['texts'].tolist()
        metadata = json.loads(str(saved['checkpoint']))
    records = metadata['batch_records']
    boundaries = [0] + [json.loads(entries[r['path']])['end'] for r in records]
    if base_rows not in boundaries or base_rows >= len(x):
        raise ValueError('Delta base must be an earlier completed raw batch boundary')
    regenerated = regenerate(x, texts, metadata['registry_sha256'], records)
    if regenerated != npz:
        raise ValueError('Canonical raw/metadata regeneration differs from actual whole NPZ bytes')
    delta = {}
    for record in records:
        raw = entries[record['path']]
        if json.loads(raw)['start'] >= base_rows:
            delta[record['path']] = raw
    receipt = {'schema': SCHEMA, 'base_rows': base_rows, 'completed_rows': len(x),
               'registration_sha256': digest(entries['registration.json']),
               'original_npz_sha256': digest(npz), 'original_npz_bytes': len(npz),
               'array_sha256': digest(np.ascontiguousarray(x).tobytes()),
               'all_batch_records': records, 'delta_batch_paths': list(delta),
               'driver_sha256': producer.sha(producer.__file__),
               'numpy_version': np.__version__,
               'original_whole_npz_byte_regeneration_verified': True,
               'receiver_authority': 0, 'semantic_quality_proven': False}
    delta['registration.json'] = entries['registration.json']
    delta['DELTA-RECEIPT.json'] = (json.dumps(receipt, indent=2, sort_keys=True)+'\n').encode()
    deterministic_zip(destination, delta)
    return receipt | {'archive_sha256': producer.sha(destination), 'archive_bytes': destination.stat().st_size}


def restore(base_capture, archives, destination):
    base_capture, destination = Path(base_capture), Path(destination)
    if destination.exists():
        raise ValueError('Exact restoration requires an empty new destination')
    registry_bytes = (base_capture/'registration.json').read_bytes()
    registry = json.loads(registry_bytes)
    for key in ('sentences', 'actions'):
        if producer.sha(registry[key]['path']) != registry[key]['sha256']:
            raise ValueError('Registered corpus changed')
    _, _, texts = producer.corpus(registry['sentences']['path'], registry['actions']['path'])
    if producer.json_sha(texts) != registry['texts_sha256']:
        raise ValueError('Registered full input order changed')
    registry_sha = digest(registry_bytes)
    x, records = producer.load_checkpoint(base_capture, texts, registry_sha)
    files = {'registration.json': registry_bytes, 'taps.npz': (base_capture/'taps.npz').read_bytes()}
    for record in records:
        files[record['path']] = (base_capture/safe(record['path'])).read_bytes()
    for archive in archives:
        with zipfile.ZipFile(archive) as saved:
            names = saved.namelist()
            if len(names) != len(set(names)):
                raise ValueError('Duplicated archive entry')
            for name in names:
                safe(name)
            receipt = json.loads(saved.read('DELTA-RECEIPT.json'))
            if (receipt.get('schema') != SCHEMA or receipt.get('base_rows') != len(x)
                    or type(receipt.get('completed_rows')) is not int
                    or not len(x) < receipt['completed_rows'] <= len(texts)
                    or receipt.get('registration_sha256') != registry_sha
                    or saved.read('registration.json') != registry_bytes
                    or receipt.get('driver_sha256') != producer.sha(producer.__file__)
                    or receipt.get('numpy_version') != np.__version__
                    or receipt.get('original_whole_npz_byte_regeneration_verified') is not True):
                raise ValueError('Delta lineage/runtime/boundary mismatch')
            all_records = receipt.get('all_batch_records')
            if not isinstance(all_records, list) or all_records[:len(records)] != records:
                raise ValueError('Historical batch lineage changed')
            new_records = all_records[len(records):]
            paths = [r['path'] for r in new_records]
            if (not paths or len(paths) != len(set(paths)) or receipt.get('delta_batch_paths') != paths
                    or set(names) != set(paths + ['registration.json', 'DELTA-RECEIPT.json'])):
                raise ValueError('Missing/reordered/unexpected raw delta records')
            chunks = []
            offset = len(x)
            for record in new_records:
                raw = saved.read(record['path'])
                if digest(raw) != record['sha256']:
                    raise ValueError('Raw delta digest mismatch')
                batch = json.loads(raw)
                end = batch['end']
                if (batch['registry_sha256'] != registry_sha or batch['start'] != offset
                        or type(end) is not int or not offset < end <= receipt['completed_rows']
                        or batch['inputs'] != texts[offset:end]):
                    raise ValueError('Raw delta input/source order mismatch')
                chunks.append(producer.validate_response(batch['response'], end-offset, batch['model_alias']))
                files[record['path']] = raw
                offset = end
            if offset != receipt['completed_rows']:
                raise ValueError('Unrecorded delta rows')
            x = np.concatenate([x, *chunks], axis=0)
            if digest(np.ascontiguousarray(x).tobytes()) != receipt['array_sha256']:
                raise ValueError('Exact array digest mismatch')
            records = all_records
            npz = regenerate(x, texts, registry_sha, records)
            if len(npz) != receipt['original_npz_bytes'] or digest(npz) != receipt['original_npz_sha256']:
                raise ValueError('Exact whole NPZ digest mismatch')
            files['taps.npz'] = npz
    destination.mkdir(parents=True)
    for name, raw in files.items():
        path = destination/safe(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    verified, _ = producer.load_checkpoint(destination, texts, registry_sha)
    return {'completed_rows': len(verified), 'taps_sha256': producer.sha(destination/'taps.npz'),
            'exact_original_npz_bytes_restored': True, 'receiver_authority': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('seal'); p.add_argument('--capture', required=True); p.add_argument('--out', required=True); p.add_argument('--base-rows', type=int, required=True)
    p = commands.add_parser('restore'); p.add_argument('--base-capture', required=True); p.add_argument('--delta', action='append', required=True); p.add_argument('--out', required=True)
    args = parser.parse_args()
    result = seal(args.capture, args.out, args.base_rows) if args.command == 'seal' else restore(args.base_capture, args.delta, args.out)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
