"""Explicit closed V13 SQLite -> train-only World-JEPA -> private SHADOW probe.

Offline observed DIGITAL outcome path, not next physical state. No live runtime,
DB writes, model download, optimizer resume, tools or age authority.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3
import sys

import numpy as np

from scripts import world_jepa_digital_shadow as bridge
from scripts import world_jepa_readonly_store as closed
from scripts import world_jepa_shadow_operator_probe as probe
from v13 import world_jepa as wj
from v13 import world_jepa_shadow_checkpoint as cp
from v13 import world_model as wm

SCHEMA = 'v13.world_jepa.closedstore_private_shadow.v1'
MAX_STEPS = 400
SEED = 3
ENSEMBLE = 2


def run_db(db_path, private_checkpoint, steps=20):
    """Fit only registered train rows; persist private inference-only weights."""
    if type(steps) is not int or not 1 <= steps <= MAX_STEPS:
        raise ValueError('Invalid bounded SHADOW training steps')
    store = closed.ReadOnlyStore(db_path)
    try:
        rows = wm.transitions(store)
    finally:
        store.close()
    data = bridge.make_dataset(rows)
    tr, te = data['train'], data['heldout']
    X, X2, A = (data[k] for k in ('X', 'X2', 'A'))
    model = wj.WorldJEPA(seed=SEED, ensemble=ENSEMBLE).fit(
        X[tr], A[tr], X2[tr], steps=steps, log_every=max(1, steps))
    record = cp.save(model, private_checkpoint, data['source_sha256'])
    result = probe.infer(private_checkpoint, data['source_sha256'],
                         record['sha256'], {
                             'observations': X[te].tolist(),
                             'actions': A[te].tolist(),
                         })
    labels = Counter(result['labels'])
    if set(labels) - {'MODEL_SIMULATION', 'SIMULATION_UNCERTAIN'}:
        raise ValueError('Unexpected SHADOW inference label')
    return {
        'schema': SCHEMA,
        'scope': 'CLOSED_STORE_OBSERVED_DIGITAL_PRIVATE_SHADOW',
        'evidence_kind': 'LINUX_SOFTWARE_OBSERVED_DIGITAL_NOT_NATIVE_MODEL',
        'observed_store_readonly': True,
        'source_digest_kind': 'CANONICAL_OBSERVED_TRANSITIONS_NOT_DB_FILE',
        'source_sha256': data['source_sha256'],
        'train_ids_sha256': data['train_ids_sha256'],
        'heldout_ids_sha256': data['heldout_ids_sha256'],
        'checkpoint_sha256': record['sha256'],
        'checkpoint_bytes_verified': result['checkpoint_bytes_verified'],
        'checkpoint_inference_only': True,
        'optimizer_state_persisted': False,
        'observed_rows': len(X),
        'train_rows': len(tr),
        'heldout_rows': len(te),
        'steps': steps,
        'seed': SEED,
        'ensemble': ENSEMBLE,
        'model_revision': wj.REVISION,
        'mean_heldout_confidence': float(np.mean(result['confidence'])),
        'mean_heldout_ood': float(np.mean(result['ood'])),
        'mean_heldout_spread': float(np.mean(result['ensemble_spread'])),
        'heldout_label_counts': {
            'MODEL_SIMULATION': labels['MODEL_SIMULATION'],
            'SIMULATION_UNCERTAIN': labels['SIMULATION_UNCERTAIN'],
        },
        'utility_proven': False,
        'runtime_wired': False,
        'training_resume': False,
        'tool_authority': False,
        'age_authority': 0,
        'negative_gates_unchanged': bridge.NEGATIVE_GATES,
        'claim_limit': 'Observed digital outcome SHADOW only; no causal utility or native/Redmi proof',
    }


def _unavailable():
    return {
        'status': 'UNAVAILABLE',
        'reason': 'CLOSED_STORE_OR_PRIVATE_CHECKPOINT_INVALID',
        'runtime_wired': False,
        'tool_authority': False,
        'age_authority': 0,
        'utility_proven': False,
    }


def main(argv=None, stdout=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--private-checkpoint', type=Path, required=True)
    parser.add_argument('--ack-closed-store', action='store_true')
    parser.add_argument('--steps', type=int, default=20)
    args = parser.parse_args(argv)
    out = sys.stdout if stdout is None else stdout
    if not args.ack_closed_store:
        out.write(json.dumps(_unavailable(), sort_keys=True) + '\n')
        return 2
    try:
        report = run_db(args.db, args.private_checkpoint, steps=args.steps)
        rendered = json.dumps(report, sort_keys=True, allow_nan=False)
    except (ValueError, TypeError, OSError, OverflowError,
            sqlite3.Error, np.linalg.LinAlgError):
        out.write(json.dumps(_unavailable(), sort_keys=True) + '\n')
        return 2
    out.write(rendered + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
