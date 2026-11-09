"""Bounded replay and retention measurement for experimental World-JEPA.

No active runtime promotion or modification of pretrained GGUF weights.
Callers provide independently held-out old transitions; this module never trains
on those holdout rows. New/replay training rows are explicit, not silently mined.
"""
import numpy as np

MAX_ROWS = 4096
MAX_STEPS = 2000


def _transition(triple, label):
    if not isinstance(triple, (tuple, list)) or len(triple) != 3:
        raise ValueError(f"{label}: expected (observations, actions, next observations)")
    try:
        x, a, x2 = (np.asarray(v) for v in triple)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: invalid arrays") from exc
    if (any(v.ndim != 2 or v.dtype.kind not in "fiub" for v in (x, a, x2))
            or not 2 <= len(x) <= MAX_ROWS or a.shape[0] != len(x)
            or x.shape != x2.shape or not 1 <= x.shape[1] <= 4096
            or not 1 <= a.shape[1] <= 64
            or not all(np.isfinite(v).all() for v in (x, a, x2))):
        raise ValueError(f"{label}: invalid transition dimensions or values")
    return x, a, x2


def replay_update(model, new, replay, old_holdout, new_holdout, *,
                  steps=100, replay_fraction=0.25, seed=0):
    """Update weights on a deterministic bounded new/replay mixture.

    Report old and new held-out prediction error before and after. A negative
    delta is improvement. Retention evidence is observational, not authorization.
    """
    if (type(steps) is not int or not 1 <= steps <= MAX_STEPS
            or type(seed) is not int or not 0 <= seed < 2**63
            or type(replay_fraction) not in (float, int)
            or not np.isfinite(replay_fraction)
            or not 0 <= replay_fraction <= 1):
        raise ValueError("invalid replay budget")
    n = _transition(new, "new")
    r = _transition(replay, "replay")
    old = _transition(old_holdout, "old_holdout")
    fresh = _transition(new_holdout, "new_holdout")
    if not hasattr(model, "partial_fit") or not hasattr(model, "prediction_loss"):
        raise ValueError("a fitted incremental World-JEPA is required")
    dims = {(x.shape[1], a.shape[1]) for x, a, _ in (n, r, old, fresh)}
    if len(dims) != 1:
        raise ValueError("incompatible JEPA transition dimensions")
    rng = np.random.default_rng(seed)
    count = min(MAX_ROWS, len(n) + len(r))
    replay_count = min(len(r), round(count * replay_fraction))
    new_count = min(len(n), count - replay_count)
    if new_count < 2:
        raise ValueError("insufficient new transitions")
    replay_count = min(replay_count, count - new_count)
    ni = rng.choice(len(n), new_count, replace=False)
    ri = rng.choice(len(r), replay_count, replace=False)
    mixture = tuple(np.concatenate((n[k][ni], r[k][ri]), axis=0) for k in range(3))
    before_old = float(model.prediction_loss(*old))
    before_new = float(model.prediction_loss(*fresh))
    if not all(np.isfinite(v) for v in (before_old, before_new)):
        raise ValueError("nonfinite baseline retention")
    model.partial_fit(*mixture, steps=steps, log_every=max(1, steps // 4))
    after_old = float(model.prediction_loss(*old))
    after_new = float(model.prediction_loss(*fresh))
    if not all(np.isfinite(v) for v in (after_old, after_new)):
        raise ValueError("nonfinite post-update retention")
    return {"new_train_rows":new_count, "replay_train_rows":replay_count,
            "old_holdout_before":before_old, "old_holdout_after":after_old,
            "old_holdout_delta":after_old-before_old,
            "new_holdout_before":before_new, "new_holdout_after":after_new,
            "new_holdout_delta":after_new-before_new,
            "active_model_promoted":False, "pretrained_weights_changed":False}
