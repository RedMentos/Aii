"""Explicit offline read-only World-JEPA SHADOW checkpoint operator probe.

No model downloads, Runtime hook, tool execution, training resume or age authority.
Input and fitted NPZ stay local/private; never commit real checkpoint/input bytes.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import stat
import sys

import numpy as np

from v13 import world_jepa as wj
from v13 import world_jepa_shadow_checkpoint as cp

SCHEMA = 'v13.world_jepa.shadow_operator_probe.v1'
MAX_INPUT_BYTES = 256 * 1024
MAX_ROWS = 128
MAX_ABS_FEATURE = 1_000_000.


def _read_private_json(path):
    """Read one bounded regular file without following a final symlink."""
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(os.fspath(path), flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_INPUT_BYTES:
            raise ValueError('Probe input must be a bounded nonempty regular file')
        chunks, total = [], 0
        while True:
            block = os.read(fd, min(65536, MAX_INPUT_BYTES + 1 - total))
            if not block:
                break
            total += len(block)
            if total > MAX_INPUT_BYTES:
                raise ValueError('Probe input grew beyond size limit')
            chunks.append(block)
        after = os.fstat(fd)
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
            raise ValueError('Probe input changed during read')
    finally:
        os.close(fd)

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate probe JSON key')
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError('Nonfinite probe JSON constant: ' + value)

    return json.loads(b''.join(chunks).decode('utf-8'),
                      object_pairs_hook=unique, parse_constant=nonfinite)


def _matrix(value, columns, label):
    if (type(value) is not list or not 1 <= len(value) <= MAX_ROWS or
            any(type(row) is not list or len(row) != columns for row in value)):
        raise ValueError('Probe ' + label + ' shape mismatch')
    for row in value:
        for number in row:
            if (type(number) not in (int, float) or
                    abs(number) > MAX_ABS_FEATURE or not math.isfinite(number)):
                raise ValueError('Invalid probe ' + label + ' number')
    return np.asarray(value, dtype=np.float64)


def infer(checkpoint, source_sha256, checkpoint_sha256, payload):
    """Return bounded SHADOW predictions; never authorize an external action."""
    model = cp.load(checkpoint, source_sha256, checkpoint_sha256)
    if type(payload) is not dict or set(payload) != {'observations', 'actions'}:
        raise ValueError('Probe requires exactly observations and actions')
    X = _matrix(payload['observations'], len(model.mu), 'observations')
    A = _matrix(payload['actions'], len(model._action_counts), 'actions')
    if len(A) != len(X):
        raise ValueError('Probe observation/action row mismatch')
    if not (np.all((A == 0.) | (A == 1.)) and np.all(A.sum(1) == 1.)):
        raise ValueError('Probe actions must be exactly one-hot')
    prediction, spread = model.predict(X, A)
    ood = model.ood(X)
    confidence, labels = model.confidence(X, A)
    arrays = (prediction, spread, ood, confidence)
    if not all(np.isfinite(a).all() for a in arrays):
        raise ValueError('Nonfinite SHADOW inference result')
    return {
        'schema': SCHEMA,
        'scope': 'PRIVATE_READ_ONLY_SHADOW_INFERENCE',
        'source_sha256': source_sha256,
        'source_bytes_verified_by_cli': False,
        'checkpoint_sha256': checkpoint_sha256,
        'checkpoint_bytes_verified': True,
        'model_revision': wj.REVISION,
        'rows': len(X),
        'predicted_next_latent': prediction.tolist(),
        'ensemble_spread': spread.tolist(),
        'ood': ood.tolist(),
        'confidence': confidence.tolist(),
        'labels': labels,
        'runtime_wired': False,
        'training_resume': False,
        'age_authority': 0,
        'tool_authority': False,
        'claim_limit': 'Local model simulation only; not native/Redmi utility or permission to act',
    }


def main(argv=None, stdout=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--checkpoint-sha256', required=True)
    parser.add_argument('--input-json', type=Path, required=True)
    args = parser.parse_args(argv)
    payload = _read_private_json(args.input_json)
    report = infer(args.checkpoint, args.source_sha256,
                   args.checkpoint_sha256, payload)
    output = sys.stdout if stdout is None else stdout
    output.write(json.dumps(report, sort_keys=True, allow_nan=False) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
