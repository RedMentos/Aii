"""Read-only, digest-bound v2 SlotWorldJEPA inference (WP-Z12c SHADOW).

No file actions, tools, training, Age change, fact writes, or runtime authority.
This is an explicit inference interface for observations supplied by the caller.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from .common import atomic_write
from .world_jepa_slots import SlotWorldJEPA

SCHEMA = 'V13_Z12C_SHADOW_PROBE_V1'
MAX_REQUEST_BYTES = 2 * 1024 * 1024
MAX_PROVENANCE_BYTES = 8192


def _matrix(value, rows, cols, name):
    """Type-exact finite JSON numeric matrix, not NumPy's coercive conversion."""
    if type(value) is not list or len(value) != rows:
        raise ValueError(name + ': expected exact row count')
    for row in value:
        if type(row) is not list or len(row) != cols:
            raise ValueError(name + ': expected exact column count')
        for v in row:
            if type(v) not in (int, float):
                raise ValueError(name + ': expected JSON number (not bool/string)')
            try:
                valid = math.isfinite(v)
            except (TypeError, OverflowError, ValueError):
                valid = False
            if not valid:
                raise ValueError(name + ': nonfinite value')
    out = np.asarray(value, dtype=np.float64)
    if out.shape != (rows, cols) or not np.isfinite(out).all():
        raise ValueError(name + ': out-of-range or nonfinite value')
    return out


def probe_checkpoint(checkpoint, expected_sha256, expected_provenance, request):
    """Run one explicit counterfactual on a calibrated inference-only checkpoint.

    The optional after observation is evidence of a caller-supplied transition,
    NOT evidence that this function performed the proposed action.
    """
    model = SlotWorldJEPA.load(
        checkpoint, expected_provenance=expected_provenance,
        expected_sha256=expected_sha256)
    if type(request) is not dict or not {'before', 'actions'} <= request.keys() or (
            set(request) - {'before', 'actions', 'after'}):
        raise ValueError('Expected before, actions, optional after only')
    S, d, na = model.S, len(model.mu), len(model.op_counts)
    before = _matrix(request['before'], S, d, 'before')
    actions = _matrix(request['actions'], S, na, 'actions')
    if not np.logical_or(actions == 0., actions == 1.).all() or not np.all(actions.sum(axis=1) == 1.):
        raise ValueError('actions: exactly one binary operation per slot')
    after = _matrix(request['after'], S, d, 'after') if 'after' in request else None
    canonical = json.dumps(request, sort_keys=True, separators=(',', ':'),
                           ensure_ascii=False, allow_nan=False).encode('utf-8')
    if len(canonical) > MAX_REQUEST_BYTES:
        raise ValueError('Request exceeds bounded size')
    X = before.reshape(1, S * d)
    A = actions.reshape(1, S, na)
    predicted, spread = model.predict(X, A)
    confidence, labels = model.confidence(X, A)
    errors = (model.slot_errors(X, A, after.reshape(1, S * d))[0]
              if after is not None else None)
    values = [predicted, spread, confidence]
    if errors is not None:
        values.append(errors)
    if not all(np.isfinite(v).all() for v in values):
        raise ValueError('Nonfinite model inference: no SHADOW output')
    conf = float(confidence[0])
    if not 0. <= conf <= 1. or np.any(spread < 0) or (errors is not None and np.any(errors < 0)):
        raise ValueError('Invalid calibrated model inference')
    if labels[0] not in ('MODEL_SIMULATION', 'SIMULATION_UNCERTAIN'):
        raise ValueError('Unknown simulation label')
    return {
        'schema': SCHEMA,
        'mode': 'SHADOW_ONLY',
        'authority': 0,
        'action_executed': False,
        'learning_performed': False,
        'after_supplied': after is not None,
        'after_verified': False,  # caller data is not independently attested
        'checkpoint_sha256': expected_sha256,
        'request_sha256': hashlib.sha256(canonical).hexdigest(),
        'simulation_label': labels[0],
        'confidence': conf,
        'predicted_next_latent': predicted[0].tolist(),
        'slot_spread': spread[0].tolist(),
        'slot_errors': None if errors is None else errors.tolist(),
        'claim_limit': 'Inferred target latent only; not observed outcome, causality, or decision authority',
    }


def _json_file(path, max_bytes):
    # A size check *after* Path.read_bytes is not a memory bound: a caller
    # can pass a multi-GB local file on a 6-GB-class phone. Read at most
    # one byte past the accepted limit, including when the file grows.
    with Path(path).open('rb') as stream:
        raw = stream.read(max_bytes + 1)
    if not raw or len(raw) > max_bytes:
        raise ValueError('JSON input missing or exceeds size bound')
    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ValueError('Duplicate JSON key: ' + k)
            out[k] = v
        return out
    def bad_constant(v):
        raise ValueError('Nonfinite JSON constant: ' + v)
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                      parse_constant=bad_constant)


def main(argv=None):
    parser = argparse.ArgumentParser(description='V13 read-only World-JEPA v2 SHADOW inference')
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--sha256', required=True, help='exact pinned checkpoint SHA256')
    parser.add_argument('--provenance', required=True, help='JSON file of exact expected provenance')
    parser.add_argument('--input', required=True, help='JSON file: before, actions, optional after')
    parser.add_argument('--output', help='explicit atomic JSON output path (otherwise stdout)')
    args = parser.parse_args(argv)
    provenance = _json_file(args.provenance, MAX_PROVENANCE_BYTES)
    request = _json_file(args.input, MAX_REQUEST_BYTES)
    result = probe_checkpoint(args.checkpoint, args.sha256, provenance, request)
    payload = json.dumps(result, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False) + '\n'
    if args.output:
        destination = Path(args.output).resolve()
        protected = {Path(p).resolve() for p in (args.checkpoint, args.input, args.provenance)}
        if destination in protected:
            raise ValueError('Output must not replace checkpoint, input or provenance')
        atomic_write(args.output, payload)
    else:
        print(payload, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
