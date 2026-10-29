"""Explicit closed-SQLite World-JEPA fixed-readout heldout-action ablation.

Operator-only offline digital-outcome SHADOW. No live Runtime, private row
export, checkpoint, model permission, native claim or gate promotion.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys

import numpy as np

from scripts import world_jepa_heldout_action_readout_20261028 as ablation
from scripts import world_jepa_readonly_store as closed
from v13 import world_model

SCHEMA = 'v13.world_jepa.closedstore_fixed_action_readout.v1'


def run_db(db_path, *, steps=20):
    """Read one closed SQLite snapshot and fit/score train-only software SHADOW."""
    if type(steps) is not int or not 0 <= steps <= ablation.STEPS:
        raise ValueError('Invalid bounded World-JEPA shadow steps')
    store = closed.ReadOnlyStore(db_path)
    try:
        rows = world_model.transitions(store)
    finally:
        store.close()
    result = ablation.run_rows(rows, steps=steps)
    if (result.get('scope') != 'WORLD_JEPA_FIXED_READOUT_HELDOUT_ACTION_ABLATION'
            or result.get('readout_frozen_for_heldout_controls') is not True
            or result.get('utility_proven') is not False
            or result.get('runtime_wired') is not False):
        raise ValueError('Untrusted World-JEPA ablation report')
    return {
        **result,
        'schema': SCHEMA,
        'scope': 'CLOSED_STORE_FIXED_READOUT_DIGITAL_SHADOW',
        'data_source_kind': 'OPERATOR_ASSERTED_CLOSED_SQLITE',
        'source_digest_kind': 'CANONICAL_PARSED_TRANSITIONS_NOT_DB_BYTES',
        'store_bytes_independently_verified': False,
        'store_readonly': True,
        'training_partition_only': True,
        'heldout_actions_used_only_for_scoring': True,
        'raw_ids_exported': False,
        'model_weights_persisted': False,
        'native_executed': False,
        'phone_measured': False,
        'tool_authority': False,
        'age_authority': 0,
        'learning_gate_pass': False,
        'utility_proven': False,
        'whole_system_complete': False,
        'claim_limit': ('Digital action/outcome software SHADOW ablation only; '
                        'positive MAE deltas cannot establish JEPA causal utility'),
    }


def _unavailable():
    return {'schema': SCHEMA, 'status': 'UNAVAILABLE',
            'reason': 'CLOSED_STORE_OR_OPERATOR_ACK_INVALID',
            'runtime_wired': False, 'tool_authority': False,
            'age_authority': 0, 'utility_proven': False,
            'whole_system_complete': False}


def main(argv=None, stdout=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--ack-closed-store', action='store_true')
    parser.add_argument('--ack-shadow-fit', action='store_true')
    parser.add_argument('--steps', type=int, default=20)
    args = parser.parse_args(argv)
    out = sys.stdout if stdout is None else stdout
    if not (args.ack_closed_store and args.ack_shadow_fit):
        out.write(json.dumps(_unavailable(), sort_keys=True) + '\n')
        return 2
    try:
        report = run_db(args.db, steps=args.steps)
        rendered = json.dumps(report, sort_keys=True, allow_nan=False)
    except (ValueError, TypeError, OSError, OverflowError,
            sqlite3.Error, np.linalg.LinAlgError):
        out.write(json.dumps(_unavailable(), sort_keys=True) + '\n')
        return 2
    out.write(rendered + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
