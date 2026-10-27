#!/usr/bin/env python3
"""Isolated real-file-world -> SlotWorldJEPA -> calibrated v2 checkpoint -> SHADOW probe.

Only main() performs file actions, inside a new temporary sandbox via Z12b's
independent world subprocess. export_from_rows() is a caller-data experiment,
not proof that those rows came from the real world. Neither path touches V13's
live models, tools, Age, facts, or registered Z12c cohorts.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import z12b_world_jepa as z12b
from scripts import z12c_slot_world_jepa as z12c
from v13.common import atomic_write
from v13.world_jepa_slots import SlotWorldJEPA, CHECKPOINT_REVISION
from v13.world_jepa_shadow_probe import probe_checkpoint

SCHEMA = 'V13_WORLD_SHADOW_LIFECYCLE_V1'
SOURCE_PATHS = (
    'v13/common.py',
    'v13/world_jepa.py',
    'v13/world_jepa_slots.py',
    'v13/world_jepa_shadow_probe.py',
    'scripts/z12b_world_jepa.py',
    'scripts/z12c_slot_world_jepa.py',
    'scripts/world_jepa_shadow_lifecycle.py',
)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def source_manifest():
    """Exact source-byte inventory, not a historical/assumed git ref."""
    files = []
    for name in SOURCE_PATHS:
        files.append({'path': name,
                      'sha256': hashlib.sha256((ROOT / name).read_bytes()).hexdigest()})
    return {'sha256': _digest(files), 'files': files}


def _checked_rows(rows):
    if type(rows) is not list or not 120 <= len(rows) <= 20000:
        raise ValueError('Requires 120..20000 ordered transitions')
    checked = []
    for r in rows:
        if type(r) is not dict or type(r.get('a')) is not int or not 0 <= r['a'] < len(z12b.ACTIONS):
            raise ValueError('Invalid source action index')
        if type(r.get('world')) is not bool or type(r.get('world_changed')) is not bool:
            raise ValueError('World overlap labels must be explicit booleans')
        x, x2 = np.asarray(r.get('x'), dtype=np.float64), np.asarray(r.get('x2'), dtype=np.float64)
        if (x.shape != (z12b.SLOTS * 10,) or x2.shape != x.shape
                or not np.isfinite(x).all() or not np.isfinite(x2).all()):
            raise ValueError('Invalid/nonfinite source transition features')
        checked.append({'x': x.tolist(), 'a': r['a'], 'x2': x2.tolist(),
                        'world': r['world'], 'world_changed': r['world_changed']})
    return checked


def _arrays(rows):
    X = np.array([r['x'] for r in rows], dtype=np.float64)
    A = np.array([z12c.slot_action(r['a']) for r in rows], dtype=np.float64)
    X2 = np.array([r['x2'] for r in rows], dtype=np.float64)
    return X, A, X2


def export_from_rows(rows, output_dir, seed, steps, collection='CALLER_SUPPLIED_UNVERIFIED'):
    """Train in memory, calibrate on later clean rows, then create a NEW output directory."""
    out = Path(output_dir)
    if out.exists():
        raise FileExistsError('Refuse to overwrite any existing World-JEPA export')
    if type(seed) is not int or seed < 0 or type(steps) is not int or not 1 <= steps <= 5000:
        raise ValueError('Invalid seed or bounded training steps')
    if collection not in ('CALLER_SUPPLIED_UNVERIFIED', 'LINUX_TEMP_FILE_WORLD_PROCESS'):
        raise ValueError('Unknown collection evidence level')
    data = _checked_rows(rows)
    split = len(data) - max(20, len(data)//5)
    train, val = data[:split], [r for r in data[split:] if not r['world']]
    if len(val) < 12:
        raise ValueError('Insufficient clean held-out transitions')
    X, A, X2 = _arrays(train)
    Xv, Av, X2v = _arrays(val)
    for name, a in (('train', A), ('calibration', Av)):
        counts = np.bincount(a.argmax(axis=2).ravel(), minlength=len(z12b.OPS)+1)
        if np.any(counts == 0):
            raise ValueError(name + ' lacks an observed operation class')
    source = source_manifest()
    cohort_sha = _digest(data)
    provenance = {'cohort_sha256': cohort_sha, 'source_sha256': source['sha256']}
    model = SlotWorldJEPA(z12b.SLOTS, seed=seed, ensemble=2).fit(
        X, A, X2, steps=steps, log_every=max(1, steps//4))
    model.calibrate(Xv, Av, X2v)
    # Training and calibration are finished before any output is created.
    out.mkdir(parents=True, exist_ok=False)
    checkpoint = out / 'slot-shadow-v2.npz'
    saved = model.save(checkpoint, provenance=provenance)
    request = {'before': Xv[0].reshape(z12b.SLOTS, 10).tolist(),
               'actions': Av[0].tolist(),
               'after': X2v[0].reshape(z12b.SLOTS, 10).tolist()}
    probe = probe_checkpoint(checkpoint, saved['sha256'], provenance, request)
    manifest = {
        'schema': SCHEMA, 'mode': 'SHADOW_ONLY', 'authority': 0,
        'collection': collection, 'seed': seed, 'steps': steps,
        'total_rows': len(data), 'train_rows': len(train),
        'calibration_rows': len(val),
        'world_overlapping_validation_excluded': len(data)-split-len(val),
        'source_sha256': source['sha256'], 'source_files': source['files'],
        'cohort_sha256': cohort_sha,
        'checkpoint_revision': CHECKPOINT_REVISION,
        'checkpoint_sha256': saved['sha256'], 'checkpoint_bytes': saved['bytes'],
        'calibration_operation_counts': np.bincount(Av.argmax(2).ravel(),
                                                    minlength=len(z12b.OPS)+1).tolist(),
        'probe_request_sha256': probe['request_sha256'],
        'probe_confidence': probe['confidence'],
        'probe_label': probe['simulation_label'],
        'redmi_measured': False, 'native_body_training': False,
        'runtime_authority': False,
        'claim_limit': 'Offline synthetic-content digital transitions; no causal/semantic utility or live decision rights',
    }
    # Preserve the exact canonical rows used for training/calibration so the
    # cohort digest can be recomputed independently from persisted bytes.
    atomic_write(out / 'cohort.json', _canonical(data))
    for name, obj in (('provenance.json', provenance), ('request.json', request),
                      ('probe.json', probe), ('manifest.json', manifest)):
        atomic_write(out / name, _canonical(obj) + b'\n')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description='Isolated World-JEPA real file-world SHADOW export')
    parser.add_argument('--seed', type=int, default=212)
    parser.add_argument('--train', type=int, default=600)
    parser.add_argument('--steps', type=int, default=50)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args(argv)
    if not 120 <= args.train <= 20000:
        raise ValueError('Bounded train row count required')
    with tempfile.TemporaryDirectory(prefix='v13-world-shadow-') as td:
        work = Path(td)
        rows = z12b.collect_train(work, args.seed, args.train, held=set())
        # Read originals BEFORE export; a missing process log must not leave a
        # seemingly valid checkpoint package with unverifiable collection.
        log_raw = (work / ('world-%d.log' % args.seed)).read_bytes()
        schedule_raw = (work / ('world-%d.json' % args.seed)).read_bytes()
        manifest = export_from_rows(
            rows, args.output_dir, seed=args.seed, steps=args.steps,
            collection='LINUX_TEMP_FILE_WORLD_PROCESS')
        out = Path(args.output_dir)
        atomic_write(out / ('world-%d.log' % args.seed), log_raw)
        atomic_write(out / ('world-%d.json' % args.seed), schedule_raw)
        manifest['world_process_log_sha256'] = hashlib.sha256(log_raw).hexdigest()
        manifest['world_process_schedule_sha256'] = hashlib.sha256(schedule_raw).hexdigest()
        manifest['world_process_log_events'] = sum(bool(line.strip()) for line in log_raw.splitlines())
        atomic_write(out / 'manifest.json', _canonical(manifest) + b'\n')
    print(json.dumps({'schema': manifest['schema'], 'mode': manifest['mode'],
                      'checkpoint_sha256': manifest['checkpoint_sha256'],
                      'cohort_sha256': manifest['cohort_sha256'],
                      'calibration_rows': manifest['calibration_rows'],
                      'claim_limit': manifest['claim_limit']}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
