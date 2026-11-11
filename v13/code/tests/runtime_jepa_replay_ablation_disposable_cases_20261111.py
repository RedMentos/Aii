"""Source-backed, synthetic Runtime T8 -> JEPA continual-learning replay ablation.

This test runs inside the existing exact-source disposable Runtime integration,
not a substitute production replay scheduler. No GGUF or body weights change.
"""
import copy
import json
import math

import numpy as np

from v13.runtime import Runtime
from v13 import world_model
from v13.world_jepa_action_outcome_adapter import build
from v13.world_jepa import WorldJEPA
from integrated_jepa_disposable_cases import populate


def test_runtime_jepa_replay_retention_and_budget(tmp_path):
    runtime = Runtime(tmp_path)
    try:
        populate(runtime)
        rows = world_model.transitions(runtime.store, limit=160)
        split = build(rows)
        old = tuple(np.asarray(v, dtype=np.float64) for v in split['train'])
        heldout = tuple(np.asarray(v, dtype=np.float64) for v in split['holdout'])
        train_ids = split['train_action_ids']
        holdout_ids = split['holdout_action_ids']
        assert not set(train_ids) & set(holdout_ids)
        assert len(train_ids) >= 16 and len(holdout_ids) >= 8

        # Split actual T8 training IDs into old/new phases; never train on holdout.
        # Fixed row positions avoid changing the train/holdout assignment.
        cut = len(train_ids) // 2
        a = tuple(v[:cut] for v in old)
        b = tuple(v[cut:] for v in old)
        assert cut >= 8 and len(b[0]) >= 8
        assert set(train_ids[:cut]).isdisjoint(train_ids[cut:])

        # Same initialization/old phase, equal optimizer step budgets in phase B.
        replay = WorldJEPA(seed=19, ensemble=2)
        fresh_only = WorldJEPA(seed=19, ensemble=2)
        replay.fit(*a, steps=12, log_every=12)
        fresh_only.fit(*a, steps=12, log_every=12)
        for key in replay.enc:
            assert np.array_equal(replay.enc[key], fresh_only.enc[key])

        before_old = replay.prediction_loss(*a)
        before_new = replay.prediction_loss(*b)
        before_holdout = replay.prediction_loss(*heldout)

        mixed = tuple(np.concatenate((left, right), axis=0) for left, right in zip(a, b))
        replay.partial_fit(*mixed, steps=12, log_every=12)
        fresh_only.partial_fit(*b, steps=12, log_every=12)
        assert replay._fit_steps == fresh_only._fit_steps == 24

        def measures(model):
            return {'old': model.prediction_loss(*a),
                    'new': model.prediction_loss(*b),
                    'holdout': model.prediction_loss(*heldout)}
        with_replay = measures(replay)
        no_replay = measures(fresh_only)
        assert all(math.isfinite(v) and v >= 0 for v in (*with_replay.values(), *no_replay.values()))
        assert any(not np.array_equal(replay.enc[k], fresh_only.enc[k]) for k in replay.enc)
        report = {
            'evidence': 'SYNTHETIC_RUNTIME_T8_DISJOINT_SHADOW',
            'train_rows': len(train_ids), 'holdout_rows': len(holdout_ids),
            'old_train_rows': cut, 'new_train_rows': len(b[0]),
            'steps_per_phase': 12, 'ensemble': 2,
            'before': {'old': before_old, 'new': before_new, 'holdout': before_holdout},
            'replay_on': with_replay, 'replay_off': no_replay,
            'old_forgetting_on': with_replay['old'] - before_old,
            'old_forgetting_off': no_replay['old'] - before_old,
            'holdout_delta_on': with_replay['holdout'] - before_holdout,
            'holdout_delta_off': no_replay['holdout'] - before_holdout,
            'replay_advantage_old': no_replay['old'] - with_replay['old'],
        }
        print('JEPA_REPLAY_RETENTION', json.dumps(report, sort_keys=True, allow_nan=False))
        # No cherry-picked positive gain requirement: negative controls must remain visible.
        # This test does not persist either experimental arm or enable live training.
    finally:
        runtime.close()
