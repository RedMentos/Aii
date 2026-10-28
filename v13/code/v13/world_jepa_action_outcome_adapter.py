"""Read-only V13 digital action/outcome -> World-JEPA SHADOW array adapter.

This is not a physical next-state model. The target [state, outcome] is a
fixed observation encoding, and no inference/training/Runtime authority is
created. Callers must separately authorize any read of a real Store.
"""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np

from v13 import world_model

SCHEMA = 'v13.world_jepa.digital_action_outcome_adapter.v1'
MAX_ROWS = 2048
MIN_SPLIT_ROWS = 8
ACTIONS = tuple(world_model.ACTIONS)


def _vec(value, size):
    if (not isinstance(value, (list, tuple, np.ndarray))
            or len(value) != size):
        raise ValueError('RUN50_INVALID_VECTOR_SHAPE')
    out = []
    for item in value:
        if (isinstance(item, (bool, np.bool_))
                or not isinstance(item, (int, float, np.integer, np.floating))
                or not math.isfinite(float(item))):
            raise ValueError('RUN50_NONFINITE_OR_INVALID_VECTOR')
        out.append(float(item))
    return out


def _row_digest(row):
    raw = json.dumps(row, sort_keys=True, separators=(',', ':'),
                     allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _partition(action_id):
    # Stable across Store row ordering and across Python hash randomization.
    digest = hashlib.sha256(action_id.encode('utf-8')).digest()
    return 'holdout' if int.from_bytes(digest[:8], 'big') % 4 == 0 else 'train'


def build(records):
    """Construct a bounded, ID-disjoint SHADOW train/holdout candidate.

    Input records are exactly the output shape of world_model.transitions().
    They are caller-supplied: this function cannot authenticate the Store,
    permissions, actual model fit provenance or real-world causality.
    """
    if type(records) not in (list, tuple) or not 16 <= len(records) <= MAX_ROWS:
        raise ValueError('RUN50_INVALID_RECORD_COUNT')
    canonical = []
    seen = set()
    for item in records:
        if type(item) is not dict:
            raise ValueError('RUN50_INVALID_RECORD')
        ident = item.get('action_id')
        route = item.get('a')
        if (type(ident) is not str or not 1 <= len(ident) <= 128
                or ident in seen or route not in ACTIONS):
            raise ValueError('RUN50_INVALID_OR_DUPLICATE_ACTION_ID')
        seen.add(ident)
        canonical.append({'action_id': ident, 's': _vec(item.get('s'), 4),
                          'a': route, 'y': _vec(item.get('y'), 3)})
    canonical.sort(key=lambda item: item['action_id'])
    train = [r for r in canonical if _partition(r['action_id']) == 'train']
    holdout = [r for r in canonical if _partition(r['action_id']) == 'holdout']
    if len(train) < MIN_SPLIT_ROWS or len(holdout) < MIN_SPLIT_ROWS:
        raise ValueError('RUN50_INSUFFICIENT_SPLIT_ROWS')
    if (len({r['a'] for r in train}) < 2
            or len({r['a'] for r in holdout}) < 2
            or not {r['a'] for r in holdout}.issubset({r['a'] for r in train})):
        raise ValueError('RUN50_INSUFFICIENT_ACTION_SUPPORT')

    def arrays(rows):
        x = np.asarray([r['s'] + [0., 0., 0.] for r in rows], dtype=np.float64)
        a = np.asarray([world_model.onehot(r['a']) for r in rows], dtype=np.float64)
        x2 = np.asarray([r['s'] + r['y'] for r in rows], dtype=np.float64)
        return x, a, x2

    def digest(rows):
        h = hashlib.sha256()
        for row in rows:
            h.update(bytes.fromhex(_row_digest(row)))
        return h.hexdigest()

    train_arrays, holdout_arrays = arrays(train), arrays(holdout)
    train_ids = tuple(r['action_id'] for r in train)
    holdout_ids = tuple(r['action_id'] for r in holdout)
    if set(train_ids) & set(holdout_ids):
        raise ValueError('RUN50_SPLIT_OVERLAP')
    manifest = {'schema': SCHEMA, 'scope': 'READONLY_SHADOW_NO_AUTHORITY',
                'mapping': 'X=[observed_s4,zeros3],A=route_onehot4,X2=[observed_s4,outcome_y3]',
                'source_verified': False, 'real_world_causality_proven': False,
                'training_executed': False, 'native_executed': False,
                'phone_measured': False, 'age_authority': 0,
                'learning_gate_pass': False, 'whole_system_complete': False,
                'jepa_weight': 0, 'n_total': len(canonical),
                'n_train': len(train), 'n_holdout': len(holdout),
                'within_supplied_records_id_disjoint': True,
                'train_rows_sha256': digest(train),
                'holdout_rows_sha256': digest(holdout),
                'all_rows_sha256': digest(canonical)}
    return {'manifest': manifest, 'train': train_arrays,
            'holdout': holdout_arrays, 'train_action_ids': train_ids,
            'holdout_action_ids': holdout_ids}
