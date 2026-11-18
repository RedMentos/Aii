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
        unique[key] = (row.get('event_id'), world.encode(row))
    # Mixed legacy and event-bound rows cannot safely be split as individual actions.
    has_event = [((type(event) is str and bool(event)) or (type(event) is int and event >= 0))
                 for event, _ in unique.values()]
    if any(has_event) and not all(has_event):
        raise ValueError('Mixed event-bound and legacy T8 rows: holdout would leak siblings')
    # Group all actions of the same event together to prevent sibling leakage.
    # Legacy synthetic rows without event_id are individually split and flagged.
    grouped = all((type(event) is str and bool(event)) or (type(event) is int and event >= 0)
                  for event, _ in unique.values())
    def bucket(action_id, event_id):
        source = str(event_id) if grouped else action_id
        return int.from_bytes(hashlib.sha256(source.encode()).digest()[:8], 'big') % 5
    holdout = [encoded for key, (event, encoded) in unique.items() if bucket(key, event) == 0]
    train = [encoded for key, (event, encoded) in unique.items() if bucket(key, event) != 0]
    if len(holdout) < min_holdout or len(train) < 8:
        return {'status': 'INSUFFICIENT_DISJOINT_T8', 'train': len(train),
                'holdout': len(holdout), 'production_unchanged': True}
    results = {}
    tracemalloc.start()
    started = time.perf_counter()
    try:
        for label, rehearsals in (('replay_on', 2), ('replay_off', 0),
                                  ('action_shift_control', 2)):
            with tempfile.TemporaryDirectory(prefix='v13-t8-audit-') as home:
                model = OnlinePredictor(7, len(world_model.ACTIONS), home,
                                        lr=world.model.lr, replay=world.model.cap)
                before = model.error(holdout)
                old_anchor = train[:max(1, len(train)//4)]
                anchor_before = model.error(old_anchor)
                for x, action, y in train:
                    fit_action = ((action + 1) % len(world_model.ACTIONS)\n                                  if label == 'action_shift_control' else action)\n                    model.observe(x, fit_action, y, rehearsals=rehearsals)
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
                    'early_train_anchor_mse_before': anchor_before,
                    'early_train_anchor_mse_after': anchor_after,
                    'early_train_anchor_mse_delta': anchor_after-anchor_before,
                    'holdout_improved': after < before,
                    'restart_holdout_mse': restart_error,
                    'restart_exact': abs(after-restart_error) <= 1e-12,
                    'updates': model.updates,
                }
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    results['replay_on']['action_specific_gain_vs_shift_control'] = (
        results['action_shift_control']['holdout_mse_after'] -
        results['replay_on']['holdout_mse_after'])
    return {'status': 'SYNTHETIC_OR_LOCAL_T8_AUDIT_NOT_ANDROID_PROOF',
            'train': len(train), 'holdout': len(holdout),
            'split': 'SHA256_EVENT_ID_MOD5' if grouped else 'SHA256_ACTION_ID_MOD5_LEGACY_UNGROUPED', 'production_unchanged': True,
            'elapsed_seconds': time.perf_counter()-started,
            'python_peak_alloc_bytes': peak, 'results': results}
