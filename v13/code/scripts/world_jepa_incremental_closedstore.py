"""Offline, read-only incremental World-JEPA outcome readout on a CLOSED V13 SQLite store.

Combines the unchanged train-only synthetic ablation (#764) with the closed-store
SELECT-only boundary (#758). Digital action outcomes are not physical world states.
No live hook, database/weight writes, raw ID export, tools or Age authority.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

import numpy as np
from scripts import world_jepa_incremental_probe as probe
from scripts import world_jepa_readonly_store as closed
from v13 import world_model as wm


def run_db(db_path, steps=probe.STEPS):
    """Read observed transitions once under a closed immutable SQLite snapshot."""
    store = closed.ReadOnlyStore(db_path)
    try:
        rows = wm.transitions(store)
    finally:
        store.close()
    report = probe.run_probe(rows, steps=steps)
    report['scope'] = 'OBSERVED_DIGITAL_INCREMENTAL_OUTCOME_SHADOW'
    report['evidence_level'] = 'CLOSED_STORE_DIGITAL_RESEARCH_ONLY_NO_UTILITY_PROOF'
    report['observed_store_readonly'] = True
    return report


def _unavailable():
    return {
        'status': 'UNAVAILABLE',
        'reason': 'CLOSED_STORE_INVALID_OR_INSUFFICIENT',
        'runtime_wired': False,
        'model_weights_persisted': False,
        'utility_proven': False,
        'age_authority': 0,
    }


def main(argv=None, stdout=None):
    parser = argparse.ArgumentParser(description='Read-only observed digital JEPA incremental readout')
    parser.add_argument('--db', required=True, type=Path)
    parser.add_argument('--ack-closed-store', action='store_true',
                        help='confirm V13 is stopped and SQLite has no live writer')
    args = parser.parse_args(argv)
    out = sys.stdout if stdout is None else stdout
    if not args.ack_closed_store:
        out.write(json.dumps(_unavailable(), sort_keys=True) + '\n')
        return 2
    try:
        report = run_db(args.db)
        rendered = json.dumps(report, sort_keys=True, allow_nan=False)
    except (ValueError, TypeError, OSError, sqlite3.Error, PermissionError,
            KeyError, OverflowError, np.linalg.LinAlgError):
        out.write(json.dumps(_unavailable(), sort_keys=True) + '\n')
        return 2
    out.write(rendered + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
