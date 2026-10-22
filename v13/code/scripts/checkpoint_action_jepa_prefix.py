#!/usr/bin/env python3
"""Close a validated atomic native prefix without requiring a stopped worker.

Reads taps.npz once. Raw successful batches are immutable, so concurrent append
cannot turn that frozen prefix into a mixed checkpoint. Partial remains partial.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_action_jepa_taps import sha, validate_response, corpus, json_sha
from seal_action_jepa_evidence import deterministic_zip


def checkpoint(capture, destination):
    capture, destination = Path(capture), Path(destination)
    registry_bytes = (capture/'registration.json').read_bytes()
    registry_sha = hashlib.sha256(registry_bytes).hexdigest()
    registry = json.loads(registry_bytes)
    taps_bytes = (capture/'taps.npz').read_bytes()
    with np.load(io.BytesIO(taps_bytes), allow_pickle=False) as saved:
        x, texts = saved['x'], saved['texts'].tolist()
        meta = json.loads(str(saved['checkpoint']))
    if (meta['registry_sha256'] != registry_sha or meta['completed_rows'] != len(x)
            or x.shape != (len(texts), registry['expected_dim']) or x.dtype != np.dtype('float64')
            or not np.isfinite(x).all() or not 0 < len(x) <= registry['expected_rows']):
        raise ValueError('Atomic native prefix shape/registration mismatch')
    for key in ('sentences','actions'):
        if sha(registry[key]['path']) != registry[key]['sha256']:
            raise ValueError('Original source corpus binding changed')
    _, _, expected_texts = corpus(registry['sentences']['path'],registry['actions']['path'])
    if json_sha(expected_texts) != registry['texts_sha256'] or texts != expected_texts[:len(x)]:
        raise ValueError('Native prefix differs from registered original input order')
    entries = {'registration.json': registry_bytes, 'taps.npz': taps_bytes}
    offset = 0
    for record in meta['batch_records']:
        name = record['path']
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts or name in entries:
            raise ValueError('Unsafe/duplicated native batch path')
        raw = (capture/relative).read_bytes()
        if hashlib.sha256(raw).hexdigest() != record['sha256']:
            raise ValueError('Immutable raw batch changed')
        batch = json.loads(raw)
        end = batch['end']
        if (batch['registry_sha256'] != registry_sha or batch['start'] != offset
                or not offset < end <= len(x) or batch['inputs'] != texts[offset:end]):
            raise ValueError('Native prefix input/source lineage mismatch')
        actual = validate_response(batch['response'], end-offset, batch['model_alias'])
        if not np.array_equal(actual, x[offset:end]):
            raise ValueError('Atomic prefix floats differ from native raw response')
        entries[name] = raw
        offset = end
    if offset != len(x):
        raise ValueError('Native prefix has unrecorded rows')
    manifest = {'schema':'v13-native-closed-prefix-v1', 'status':'PARTIAL_CHECKPOINT',
                'completed_rows':len(x), 'expected_rows':registry['expected_rows'],
                'raw_batches':len(meta['batch_records']), 'registration_sha256':registry_sha,
                'taps_sha256':hashlib.sha256(taps_bytes).hexdigest(),
                'checkpoint_source':'single atomic NPZ read plus immutable hash-bound raw batches',
                'complete_capture_claimed':False, 'worker_exit_claimed':False,
                'native_extraction_observed':False, 'semantic_quality_proven':False,
                'receiver_authority':0, 'canonical_architecture_complete':False}
    entries['CLOSED-PREFIX.json'] = (json.dumps(manifest,indent=2)+'\n').encode()
    deterministic_zip(destination, entries)
    return manifest | {'archive_sha256':sha(destination), 'archive_bytes':destination.stat().st_size}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--capture',required=True)
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    print(json.dumps(checkpoint(args.capture,args.out)))


if __name__=='__main__':
    main()
