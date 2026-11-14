"""Store-bound offline T8 learning evaluation; never activates Android training.

Only world_model.transitions(store) may supply labels. In particular callers
cannot provide arbitrary row dictionaries and claim trusted provenance.
"""
from . import world_model
from .online_world_evaluation import evaluate_disjoint
from .online_world_retention import evaluate_retention


def _admitted(store, limit):
    if store is None or not callable(getattr(store, "rows", None)):
        raise ValueError("A readable committed T8 Store is required")
    if type(limit) is not int or not 8 <= limit <= world_model.MAX_ROWS:
        raise ValueError("Invalid T8 read limit")
    rows = world_model.transitions(store, limit=limit)
    if len(rows) > limit:
        raise ValueError("T8 producer exceeded requested bound")
    ids = [r["action_id"] for r in rows]
    if any(type(i) is not str or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Invalid or repeated committed action ID")
    return rows


def evaluate_store_disjoint(store, *, limit=256, lr=0.02, replay=128):
    """Offline producer-bound split; no user-provided training labels."""
    rows = _admitted(store, limit)
    if len(rows) < 8:
        return {"status": "INSUFFICIENT_COMMITTED_T8", "count": len(rows)}
    # Stable nonperiodic split by action ID; no heldout label access.
    import hashlib
    held = [r for r in rows if int.from_bytes(hashlib.sha256(r["action_id"].encode()).digest()[:4], "big") % 4 == 0]
    train = [r for r in rows if r not in held]
    if not train or not held:
        return {"status": "INSUFFICIENT_DISJOINT_T8", "count": len(rows)}
    result = evaluate_disjoint(train, held, lr=lr, replay=replay)
    result["producer"] = "world_model.transitions"
    result["evidence"] = "OFFLINE_STORE_BOUND_NOT_ANDROID"
    return result


def evaluate_store_retention(store, *, limit=256, lr=0.02, replay=128):
    """Chronological old/new cohorts with independent holdouts.

    Input must come from the committed T8 producer; no arbitrary rows accepted.
    """
    rows = _admitted(store, limit)
    if len(rows) < 16:
        return {"status": "INSUFFICIENT_COMMITTED_T8", "count": len(rows)}
    mid = len(rows) // 2
    old, new = rows[:mid], rows[mid:]
    # Interleave within each chronological phase; holdouts never train.
    old_train, old_test = old[::2], old[1::2]
    new_train, new_test = new[::2], new[1::2]
    result = evaluate_retention(old_train, new_train, old_test, new_test, lr=lr, replay=replay)
    result["producer"] = "world_model.transitions"
    result["evidence"] = "OFFLINE_STORE_BOUND_NOT_ANDROID"
    return result
