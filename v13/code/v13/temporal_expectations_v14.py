"""V14 temporal expectations over V13's trusted committed T8 transition feed.

Read-only consumer of world_model.transitions. Never treats absent telemetry as
a negative outcome. Persistent SQLite state is kept by the existing Store API.
This module does not modify GGUF, train JEPA or authorize Android actions.
"""
from __future__ import annotations

import math
from . import world_model

KEY = "V14_T8_TEMPORAL_EXPECTATIONS_V1"
REVISION = "v14-t8-temporal-v1"


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def observe(runtime, *, now_s, horizon_s=120.0, limit=2048):
    """Resolve pending expectations only when a trusted T8 outcome is present.

    The caller supplies monotonic-compatible wall-clock seconds. No automatic
    negative labels are created for missed deadlines: missing observations are
    censored until an independent observation-coverage proof exists.
    """
    if not _finite(now_s) or now_s < 0:
        raise ValueError("invalid clock")
    if not _finite(horizon_s) or not 0 < horizon_s <= 86400:
        raise ValueError("invalid horizon")
    if type(limit) is not int or not 1 <= limit <= world_model.MAX_ROWS:
        raise ValueError("invalid limit")
    store = runtime.store
    state = store.get_state(KEY) or {"revision": REVISION, "pending": {}, "resolved": {}}
    if state.get("revision") != REVISION:
        raise ValueError("incompatible expectation state")
    pending = dict(state["pending"])
    resolved = dict(state["resolved"])
    rows = world_model.transitions(store, limit=limit)
    observed = 0
    scored = 0
    for row in rows:
        action_id = row["action_id"]
        if not isinstance(action_id, str) or not action_id:
            continue
        if action_id in resolved or action_id not in pending:
            continue
        # A T8 row is already a committed, observed action/outcome pair.
        # It proves an outcome, not a counterfactual or a missed deadline.
        outcome = row["y"]
        hypothesis = pending[action_id]
        # Numeric diagnostic on committed T8 FINAL, never on missing observations.
        success = outcome[1] if isinstance(outcome, (list, tuple)) and len(outcome) == 3 else None
        brier = None
        if _finite(success) and success in (0, 1) and hypothesis["predicted_outcome"] in ("success", "failure"):
            label = success if hypothesis["predicted_outcome"] == "success" else 1 - success
            brier = round((hypothesis["probability"] - label) ** 2, 8)
            scored += 1
        resolved[action_id] = {
            "success_brier": brier,
            "success_label": success if brier is not None else None,
            "hypothesis_label": label if brier is not None else None,
            "status": "OBSERVED",
            "predicted_outcome": hypothesis["predicted_outcome"],
            "probability": hypothesis["probability"],
            "action": row["a"],
            "outcome": outcome,
            "evidence": {"kind": "T8_COMMITTED", "action_id": action_id},
        }
        pending.pop(action_id, None)
        observed += 1
    censored = 0
    for key, item in list(pending.items()):
        if now_s >= item["deadline"] and item["status"] == "PENDING":
            item = dict(item)
            item["status"] = "CENSORED"
            pending[key] = item
            censored += 1
    # Bound retained metadata; no raw chat or hidden T8 duplication.
    resolved = dict(list(resolved.items())[-world_model.MAX_ROWS:])
    if len(pending) > world_model.MAX_ROWS:
        raise ValueError("pending expectation capacity reached")
    store.set_state(KEY, {"revision": REVISION, "pending": pending, "resolved": resolved})
    return {"status": "OBSERVATION_ONLY", "observed": observed,
            "censored": censored, "scored": scored, "pending": len(pending), "resolved": len(resolved),
            "omission_learning": "OFF_NO_COVERAGE_PROOF"}


def expect(runtime, *, expectation_id, condition_source, predicted_outcome,
           now_s, deadline_s, probability):
    """Record an explicit source-linked hypothesis, not an observed fact."""
    if not all(isinstance(x, str) and x for x in
               (expectation_id, condition_source, predicted_outcome)):
        raise ValueError("missing source or hypothesis")
    if not all(_finite(x) for x in (now_s, deadline_s, probability)):
        raise ValueError("invalid numeric expectation")
    if not (0 <= now_s < deadline_s <= now_s + 86400 and 0 <= probability <= 1):
        raise ValueError("invalid expectation window/probability")
    store = runtime.store
    state = store.get_state(KEY) or {"revision": REVISION, "pending": {}, "resolved": {}}
    if state.get("revision") != REVISION:
        raise ValueError("incompatible expectation state")
    if expectation_id in state["pending"] or expectation_id in state["resolved"]:
        raise ValueError("duplicate expectation id")
    if len(state["pending"]) >= world_model.MAX_ROWS:
        raise ValueError("pending expectation capacity reached")
    # Expectation IDs are committed T8 action IDs; unbound hypotheses cannot
    # be resolved by unrelated observations.
    state["pending"][expectation_id] = {
        "condition_source": condition_source, "predicted_outcome": predicted_outcome,
        "created": now_s, "deadline": deadline_s,
        "probability": probability, "status": "PENDING",
    }
    store.set_state(KEY, state)
    return {"status": "PENDING", "id": expectation_id}


def score_snapshot(runtime):
    """Read-only, restart-stable Brier summary for committed binary T8 labels.

    Descriptive in-sample calibration only; not a disjoint holdout, optimizer,
    causal learning, JEPA utility, or evidence of Android performance.
    """
    state = runtime.store.get_state(KEY) or {"revision": REVISION, "resolved": {}}
    if state.get("revision") != REVISION:
        raise ValueError("incompatible expectation state")
    scores = [row.get("success_brier") for row in state["resolved"].values()
              if type(row) is dict and _finite(row.get("success_brier"))
              and 0 <= row["success_brier"] <= 1]
    return {"status": "IN_SAMPLE_ONLY", "scored": len(scores),
            "mean_brier": round(sum(scores) / len(scores), 8) if scores else None,
            "heldout_utility": "UNVERIFIED", "weights_updated": False}
