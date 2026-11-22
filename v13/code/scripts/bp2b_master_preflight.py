#!/usr/bin/env python3
"""BP2b local master preflight: exact file SHA256, no model loading/training."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from v13.common import atomic_write

REVISION = 'bp2b-master-preflight-v1'
PIN_SCHEMA = 'v13-bp2b-master-pin-v1'
METADATA = ('config.json', 'generation_config.json', 'tokenizer.json',
            'tokenizer_config.json', 'special_tokens_map.json',
            'chat_template.jinja', 'LICENSE')
PIN_KEYS = {'schema', 'model_id', 'revision', 'license_id',
            'model_safetensors_sha256', 'model_weights_sha256_verified_locally',
            'metadata', 'evidence'}
MAX_PIN_BYTES = 32768
MAX_METADATA_BYTES = 8388608
MAX_TOTAL_METADATA_BYTES = 16777216
MAX_MODEL_BYTES = 4 * 1024 * 1024 * 1024


def _pairs_unique(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError('Duplicate pin JSON key')
        out[k] = v
    return out


def _bad_constant(v):
    raise ValueError('Nonfinite pin JSON')


def _sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def load_pin(path):
    with Path(path).open('rb') as f:
        raw = f.read(MAX_PIN_BYTES + 1)
    if not raw or len(raw) > MAX_PIN_BYTES:
        raise ValueError('Pin missing or oversized')
    pin = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs_unique,
                     parse_constant=_bad_constant)
    if type(pin) is not dict or set(pin) != PIN_KEYS or pin['schema'] != PIN_SCHEMA:
        raise ValueError('Invalid pin schema')
    if (pin['model_id'] != 'LiquidAI/LFM2.5-1.2B-Instruct'
            or pin['revision'] != '8c1348a4aac046a3a5d7698e7fcaaa8a3b7d9cdf'
            or pin['license_id'] != 'LFM Open License 1.0'
            or type(pin['model_weights_sha256_verified_locally']) is not bool
            or not _sha(pin['model_safetensors_sha256'])
            or type(pin['metadata']) is not dict
            or set(pin['metadata']) != set(METADATA)
            or type(pin['evidence']) is not dict):
        raise ValueError('Invalid pinned source identity')
    total = 0
    for name in METADATA:
        entry = pin['metadata'][name]
        if (type(entry) is not dict or set(entry) != {'sha256', 'size'}
                or not _sha(entry['sha256']) or type(entry['size']) is not int
                or not 0 < entry['size'] <= MAX_METADATA_BYTES):
            raise ValueError('Invalid metadata entry')
        total += entry['size']
    if total > MAX_TOTAL_METADATA_BYTES:
        raise ValueError('Metadata total exceeds bound')
    return pin, hashlib.sha256(raw).hexdigest()


def _hash_file(path, max_bytes, expected_size=None):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Missing or symlinked model file: ' + path.name)
    size = path.stat().st_size
    if size <= 0 or size > max_bytes or (expected_size is not None and size != expected_size):
        raise ValueError('Model file size mismatch: ' + path.name)
    digest = hashlib.sha256()
    read = 0
    with path.open('rb') as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            read += len(chunk)
            if read > max_bytes:
                raise ValueError('Model file changed beyond size bound')
            digest.update(chunk)
    if read != size:
        raise ValueError('Model file changed while hashing')
    return digest.hexdigest(), size


def verify(master_dir, pin_path, metadata_only=False):
    if type(metadata_only) is not bool:
        raise ValueError('metadata_only must be boolean')
    pin, pin_sha = load_pin(pin_path)
    master = Path(master_dir)
    if master.is_symlink() or not master.is_dir():
        raise ValueError('Missing or symlinked master directory')
    found = {}
    for name in METADATA:
        expected = pin['metadata'][name]
        actual_sha, actual_size = _hash_file(master / name, MAX_METADATA_BYTES, expected['size'])
        if actual_sha != expected['sha256']:
            raise ValueError('Metadata SHA256 mismatch: ' + name)
        found[name] = {'sha256': actual_sha, 'size': actual_size}
    model_verified = False
    if not metadata_only:
        actual_sha, _ = _hash_file(master / 'model.safetensors', MAX_MODEL_BYTES)
        if actual_sha != pin['model_safetensors_sha256']:
            raise ValueError('FP32 master SHA256 mismatch')
        model_verified = True
    return {'schema': REVISION, 'model_id': pin['model_id'], 'revision': pin['revision'],
            'pin_sha256': pin_sha, 'metadata': found,
            'master_expected_sha256': pin['model_safetensors_sha256'],
            'master_sha256_verified_locally': model_verified,
            'status': 'FULL_FILE_HASH_PASS' if model_verified else 'METADATA_ONLY_PASS',
            'model_loaded': False, 'training_performed': False, 'learning_authority': 0}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--master-dir', required=True)
    ap.add_argument('--pin', default=str(Path(__file__).resolve().parents[1] /
                                         'specs' / 'bp2b_master_metadata.json'))
    ap.add_argument('--metadata-only', action='store_true')
    ap.add_argument('--out', required=True)
    args = ap.parse_args(argv)
    report = verify(args.master_dir, args.pin, args.metadata_only)
    data = json.dumps(report, sort_keys=True, indent=2) + '\n'
    path = Path(args.out)
    if path.exists():
        if path.read_bytes() != data.encode('utf-8'):
            raise ValueError('Refusing to replace differing preflight receipt')
    else:
        atomic_write(path, data)
    print(json.dumps({'status': report['status'], 'model_loaded': False,
                      'master_sha256_verified_locally': report['master_sha256_verified_locally']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
