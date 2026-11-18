"""Disjoint, read-only T8 online-learning utility audit.

This audit is NOT native JEPA, an Android benchmark, or permission to train
the live predictor. All fitting happens in temporary isolated model homes.
"""
import hashlib
import tempfile
import time
import tracemalloc
from .continuous_predictor import OnlinePredictor
from . import world_model


def benchmark(world, limit=512, min_holdout=4):
    """Measure before/after unseen T8 utility and replay ablation.

    Input is only world_model.transitions(), which admits committed T8 rows.
    A stable action-id hash defines the holdout; no holdout is ever observed.
    The production predictor and cursor are not read or mutated for training.
    """
    if type(limit) is not int or not 8 <= limit <= world_model.MAX_ROWS:
        raise ValueError('Invalid benchmark limit')
    rows = world_model.transitions(world.runtime.store, limit=limit)
    unique = {}
    for row in rows:
        key = row['action_id']
        if type(key) is not str or not key:
            raise ValueError('Invalid T8 action ID')
        if key in unique:
            raise ValueError('Duplicate T8 action ID')
        unique[key] = world.encode(row)
    # A hash partition, not a time-order or adjacent-row split.
    holdout = [v for k, v in unique.items()
               if int.from_bytes(hashlib.sha256(k.encode()).digest()[:8], 'big') % 5 == 0]
    train = [v for k, v in unique.items()
             if int.from_bytes(hashlib.sha256(k.encode()).digest()[:8], 'big') % 5 != 0]
    if len(holdout) < min_holdout or len(train) < 8:
        return {'status': 'INSUFFICIENT_DISJOINT_T8', 'train': len(train),
                'holdout': len(holdout), 'production_unchanged': True}
    results = {}
    tracemalloc.start()
    started = time.perf_counter()
    try:
        for label, rehearsals in (('replay_on', 2), ('replay_off', 0)):
            with tempfile.TemporaryDirectory(prefix='v13-t8-audit-') as home:
                model = OnlinePredictor(7, len(world_model.ACTIONS), home,
                                        lr=world.model.lr, replay=world.model.cap)
                before = model.error(holdout)
                old_anchor = train[:max(1, len(train)//4)]
                for x, action, y in train:
                    model.observe(x, action, y, rehearsals=rehearsals)
                after = model.error(holdout)
                anchor_after = model.error(old_anchor)
                model.checkpoint()
                restored = OnlinePredictor(7, len(world_model.ACTIONS), home,
                                           lr=world.model.lr, replay=world.model.cap)
                restart_error = restored.error(holdout)
                results[label] = {
                    'holdout_mse_before': before,
                    'holdout_mse_after': after,
                    'holdout_mse_delta': after-before,
                    'early_train_anchor_mse_after': anchor_after,
                    'restart_holdout_mse': restart_error,
                    'restart_exact': abs(after-restart_error) <= 1e-12,
                    'updates': model.updates,
                }
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return {'status': 'SYNTHETIC_OR_LOCAL_T8_AUDIT_NOT_ANDROID_PROOF',
            'train': len(train), 'holdout': len(holdout),
            'split': 'SHA256_ACTION_ID_MOD5', 'production_unchanged': True,
            'elapsed_seconds': time.perf_counter()-started,
            'python_peak_alloc_bytes': peak, 'results': results}
