"""Persistent Store-backed JEPA consumer for verified V13 T8 action outcomes.

This is a trainable numeric WorldJEPA + role-specific B1/B2 readout candidate.
It is not a native LLM/GGUF weight editor. SleepRuntime calls the persistent
consumer after committed T8 outcomes; WorldPlanner then reads the persisted
B1/B2/SELF heads in SHADOW. The Store pointer binds checkpoint, receipt cursor,
replay memory and receiver heads atomically.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import uuid

import numpy as np
from v13.common import dumps, now
from v13.contracts import packet

from v13 import world_jepa
from v13 import world_jepa_replay
from v13 import world_jepa_drift
from v13 import world_jepa_shadow_checkpoint
from v13 import world_model
from .world_jepa_store_authority import verify_committed_transition_page


REVISION = "v14-world-jepa-store-consumer-v3"
LEGACY_REVISION = "v14-world-jepa-store-consumer-v2"
STATE_KEY = "v14.world_jepa.store_consumer"
STATE_SCHEMA = 3
NEUROMOD_CURSOR_KEY = "v14.world_jepa.neuromod_cursor"
NEUROMOD_CURSOR_REVISION = 1
LEGACY_STATE_SCHEMA = 2
MAX_ROWS = min(2048, world_model.MAX_ROWS)
DEFAULT_PAGE_SIZE = MAX_ROWS
MAX_TRACKED = 10000
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
CHECKPOINT_NAME = re.compile(r"jepa-[0-9a-f]{32}\.npz\Z")
ROLE_TARGETS = {
    "B1_DETAIL": (0, 2),
    "B2_GIST": (1,),
    "SELF_MODEL": (0, 1, 2),
}


def _finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _vector(value, size):
    if (type(value) not in (list, tuple) or len(value) != size
            or any(not _finite_number(item) for item in value)):
        raise ValueError("invalid finite numeric vector")
    return [float(item) for item in value]


def _sha(value):
    if type(value) is not str or not SHA256.fullmatch(value):
        raise ValueError("invalid SHA256")
    return value


def _receipt_row(receipt):
    if type(receipt.action_id) is not str or not receipt.action_id or len(receipt.action_id) > 128:
        raise ValueError("invalid verified action id")
    raw = receipt.training_row()
    proof = receipt.public_provenance()
    route = raw.get("a")
    if route not in world_model.ACTIONS:
        raise ValueError("unknown verified action route")
    source_id = proof.get("source_id")
    if type(source_id) is not str or not source_id or len(source_id) > 256:
        raise ValueError("invalid verified source id")
    session_id = receipt.session_id
    if type(session_id) is not str or not session_id or len(session_id) > 128:
        raise ValueError("invalid verified session id")
    return {
        "action_id": receipt.action_id,
        "source_id": source_id,
        "session_id": session_id,
        "fingerprint": _sha(receipt.fingerprint),
        "source_sha256": _sha(proof.get("source_sha256")),
        "outcome_sha256": _sha(proof.get("outcome_sha256")),
        "created": float(receipt.created),
        "s": _vector(raw.get("s"), 4),
        "a": route,
        "y": _vector(raw.get("y"), 3),
    }


def _cohort_sha(rows):
    body = [
        {"action_id": row["action_id"], "source_id": row["source_id"],
         "source_sha256": row["source_sha256"], "fingerprint": row["fingerprint"],
         "session_id": row.get("session_id")}
        for row in sorted(rows, key=lambda item: item["action_id"])
    ]
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _arrays(rows):
    x = np.asarray([row["s"] + [0.0, 0.0, 0.0] for row in rows], dtype=np.float64)
    a = np.asarray([world_model.onehot(row["a"]) for row in rows], dtype=np.float64)
    x2 = np.asarray([row["s"] + row["y"] for row in rows], dtype=np.float64)
    if (x.ndim != 2 or a.ndim != 2 or x2.shape != x.shape
            or not all(np.isfinite(value).all() for value in (x, a, x2))):
        raise ValueError("invalid replay arrays")

    return x, a, x2


def _source_disjoint_split(rows):
    """Deterministic holdout split by source identity, never by action ID."""
    if type(rows) not in (list, tuple) or not 16 <= len(rows) <= MAX_ROWS:
        raise ValueError("invalid source-disjoint cohort size")
    canonical, seen_actions, source_hashes = [], set(), {}
    for item in rows:
        if type(item) is not dict:
            raise ValueError("invalid source-disjoint row")
        action_id, source_id = item.get("action_id"), item.get("source_id")
        source_sha, route = _sha(item.get("source_sha256")), item.get("a")
        if (type(action_id) is not str or not action_id or len(action_id) > 128
                or action_id in seen_actions or type(source_id) is not str
                or not source_id or len(source_id) > 256 or route not in world_model.ACTIONS):
            raise ValueError("invalid source-disjoint identity")
        prior_sha = source_hashes.get(source_id)
        if prior_sha is not None and prior_sha != source_sha:
            raise ValueError("source identity changed digest")
        source_hashes[source_id] = source_sha
        seen_actions.add(action_id)
        canonical.append({
            "action_id": action_id, "source_id": source_id,
            "source_sha256": source_sha, "fingerprint": _sha(item.get("fingerprint")),
            "outcome_sha256": _sha(item.get("outcome_sha256")),
            "created": float(item["created"]), "s": _vector(item.get("s"), 4),
            "a": route, "y": _vector(item.get("y"), 3),
        })
    canonical.sort(key=lambda item: item["action_id"])
    # Group by the content digest as well as source_id. Two different event/source
    # IDs can point to byte-identical source content; those must never straddle
    # train and holdout. The earlier source_id-only split leaked this case.
    def partition(source_sha256):
        digest = bytes.fromhex(source_sha256)
        return int.from_bytes(digest[:8], "big") % 2
    train = [row for row in canonical if partition(row["source_sha256"]) == 0]
    holdout = [row for row in canonical if partition(row["source_sha256"]) == 1]
    train_sources = {row["source_id"] for row in train}
    holdout_sources = {row["source_id"] for row in holdout}
    train_source_hashes = {row["source_sha256"] for row in train}
    holdout_source_hashes = {row["source_sha256"] for row in holdout}
    if train_sources & holdout_sources:
        raise ValueError("source leakage across holdout")
    if train_source_hashes & holdout_source_hashes:
        raise ValueError("source digest leakage across holdout")
    if len(train) < 8 or len(holdout) < 8:
        raise ValueError("insufficient source-disjoint split rows")
    if (len({row["a"] for row in train}) < 2 or len({row["a"] for row in holdout}) < 2
            or not {row["a"] for row in holdout}.issubset({row["a"] for row in train})):
        raise ValueError("insufficient source-disjoint action support")
    def content_digest(row):
        raw = json.dumps({"s": row["s"], "a": row["a"], "y": row["y"]},
                         sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
    if ({content_digest(row) for row in train} & {content_digest(row) for row in holdout}):
        raise ValueError("identical content crossed source holdout")
    train_ids = tuple(row["action_id"] for row in train)
    holdout_ids = tuple(row["action_id"] for row in holdout)
    return {
        "train": _arrays(train), "holdout": _arrays(holdout),
        "train_action_ids": train_ids, "holdout_action_ids": holdout_ids,
        "manifest": {
            "source_disjoint": True, "source_sha256_disjoint": True,
            "train_source_count": len(train_sources),
            "holdout_source_count": len(holdout_sources),
            "within_supplied_records_id_disjoint": True,
            "within_supplied_records_content_disjoint": True,
            "train_rows_sha256": _cohort_sha(train), "holdout_rows_sha256": _cohort_sha(holdout),
        },
    }


MAX_RETENTION_COHORTS = 64


def _retention_cohorts(rows):
    """Stable, privacy-preserving session cohorts from the prior holdout fold."""
    grouped = {}
    for row in rows:
        session_id = row.get("session_id")
        if type(session_id) is str and session_id:
            key = "session:" + hashlib.sha256(session_id.encode("utf-8")).hexdigest()
        else:
            key = "legacy:ungrouped"
        grouped.setdefault(key, []).append(row)
    if len(grouped) > MAX_RETENTION_COHORTS:
        return None
    return tuple(
        (key, tuple(sorted(values, key=lambda item: item["action_id"])))
        for key, values in sorted(grouped.items())
    )


def _target_snapshot_sha256(target_snapshot):
    if target_snapshot is None:
        return None
    digest = hashlib.sha256()
    for key in sorted(target_snapshot):
        value = np.ascontiguousarray(target_snapshot[key], dtype=np.float64)
        digest.update(key.encode("utf-8") + b"\0")
        digest.update(json.dumps(list(value.shape), separators=(",", ":")).encode("utf-8"))
        digest.update(b"\0")
        digest.update(value.tobytes())
    return digest.hexdigest()


def _retention_cohort_losses(model, cohorts, *, target_snapshot=None):
    result = {}
    for key, rows in cohorts or ():
        loss = float(model.prediction_loss(
            *_arrays(list(rows)), target_snapshot=target_snapshot
        ))
        if not math.isfinite(loss) or loss < 0.0:
            raise ValueError("invalid per-session WorldJEPA retention loss")
        result[key] = {"rows": len(rows), "loss": loss}
    return result


def _source_disjoint_guard_split(rows, *, salt):
    """Split a training fold into disjoint fit/guard source groups.

    Guard rows are never used for gradients. They may select replay cohorts and
    bounded update scales; the independent source-disjoint holdout remains the
    final promotion gate. Source, source-digest and identical-content groups
    are kept together so no duplicate crosses the fit/guard boundary.
    """
    if (type(rows) not in (list, tuple) or len(rows) < 8
            or type(salt) is not str or not salt or len(salt) > 512):
        return None

    parent = {}

    def find(key):
        parent.setdefault(key, key)
        if parent[key] != key:
            parent[key] = find(parent[key])
        return parent[key]

    def union(left, right):
        left_root, right_root = find(left), find(right)
        if left_root == right_root:
            return
        if left_root < right_root:
            parent[right_root] = left_root
        else:
            parent[left_root] = right_root

    grouped_rows = []
    for row in rows:
        if type(row) is not dict:
            return None
        source_id = row.get("source_id")
        source_sha = row.get("source_sha256")
        action_id = row.get("action_id")
        if (type(source_id) is not str or not source_id
                or type(action_id) is not str or not action_id):
            return None
        try:
            _sha(source_sha)
            content_payload = json.dumps(
                {"s": row["s"], "a": row["a"], "y": row["y"]},
                sort_keys=True, separators=(",", ":"), allow_nan=False,
            )
        except (KeyError, TypeError, ValueError):
            return None
        content_sha = hashlib.sha256(content_payload.encode("utf-8")).hexdigest()
        source_key = "source:" + source_sha
        content_key = "content:" + content_sha
        identity_key = "identity:" + hashlib.sha256(source_id.encode("utf-8")).hexdigest()
        union(source_key, content_key)
        union(source_key, identity_key)
        session_id = row.get("session_id")
        if type(session_id) is not str or not session_id:
            session_id = "legacy:" + source_id
        grouped_rows.append((row, source_key, session_id, source_sha, content_sha))

    roots = sorted({find(item[1]) for item in grouped_rows})
    if len(roots) < 4:
        return None
    ranked_roots = sorted(
        roots,
        key=lambda root: hashlib.sha256(
            (salt + "\0guard\0" + root).encode("utf-8")
        ).digest(),
    )
    guard_group_count = max(1, len(ranked_roots) // 4)
    guard_group_count = min(guard_group_count, len(ranked_roots) - 2)
    guard_roots = set(ranked_roots[:guard_group_count])

    fit_rows, guard_rows = [], []
    session_counts = {}
    for row, source_key, session_id, _source_sha, _content_sha in grouped_rows:
        is_guard = find(source_key) in guard_roots
        (guard_rows if is_guard else fit_rows).append(row)
        counts = session_counts.setdefault(session_id, {"fit": 0, "guard": 0})
        counts["guard" if is_guard else "fit"] += 1

    if len(fit_rows) < 2 or len(guard_rows) < 2:
        return None
    if any(counts["fit"] < 2 or counts["guard"] < 2
           for counts in session_counts.values()):
        return None

    fit_source_ids = {row["source_id"] for row in fit_rows}
    guard_source_ids = {row["source_id"] for row in guard_rows}
    fit_source_hashes = {row["source_sha256"] for row in fit_rows}
    guard_source_hashes = {row["source_sha256"] for row in guard_rows}
    fit_content_hashes = {
        hashlib.sha256(json.dumps(
            {"s": row["s"], "a": row["a"], "y": row["y"]},
            sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")).hexdigest()
        for row in fit_rows
    }
    guard_content_hashes = {
        hashlib.sha256(json.dumps(
            {"s": row["s"], "a": row["a"], "y": row["y"]},
            sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")).hexdigest()
        for row in guard_rows
    }
    source_disjoint = not (
        fit_source_ids & guard_source_ids
        or fit_source_hashes & guard_source_hashes
    )
    content_disjoint = not (fit_content_hashes & guard_content_hashes)
    if not source_disjoint or not content_disjoint:
        return None

    def digest_ids(items):
        return hashlib.sha256(
            "\n".join(sorted(row["action_id"] for row in items)).encode("utf-8")
        ).hexdigest()

    manifest_payload = {
        "salt_sha256": hashlib.sha256(salt.encode("utf-8")).hexdigest(),
        "fit_action_ids_sha256": digest_ids(fit_rows),
        "guard_action_ids_sha256": digest_ids(guard_rows),
        "fit_source_group_count": len(roots) - len(guard_roots),
        "guard_source_group_count": len(guard_roots),
        "fit_rows": len(fit_rows),
        "guard_rows": len(guard_rows),
    }
    manifest = {
        **manifest_payload,
        "session_count": len(session_counts),
        "source_disjoint": source_disjoint,
        "content_disjoint": content_disjoint,
        "manifest_sha256": hashlib.sha256(json.dumps(
            manifest_payload, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")).hexdigest(),
    }
    return {"fit_rows": fit_rows, "guard_rows": guard_rows, "manifest": manifest}


# Explicit per-update retention budget: bounded plasticity is allowed, but
# large session regressions still reject promotion. This is not a cumulative
# forgetting guarantee; accepted-checkpoint anchor baselines are the next gate.
RETENTION_RELATIVE_TOLERANCE = 0.01


def _retention_cohort_gate(before, after, *, overflow=False):
    if overflow:
        return {
            "accepted": False,
            "reason": "RETENTION_COHORT_LIMIT_EXCEEDED",
            "max_cohorts": MAX_RETENTION_COHORTS,
            "cohorts": {},
        }
    if not before:
        return {"accepted": True, "reason": "NO_PRIOR_HOLDOUT", "cohorts": {}}
    if set(before) != set(after):
        return {"accepted": False, "reason": "RETENTION_COHORT_SET_MISMATCH", "cohorts": {}}
    checks = {}
    for key, prior in before.items():
        current = after[key]
        if int(prior["rows"]) != int(current["rows"]):
            return {"accepted": False, "reason": "RETENTION_COHORT_ROW_MISMATCH", "cohorts": {}}
        loss_before = float(prior["loss"])
        loss_after = float(current["loss"])
        tolerance = max(1e-12, abs(loss_before) * RETENTION_RELATIVE_TOLERANCE)
        checks[key] = {
            "rows": int(prior["rows"]),
            "loss_before": loss_before,
            "loss_after": loss_after,
            "delta": loss_after - loss_before,
            "tolerance": tolerance,
            "retained": loss_after <= loss_before + tolerance,
        }
    accepted = all(item["retained"] for item in checks.values())
    return {
        "accepted": accepted,
        "reason": "ALL_PRIOR_SESSIONS_RETAINED" if accepted else "SESSION_RETENTION_REGRESSED",
        "cohorts": checks,
    }

MAX_CONFLICT_PROBES = 32
MAX_CONFLICT_SAMPLE_ROWS = 64


def _gradient_vector(model, rows, *, train_encoder, salt):
    sampled = sorted(
        rows,
        key=lambda row: hashlib.sha256(
            (salt + "\0" + row["action_id"]).encode("utf-8")
        ).digest(),
    )[:MAX_CONFLICT_SAMPLE_ROWS]
    if len(sampled) < 2:
        return None
    x, actions, x2 = _arrays(sampled)
    x = (x - model.mu) / model.sd
    x2 = (x2 - model.mu) / model.sd
    target = world_jepa.encode(model.tgt, x2)[0]
    out = world_jepa.loss_grads(
        model.enc, model.preds[0], x, actions, target,
        world_jepa.VAR_W, world_jepa.COV_W, train_enc=train_encoder,
    )
    predictor_gradients = out[2]
    encoder_gradients = out[3]
    pieces = []
    if encoder_gradients is not None:
        pieces.extend(
            np.asarray(encoder_gradients[key], dtype=np.float64).reshape(-1)
            for key in sorted(encoder_gradients)
        )
    pieces.extend(
        np.asarray(predictor_gradients[key], dtype=np.float64).reshape(-1)
        for key in sorted(predictor_gradients)
    )
    vector = np.concatenate(pieces)
    if vector.size == 0 or not np.isfinite(vector).all():
        raise ValueError("invalid WorldJEPA replay-conflict gradient")
    return vector


def _session_gradient_conflict_scores(model, new_rows, old_rows, *, train_encoder, salt):
    """Bounded prior-guard-fold estimate of signed interference by old session."""
    grouped = {}
    for row in old_rows:
        session_id = row.get("session_id")
        if type(session_id) is str and session_id:
            grouped.setdefault(session_id, []).append(row)
    eligible = {
        session_id: values for session_id, values in grouped.items() if len(values) >= 2
    }
    ranked = sorted(
        eligible,
        key=lambda session_id: hashlib.sha256(
            (salt + "\0probe\0" + session_id).encode("utf-8")
        ).digest(),
    )
    scored = ranked[:MAX_CONFLICT_PROBES]
    new_gradient = _gradient_vector(
        model, new_rows, train_encoder=train_encoder, salt=salt + ":new"
    )
    new_norm = float(np.linalg.norm(new_gradient))
    scores = {}
    probe_rows = min(len(new_rows), MAX_CONFLICT_SAMPLE_ROWS)
    for session_id in scored:
        rows = eligible[session_id]
        old_gradient = _gradient_vector(
            model, rows, train_encoder=train_encoder, salt=salt + ":" + session_id
        )
        old_norm = float(np.linalg.norm(old_gradient))
        probe_rows += min(len(rows), MAX_CONFLICT_SAMPLE_ROWS)
        if new_norm <= 1e-20 or old_norm <= 1e-20:
            conflict = 0.0
        else:
            cosine = float(np.dot(new_gradient, old_gradient) / (new_norm * old_norm))
            conflict = max(0.0, min(1.0, -cosine))
        scores[session_id] = conflict
    return {
        "scores": scores,
        "scored_session_count": len(scores),
        "unscored_session_count": len(grouped) - len(scores),
        "legacy_rows_excluded": sum(1 for row in old_rows if not row.get("session_id")),
        "probe_rows": probe_rows,
    }


def _session_loss_demand_scores(model, new_rows, old_rows, *, train_encoder, salt,
                                 steps, cancel_check=None):
    """Estimate replay demand from a short disposable no-replay update.

    Only prior source-disjoint training-fold rows are scored. The reference is
    the active checkpoint before the probe; holdout rows never enter selection.
    No adaptation-specialist reference exists here, so no adaptation score is
    invented. The probe model is discarded and never persisted.
    """
    target_anchor = {
        key: np.asarray(value).copy() for key, value in model.tgt.items()
    }
    grouped = {}
    for row in old_rows:
        session_id = row.get("session_id")
        if type(session_id) is str and session_id:
            grouped.setdefault(session_id, []).append(row)
    eligible = {
        session_id: values for session_id, values in grouped.items()
        if len(values) >= 2
    }
    ranked = sorted(
        eligible,
        key=lambda session_id: hashlib.sha256(
            (salt + "\0loss-probe\0" + session_id).encode("utf-8")
        ).digest(),
    )
    scored = ranked[:MAX_CONFLICT_PROBES]
    samples = {}
    before_losses = {}
    probe_rows = 0
    for session_id in scored:
        sampled = sorted(
            eligible[session_id],
            key=lambda row: hashlib.sha256(
                (salt + "\0" + session_id + "\0" + row["action_id"]).encode("utf-8")
            ).digest(),
        )[:MAX_CONFLICT_SAMPLE_ROWS]
        if len(sampled) < 2:
            continue
        loss_before = float(model.prediction_loss(
            *_arrays(sampled), target_snapshot=target_anchor
        ))
        if not math.isfinite(loss_before) or loss_before < 0.0:
            raise ValueError("invalid pre-probe WorldJEPA cohort loss")
        samples[session_id] = sampled
        before_losses[session_id] = loss_before
        probe_rows += len(sampled)

    probe_steps = min(8, max(1, steps // 8)) if samples and len(new_rows) >= 2 else 0
    if probe_steps:
        model.partial_fit(
            *_arrays(new_rows), steps=probe_steps,
            log_every=max(1, probe_steps), cancel_check=cancel_check,
            allow_optimizer_bootstrap=True, train_encoder=train_encoder,
            update_scale=1.0,
        )
        probe_rows += len(new_rows)

    scores = {}
    for session_id, sampled in samples.items():
        loss_after = float(model.prediction_loss(
            *_arrays(sampled), target_snapshot=target_anchor
        ))
        if not math.isfinite(loss_after) or loss_after < 0.0:
            raise ValueError("invalid post-probe WorldJEPA cohort loss")
        loss_before = before_losses[session_id]
        relative_growth = max(0.0, loss_after - loss_before) / max(loss_before, 1e-8)
        scores[session_id] = min(1e6, float(relative_growth))

    return {
        "scores": scores,
        "scored_session_count": len(scores),
        "unscored_session_count": len(grouped) - len(scores),
        "legacy_rows_excluded": sum(1 for row in old_rows if not row.get("session_id")),
        "probe_rows": probe_rows,
        "probe_steps": probe_steps,
    }


def _ordered_replay_rows_and_ranges(rows, replay_start):
    """Group selected replay rows into bounded contiguous per-session GEM ranges."""
    grouped = {}
    for row in rows:
        session_id = row.get("session_id")
        if type(session_id) is not str or not session_id:
            return None
        key = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
        grouped.setdefault(key, []).append(row)
    if not grouped or len(grouped) > world_jepa.MAX_REPLAY_CONSTRAINTS:
        return None
    ordered, ranges, session_keys = [], [], []
    cursor = replay_start
    for key, values in sorted(grouped.items()):
        values = sorted(values, key=lambda row: (float(row["created"]), row["action_id"]))
        if len(values) < 2:
            return None
        start = cursor
        ordered.extend(values)
        cursor += len(values)
        ranges.append((start, cursor))
        session_keys.append(key[:16])
    if cursor != replay_start + len(rows):
        raise ValueError("WorldJEPA replay cohort ranges do not cover selected rows")
    return ordered, tuple(ranges), tuple(session_keys)



def _parameter_snapshot(model):

    return {
        "enc": {key: np.asarray(value).copy() for key, value in model.enc.items()},
        "tgt": {key: np.asarray(value).copy() for key, value in model.tgt.items()},
        "preds": [
            {key: np.asarray(value).copy() for key, value in predictor.items()}
            for predictor in model.preds
        ],
    }


def _apply_parameter_interpolation(model, before, after, scale):
    if (type(scale) not in (int, float) or not np.isfinite(scale)
            or not 0.0 < float(scale) <= 1.0):
        raise ValueError("invalid WorldJEPA parameter interpolation scale")
    for group in ("enc", "tgt"):
        current = getattr(model, group)
        left, right = before[group], after[group]
        if set(current) != set(left) or set(current) != set(right):
            raise ValueError("parameter interpolation fields changed")
        for key, target in current.items():
            start = np.asarray(left[key])
            end = np.asarray(right[key])
            destination = np.asarray(target)
            if start.shape != end.shape or start.shape != destination.shape:
                raise ValueError("parameter interpolation shape changed")
            np.copyto(destination, start + (end - start) * float(scale))
    if len(model.preds) != len(before["preds"]) or len(model.preds) != len(after["preds"]):
        raise ValueError("parameter interpolation ensemble changed")
    for index, predictor in enumerate(model.preds):
        left, right = before["preds"][index], after["preds"][index]
        if set(predictor) != set(left) or set(predictor) != set(right):
            raise ValueError("parameter interpolation predictor fields changed")
        for key, target in predictor.items():
            start = np.asarray(left[key])
            end = np.asarray(right[key])
            destination = np.asarray(target)
            if start.shape != end.shape or start.shape != destination.shape:
                raise ValueError("parameter interpolation predictor shape changed")
            np.copyto(destination, start + (end - start) * float(scale))


def _group_delta(before, after, groups):
    total = 0.0
    for group in groups:
        left_group, right_group = before[group], after[group]
        if group == "preds":
            if len(left_group) != len(right_group):
                raise ValueError("parameter ensemble mismatch")
            pairs = []
            for left_pred, right_pred in zip(left_group, right_group):
                if set(left_pred) != set(right_pred):
                    raise ValueError("parameter snapshot mismatch")
                pairs.extend((left_pred[key], right_pred[key]) for key in left_pred)
        else:
            if set(left_group) != set(right_group):
                raise ValueError("parameter snapshot mismatch")
            pairs = [(left_group[key], right_group[key]) for key in left_group]
        for left, right in pairs:
            if left.shape != right.shape:
                raise ValueError("parameter shape changed")
            total += float(np.square(right - left).sum())
    return math.sqrt(total)


def _ridge_head(z_train, y_train, ridge=1e-3):
    z = np.asarray(z_train, dtype=np.float64)
    y = np.asarray(y_train, dtype=np.float64)
    if y.ndim == 1:
        y = y[:, None]
    if (z.ndim != 2 or y.ndim != 2 or len(z) != len(y) or len(z) < 2
            or not np.isfinite(z).all() or not np.isfinite(y).all()):
        raise ValueError("invalid role receiver training data")
    design = np.column_stack((z, np.ones(len(z), dtype=np.float64)))
    penalty = np.eye(design.shape[1], dtype=np.float64) * ridge
    penalty[-1, -1] = 0.0
    solution = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    weights, bias = solution[:-1], solution[-1]
    if not np.isfinite(weights).all() or not np.isfinite(bias).all():
        raise ValueError("nonfinite role receiver")
    return weights, bias


def _mse(prediction, target):
    value = float(np.mean(np.square(np.asarray(prediction) - np.asarray(target))))
    if not math.isfinite(value):
        raise ValueError("nonfinite receiver metric")
    return value


def receiver_utility_gate(metrics, role):
    """Require each numeric role receiver to beat its mean and latent-negative controls."""
    if role not in ROLE_TARGETS or type(metrics) is not dict:
        return {"accepted": False, "reason": "RECEIVER_METRICS_UNAVAILABLE"}
    prefix = role.lower()
    keys = (
        prefix + "_holdout_mse",
        prefix + "_mean_baseline_mse",
        prefix + "_zero_latent_mse",
        prefix + "_shuffled_latent_mse",
    )
    values = [metrics.get(key) for key in keys]
    if any(not _finite_number(value) or value < 0 for value in values):
        return {"accepted": False, "reason": "RECEIVER_METRICS_INVALID"}
    holdout, mean_baseline, zero_latent, shuffled_latent = map(float, values)
    margin = max(1e-12, max(abs(value) for value in values) * 1e-9)
    accepted = all(
        holdout + margin < baseline
        for baseline in (mean_baseline, zero_latent, shuffled_latent)
    )
    if not accepted:
        return {
            "accepted": False,
            "reason": "HELDOUT_DID_NOT_BEAT_ALL_CONTROLS",
            "holdout_mse": holdout,
            "mean_baseline_mse": mean_baseline,
            "zero_latent_mse": zero_latent,
            "shuffled_latent_mse": shuffled_latent,
            "required_margin": float(margin),
        }
    retention = metrics.get(prefix + "_old_session_retention_gate")
    if type(retention) is not dict:
        return {
            "accepted": False,
            "reason": "RECEIVER_RETENTION_NOT_MEASURED",
            "holdout_mse": holdout,
            "mean_baseline_mse": mean_baseline,
            "zero_latent_mse": zero_latent,
            "shuffled_latent_mse": shuffled_latent,
        }
    if retention.get("accepted") is not True:
        return {
            "accepted": False,
            "reason": "OLD_SESSION_RECEIVER_RETENTION_REJECTED",
            "holdout_mse": holdout,
            "mean_baseline_mse": mean_baseline,
            "zero_latent_mse": zero_latent,
            "shuffled_latent_mse": shuffled_latent,
            "old_session_retention_gate": retention,
        }
    return {
        "accepted": True,
        "reason": "HELDOUT_BEATS_MEAN_AND_NEGATIVE_CONTROLS",
        "holdout_mse": holdout,
        "mean_baseline_mse": mean_baseline,
        "zero_latent_mse": zero_latent,
        "shuffled_latent_mse": shuffled_latent,
        "required_margin": float(margin),
        "old_session_retention_gate": retention,
    }


def _fit_role_receivers(model, train, holdout, train_rows, holdout_rows):
    z_train, _ = model.predict(train[0], train[1])
    z_holdout, _ = model.predict(holdout[0], holdout[1])
    y_train = np.asarray([row["y"] for row in train_rows], dtype=np.float64)
    y_holdout = np.asarray([row["y"] for row in holdout_rows], dtype=np.float64)
    heads, metrics = {}, {}
    for role, indices in ROLE_TARGETS.items():
        target_train = y_train[:, indices]
        target_holdout = y_holdout[:, indices]
        weights, bias = _ridge_head(z_train, target_train)
        prediction = z_holdout @ weights + bias
        mean_prediction = np.tile(target_train.mean(axis=0), (len(target_holdout), 1))
        zero_latent_prediction = np.tile(bias, (len(target_holdout), 1))
        shuffled_prediction = np.roll(z_holdout, 1, axis=0) @ weights + bias
        prefix = role.lower()
        metrics[prefix + "_holdout_mse"] = _mse(prediction, target_holdout)
        metrics[prefix + "_mean_baseline_mse"] = _mse(mean_prediction, target_holdout)
        metrics[prefix + "_zero_latent_mse"] = _mse(zero_latent_prediction, target_holdout)
        metrics[prefix + "_shuffled_latent_mse"] = _mse(shuffled_prediction, target_holdout)
        metrics[prefix + "_gain_vs_mean"] = (
            metrics[prefix + "_mean_baseline_mse"] - metrics[prefix + "_holdout_mse"]
        )
        heads[role] = {
            "target_indices": list(indices),
            "weights": weights.tolist(),
            "bias": bias.tolist(),
        }
    return heads, metrics


def _receiver_cohort_losses(model, heads, cohorts):
    """Evaluate learned B1/B2/SELF heads on prior source-disjoint holdout cohorts."""
    result = {role: {} for role in ROLE_TARGETS}
    for key, rows in cohorts or ():
        x, actions, _ = _arrays(list(rows))
        latent, _ = model.predict(x, actions)
        targets = np.asarray([row["y"] for row in rows], dtype=np.float64)
        if (latent.ndim != 2 or len(latent) != len(rows)
                or targets.shape != (len(rows), 3)
                or not np.isfinite(latent).all() or not np.isfinite(targets).all()):
            raise ValueError("invalid receiver retention cohort")
        for role, indices in ROLE_TARGETS.items():
            head = heads.get(role) if type(heads) is dict else None
            if type(head) is not dict or head.get("target_indices") != list(indices):
                raise ValueError("missing receiver retention head")
            weights = np.asarray(head.get("weights"), dtype=np.float64)
            bias = np.asarray(head.get("bias"), dtype=np.float64)
            if (weights.shape != (world_jepa.Z, len(indices))
                    or bias.shape != (len(indices),)
                    or not np.isfinite(weights).all() or not np.isfinite(bias).all()):
                raise ValueError("invalid receiver retention parameters")
            prediction = latent @ weights + bias
            result[role][key] = {
                "rows": len(rows),
                "loss": _mse(prediction, targets[:, indices]),
            }
    return result


def record_world_outcome_packets(store, *, limit=64, cancel_check=None):
    """Persist source-bound T8 eligibility/modulator packets before optimizer gates.

    Packet inserts and the independent scan cursor commit in one SQLite
    transaction. A crash therefore cannot advance the cursor without its
    LearningTrace + ModulatorPacket pair, or duplicate a committed pair.
    This records experience only; it never changes predictor parameters.
    """
    if type(limit) is not int or not 1 <= limit <= MAX_ROWS:
        raise ValueError("neuromod outcome page must be 1..MAX_ROWS")
    if cancel_check is not None and cancel_check():
        raise InterruptedError("T8 neuromod recording cancelled")
    default = {
        "revision": NEUROMOD_CURSOR_REVISION,
        "scan_cursor": 0,
        "processed": 0,
        "last_event_id": None,
    }
    state, version = store.state(NEUROMOD_CURSOR_KEY, default)
    if (type(state) is not dict
            or state.get("revision") != NEUROMOD_CURSOR_REVISION
            or type(state.get("scan_cursor")) is not int
            or state["scan_cursor"] < 0
            or type(state.get("processed", 0)) is not int):
        raise ValueError("invalid persistent neuromod T8 cursor")
    receipts, rejected, next_cursor, scanned, censored_skipped, has_more = (
        verify_committed_transition_page(
            store, after_seq=state["scan_cursor"], limit=limit
        )
    )
    if next_cursor < state["scan_cursor"]:
        raise ValueError("neuromod T8 cursor moved backwards")
    if cancel_check is not None and cancel_check():
        raise InterruptedError("T8 neuromod recording cancelled")

    from .neuromod import SLOW_DECAY
    pending_packets = []
    for receipt in receipts:
        if cancel_check is not None and cancel_check():
            raise InterruptedError("T8 neuromod recording cancelled")
        source_ref = receipt.source_ref
        if type(source_ref) is not dict or not isinstance(receipt.evidence_ref, str):
            raise ValueError("verified T8 receipt lacks source/evidence provenance")
        status = str(receipt.status)
        success = status == "FINAL"
        actual = receipt.actual if type(receipt.actual) is dict else {}
        safety_veto = (
            actual.get("safety_veto") is True
            or actual.get("permission_violation") is True
        )
        provenance = [
            source_ref,
            {"evidence_ref": receipt.evidence_ref},
        ]
        outcome_sha256 = receipt.evidence_ref.rsplit(":", 1)[-1]
        trace = packet(
            "LearningTrace", "N10_NEUROMOD", receipt.event_id,
            receipt.generation_id, provenance,
            path_id="world_predictor",
            activity=1.0,
            eligibility=SLOW_DECAY,
            authority="SYSTEM",
            error=not success,
            detail={
                "action_id": receipt.action_id,
                "outcome_sha256": outcome_sha256,
                "status": status,
            },
        )
        modulator = packet(
            "ModulatorPacket", "N10_NEUROMOD", receipt.event_id,
            receipt.generation_id, provenance,
            path_id="world_predictor",
            source_class="real_deterministic_outcome",
            finality="FINAL",
            epistemic_evidence=1.0,
            human_correction=0.0,
            task_success=1.0 if success else 0.0,
            resource_cost=0.0,
            safety_veto=safety_veto,
            irreversible=actual.get("irreversible") is True,
            rollback_available=actual.get("rollback_available") is True,
            channels={
                "evidence_gain": 1.0,
                "task_success": 1.0 if success else 0.0,
                "action_error": 0.0 if success else 1.0,
            },
        )
        pending_packets.append(("LearningTrace", trace))
        pending_packets.append(("ModulatorPacket", modulator))

    next_state = {
        "revision": NEUROMOD_CURSOR_REVISION,
        "scan_cursor": next_cursor,
        "processed": state.get("processed", 0) + len(receipts),
        "last_event_id": (
            receipts[-1].event_id if receipts else state.get("last_event_id")
        ),
    }
    cursor_advanced = next_cursor > state["scan_cursor"]
    if cancel_check is not None and cancel_check():
        raise InterruptedError("T8 neuromod recording cancelled")
    if cursor_advanced or pending_packets:
        with store.tx() as connection:
            current = connection.execute(
                "SELECT version FROM states WHERE key=?", (NEUROMOD_CURSOR_KEY,)
            ).fetchone()
            current_version = current["version"] if current else 0
            if current_version != version:
                raise ValueError("stale neuromod T8 cursor write")
            for kind, value in pending_packets:
                connection.execute(
                    "INSERT INTO packets VALUES (?,?,?,?,?,?)",
                    (
                        value["packet_id"], kind, value["event_id"],
                        value["brain_generation_id"], dumps(value), now(),
                    ),
                )
            connection.execute(
                "INSERT OR REPLACE INTO states VALUES (?,?,?)",
                (NEUROMOD_CURSOR_KEY, version + 1, dumps(next_state)),
            )
    return {
        "status": "RECORDED" if receipts else "NO_NEW_OUTCOMES",
        "verified_receipts": len(receipts),
        "recorded_packets": len(pending_packets),
        "rejected_receipts": rejected,
        "censored_skipped": censored_skipped,
        "scanned_rows": scanned,
        "scan_cursor": next_cursor,
        "has_more": has_more,
    }



class WorldJEPAStoreConsumer:
    """Consume Store-verified T8 transitions into persistent WorldJEPA/receiver state.

    learning_enabled is a local per-organ lab gate. Each update also requires
    optimizer_permission=True. Both default closed; neither changes Age,
    native-model permissions, or the installed B1/B2 GGUF files.
    """

    def __init__(self, store, checkpoint_dir=None, *, learning_enabled=False,
                 seed=13, ensemble=2):
        if type(learning_enabled) is not bool:
            raise ValueError("learning_enabled must be bool")
        if type(seed) is not int or not 0 <= seed <= 2**63 - 1:
            raise ValueError("seed")
        if type(ensemble) is not int or not 1 <= ensemble <= 16:
            raise ValueError("ensemble")
        self.store = store
        root = (Path(checkpoint_dir) if checkpoint_dir is not None
                else Path(store.home) / "v14_world_jepa")
        if root.exists() and root.is_symlink():
            raise ValueError("checkpoint directory cannot be a symlink")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not root.is_dir() or root.is_symlink():
            raise ValueError("unsafe checkpoint directory")
        try:
            os.chmod(root, 0o700)
        except OSError:
            pass
        self.home = root
        self.lock_path = self.home / "consumer.lock"
        self.learning_enabled = learning_enabled
        self.seed = seed
        self.ensemble = ensemble
        # Recover a prior process that stopped between publish and pending-name cleanup.
        with self._locked(True):
            world_jepa_shadow_checkpoint.cleanup_pending(self.home)

    @contextmanager
    def _locked(self, exclusive=True):
        if self.lock_path.is_symlink():
            raise ValueError("unsafe consumer lock")
        with open(self.lock_path, "a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _validate_record(record):
        if record is None:
            return
        required = {
            "checkpoint", "checkpoint_sha256", "source_sha256", "processed_ids",
            "scan_cursor",
            "fingerprints", "experience_rows", "train_ids", "holdout_ids",
            "receiver_heads", "metrics", "self_state", "fit_steps",
        }
        if type(record) is not dict or set(record) != required:
            raise ValueError("invalid WorldJEPA state record")
        if (type(record["checkpoint"]) is not str
                or not CHECKPOINT_NAME.fullmatch(record["checkpoint"])):
            raise ValueError("invalid checkpoint filename")
        _sha(record["checkpoint_sha256"])
        _sha(record["source_sha256"])
        fingerprints = record["fingerprints"]
        if (type(fingerprints) is not dict or len(fingerprints) > MAX_TRACKED
                or any(type(key) is not str or not key or len(key) > 128 for key in fingerprints)
                or any(type(value) is not str or not SHA256.fullmatch(value)
                       for value in fingerprints.values())):
            raise ValueError("invalid processed receipt map")
        processed = record["processed_ids"]
        if (type(processed) is not list
                or any(type(item) is not str or not item or len(item) > 128 for item in processed)
                or len(processed) != len(fingerprints)
                or set(processed) != set(fingerprints)
                or len(set(processed)) != len(processed)):
            raise ValueError("processed cursor mismatch")
        rows = record["experience_rows"]
        if type(rows) is not list or len(rows) > MAX_ROWS:
            raise ValueError("replay memory budget")
        row_ids = []
        row_fields = {
            "action_id", "source_id", "fingerprint", "source_sha256", "outcome_sha256",
            "created", "s", "a", "y",
        }
        for row in rows:
            if type(row) is not dict or set(row) not in (row_fields, row_fields | {"session_id"}):
                raise ValueError("invalid replay memory row")
            if ("session_id" in row and
                    (type(row["session_id"]) is not str or not row["session_id"]
                     or len(row["session_id"]) > 128)):
                raise ValueError("invalid replay session provenance")
            if (type(row["source_id"]) is not str or not row["source_id"]
                    or len(row["source_id"]) > 256
                    or row["action_id"] not in fingerprints
                    or fingerprints[row["action_id"]] != row["fingerprint"]
                    or row["a"] not in world_model.ACTIONS
                    or not _finite_number(row["created"])):
                raise ValueError("replay provenance mismatch")
            _sha(row["fingerprint"])
            _sha(row["source_sha256"])
            _sha(row["outcome_sha256"])
            _vector(row["s"], 4)
            _vector(row["y"], 3)
            row_ids.append(row["action_id"])
        if len(set(row_ids)) != len(row_ids):
            raise ValueError("duplicate replay row")
        train_ids, holdout_ids = record["train_ids"], record["holdout_ids"]
        for ids in (train_ids, holdout_ids):
            if (type(ids) is not list
                    or any(type(item) is not str or not item for item in ids)
                    or len(set(ids)) != len(ids)):
                raise ValueError("invalid train/holdout ids")
        if (set(train_ids) & set(holdout_ids)
                or set(train_ids + holdout_ids) != set(row_ids)):
            raise ValueError("train/holdout cursor mismatch")
        row_by_id = {row["action_id"]: row for row in rows}
        source_hashes = {}
        for row in rows:
            prior = source_hashes.get(row["source_id"])
            if prior is not None and prior != row["source_sha256"]:
                raise ValueError("persisted source digest changed")
            source_hashes[row["source_id"]] = row["source_sha256"]
        train_sources = {row_by_id[action_id]["source_id"] for action_id in train_ids}
        holdout_sources = {row_by_id[action_id]["source_id"] for action_id in holdout_ids}
        if train_sources & holdout_sources:
            raise ValueError("persisted source holdout overlap")
        train_source_hashes = {row_by_id[action_id]["source_sha256"] for action_id in train_ids}
        holdout_source_hashes = {row_by_id[action_id]["source_sha256"] for action_id in holdout_ids}
        if train_source_hashes & holdout_source_hashes:
            raise ValueError("persisted source digest holdout overlap")
        def persisted_content(action_id):
            row = row_by_id[action_id]
            raw = json.dumps({"s": row["s"], "a": row["a"], "y": row["y"]},
                             sort_keys=True, separators=(",", ":"), allow_nan=False)
            return hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if ({persisted_content(action_id) for action_id in train_ids}
                & {persisted_content(action_id) for action_id in holdout_ids}):
            raise ValueError("persisted holdout content overlap")
        heads = record["receiver_heads"]
        if type(heads) is not dict or set(heads) != set(ROLE_TARGETS):
            raise ValueError("receiver head set")
        for role, indices in ROLE_TARGETS.items():
            head = heads[role]
            if (type(head) is not dict or set(head) != {"target_indices", "weights", "bias"}
                    or head["target_indices"] != list(indices)
                    or type(head["weights"]) is not list
                    or len(head["weights"]) != world_jepa.Z
                    or type(head["bias"]) is not list
                    or len(head["bias"]) != len(indices)
                    or any(type(row) is not list or len(row) != len(indices)
                           or any(not _finite_number(value) for value in row)
                           for row in head["weights"])
                    or any(not _finite_number(value) for value in head["bias"])):
                raise ValueError("invalid receiver head parameters")
        if type(record["metrics"]) is not dict or type(record["self_state"]) is not dict:
            raise ValueError("metrics/self state")
        if type(record["fit_steps"]) is not int or record["fit_steps"] < 1:
            raise ValueError("fit step evidence")
        if type(record["scan_cursor"]) is not int or record["scan_cursor"] < 0:
            raise ValueError("scan cursor")

    @staticmethod
    def _validate_pending_rows(rows, active):
        if type(rows) is not list or len(rows) > MAX_ROWS:
            raise ValueError("pending T8 buffer budget")
        active_ids = set(active["fingerprints"]) if active is not None else set()
        seen, source_hashes = set(), {}
        required = {
            "action_id", "source_id", "fingerprint", "source_sha256", "outcome_sha256",
            "created", "s", "a", "y",
        }
        for row in rows:
            if type(row) is not dict or set(row) not in (required, required | {"session_id"}):
                raise ValueError("invalid pending T8 row")
            if ("session_id" in row and
                    (type(row["session_id"]) is not str or not row["session_id"]
                     or len(row["session_id"]) > 128)):
                raise ValueError("invalid pending session provenance")
            action_id, source_id = row["action_id"], row["source_id"]
            if (type(action_id) is not str or not action_id or len(action_id) > 128
                    or action_id in active_ids or action_id in seen
                    or type(source_id) is not str or not source_id or len(source_id) > 256
                    or row["a"] not in world_model.ACTIONS
                    or not _finite_number(row["created"])):
                raise ValueError("pending T8 identity mismatch")
            _sha(row["fingerprint"])
            source_sha = _sha(row["source_sha256"])
            _sha(row["outcome_sha256"])
            _vector(row["s"], 4)
            _vector(row["y"], 3)
            prior = source_hashes.get(source_id)
            if prior is not None and prior != source_sha:
                raise ValueError("pending source digest changed")
            source_hashes[source_id] = source_sha
            seen.add(action_id)

    def _read_state(self):
        payload, version = self.store.state(STATE_KEY, None)
        if payload is None:
            return {"schema": STATE_SCHEMA, "revision": REVISION,
                    "active": None, "previous": None, "scan_cursor": 0,
                    "pending_rows": []}, version
        if type(payload) is not dict:
            raise ValueError("incompatible WorldJEPA Store state")
        old_keys = {"schema", "revision", "active", "previous", "scan_cursor"}
        if (set(payload) == old_keys
                and payload.get("schema") == LEGACY_STATE_SCHEMA
                and payload.get("revision") == LEGACY_REVISION):
            self._validate_record(payload["active"])
            self._validate_record(payload["previous"])
            if type(payload["scan_cursor"]) is not int or payload["scan_cursor"] < 0:
                raise ValueError("invalid legacy scan cursor")
            return {"schema": STATE_SCHEMA, "revision": REVISION,
                    "active": payload["active"], "previous": payload["previous"],
                    "scan_cursor": payload["scan_cursor"], "pending_rows": []}, version
        expected_keys = old_keys | {"pending_rows"}
        if (set(payload) != expected_keys
                or payload.get("schema") != STATE_SCHEMA or payload.get("revision") != REVISION
                or type(payload.get("scan_cursor")) is not int or payload["scan_cursor"] < 0):
            raise ValueError("incompatible WorldJEPA Store state")
        self._validate_record(payload["active"])
        self._validate_record(payload["previous"])
        self._validate_pending_rows(payload["pending_rows"], payload["active"])
        return payload, version

    def _persist_pending(self, state, version, pending_by_id, next_cursor):
        pending_rows = sorted(
            pending_by_id.values(), key=lambda row: (row["created"], row["action_id"])
        )
        if len(pending_rows) > MAX_ROWS:
            return "PENDING_BUFFER_CAPACITY"
        next_state = dict(state)
        next_state["pending_rows"] = pending_rows
        next_state["scan_cursor"] = next_cursor
        try:
            self.store.set_state(STATE_KEY, next_state, expected=version)
        except ValueError as exc:
            if "Stale state write" in str(exc):
                return "CONCURRENT_STATE_CONFLICT_RETRY"
            raise
        return "PERSISTED"

    def _checkpoint_path(self, record):
        self._validate_record(record)
        path = self.home / record["checkpoint"]
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or unsafe WorldJEPA checkpoint")
        return path

    def _load_model(self, record):
        path = self._checkpoint_path(record)
        return world_jepa_shadow_checkpoint.load(
            path, record["source_sha256"], record["checkpoint_sha256"]
        )

    def _prune_checkpoints(self, state):
        keep = {
            record["checkpoint"]
            for record in (state.get("active"), state.get("previous"))
            if record is not None
        }
        removed = errors = 0
        for path in self.home.glob("jepa-*.npz"):
            if path.name in keep or path.is_symlink() or not path.is_file():
                continue
            try:
                path.unlink()
                removed += 1
            except OSError:
                errors += 1
        return removed, errors


    def record_outcomes(self, *, limit=64, cancel_check=None):
        """Record T8 neuromodulation packets without touching the model checkpoint."""
        return record_world_outcome_packets(
            self.store, limit=limit, cancel_check=cancel_check
        )

    def update(self, *, limit=DEFAULT_PAGE_SIZE, steps=80, optimizer_permission=False,
               replay_mode="uniform", encoder_mode="full", cancel_check=None, drift_control=None,
               replay_projection=False, neuromod_scale=1.0):
        if type(limit) is not int or not 16 <= limit <= MAX_ROWS:
            raise ValueError("limit")
        if type(steps) is not int or not 1 <= steps <= 2000:
            raise ValueError("steps")
        if type(optimizer_permission) is not bool:
            raise ValueError("optimizer_permission must be bool")
        if replay_mode not in world_jepa_replay.REPLAY_MODES:
            raise ValueError("unsupported WorldJEPA replay_mode")
        if encoder_mode not in {"full", "predictor_only"}:
            raise ValueError("encoder_mode must be full or predictor_only")
        if type(replay_projection) is not bool:
            raise ValueError("replay_projection must be bool")
        if not _finite_number(neuromod_scale) or not 0.0 < neuromod_scale <= 1.0:
            raise ValueError("neuromod_scale must be finite in (0, 1]")
        if replay_projection and replay_mode not in {"uniform_budget", "session_contiguous", "on_demand_conflict", "on_demand_loss"}:
            raise ValueError("replay projection requires a budgeted replay mode")
        drift_config = world_jepa_drift.normalize_config(drift_control)
        if cancel_check is not None and not callable(cancel_check):
            raise ValueError("cancel_check must be callable")
        if cancel_check is not None and cancel_check():
            return {"status":"CANCELLED","pending_rows":0,"checkpoint_committed":False,
                    "native_body_weights_changed":False}
        with self._locked(True):
            state, version = self._read_state()
            receipts, rejected, next_cursor, scanned, censored_skipped, has_more = (
                verify_committed_transition_page(self.store, after_seq=state["scan_cursor"], limit=limit)
            )
            incoming = [_receipt_row(receipt) for receipt in receipts]
            active = state["active"]
            prior_fingerprints = dict(active["fingerprints"]) if active else {}
            prior_rows = {row["action_id"]: row for row in (active["experience_rows"] if active else [])}
            pending_by_id = {row["action_id"]: row for row in state["pending_rows"]}
            for action_id, row in pending_by_id.items():
                if action_id in prior_fingerprints:
                    raise ValueError("pending T8 row already committed in active checkpoint")
                prior_fingerprints[action_id] = row["fingerprint"]
                prior_rows[action_id] = row
            # Pending rows are retained, but an unchanged cohort is not retrained
            # on every post-turn callback. Re-enter it only when new verified
            # evidence arrives; otherwise the same evidence cannot improve.
            incoming_new_ids = []
            for row in incoming:
                action_id = row["action_id"]
                prior_fingerprint = prior_fingerprints.get(action_id)
                if prior_fingerprint is not None and prior_fingerprint != row["fingerprint"]:
                    raise ValueError("committed T8 receipt changed after learning")
                if prior_fingerprint is None:
                    incoming_new_ids.append(action_id)
                    prior_fingerprints[action_id] = row["fingerprint"]
                    pending_by_id[action_id] = row
                    prior_rows[action_id] = row
            new_ids = list(pending_by_id) if incoming_new_ids else []
            if len(prior_fingerprints) > MAX_TRACKED:
                raise OverflowError("processed T8 identity budget exhausted; fail closed")
            if not new_ids:
                if pending_by_id:
                    if not self.learning_enabled:
                        return {"status": "LEARNING_DISABLED", "new_receipts": 0,
                                "verified_receipts": len(receipts), "rejected_receipts": rejected,
                                "censored_skipped": censored_skipped, "scanned_rows": scanned,
                                "pending_rows": len(pending_by_id),
                                "native_body_weights_changed": False}
                    if optimizer_permission is not True:
                        return {"status": "PENDING_OPTIMIZER_PERMISSION", "new_receipts": 0,
                                "verified_receipts": len(receipts), "rejected_receipts": rejected,
                                "censored_skipped": censored_skipped, "scanned_rows": scanned,
                                "pending_rows": len(pending_by_id),
                                "native_body_weights_changed": False}
                    persisted_cursor = state["scan_cursor"]
                    if next_cursor > state["scan_cursor"]:
                        persisted = self._persist_pending(state, version, pending_by_id, next_cursor)
                        if persisted != "PERSISTED":
                            return {"status": persisted, "pending_rows": len(pending_by_id),
                                    "scan_cursor": state["scan_cursor"],
                                    "native_body_weights_changed": False}
                        persisted_cursor = next_cursor
                    return {
                        "status": "WAITING_FOR_MORE_T8_DATA", "verified_receipts": len(receipts),
                        "rejected_receipts": rejected, "censored_skipped": censored_skipped,
                        "scanned_rows": scanned, "scan_cursor": persisted_cursor,
                        "has_more": has_more, "processed": len(prior_fingerprints),
                        "pending_rows": len(pending_by_id),
                        "native_body_weights_changed": False,
                    }
                persisted_cursor = state["scan_cursor"]
                if (next_cursor > state["scan_cursor"] and self.learning_enabled is True
                        and optimizer_permission is True):
                    next_state = dict(state)
                    next_state["scan_cursor"] = next_cursor
                    self.store.set_state(STATE_KEY, next_state, expected=version)
                    persisted_cursor = next_cursor
                return {
                    "status": "NO_NEW_TRANSITIONS", "verified_receipts": len(receipts),
                    "rejected_receipts": rejected, "censored_skipped": censored_skipped,
                    "scanned_rows": scanned, "scan_cursor": persisted_cursor,
                    "has_more": has_more, "processed": len(prior_fingerprints),
                    "pending_rows": len(pending_by_id),
                    "native_body_weights_changed": False,
                }
            if not self.learning_enabled:
                return {"status": "LEARNING_DISABLED", "new_receipts": len(new_ids),
                        "verified_receipts": len(receipts), "rejected_receipts": rejected,
                        "censored_skipped": censored_skipped, "scanned_rows": scanned,
                        "pending_rows": len(pending_by_id),
                        "native_body_weights_changed": False}
            if optimizer_permission is not True:
                return {"status": "PENDING_OPTIMIZER_PERMISSION", "new_receipts": len(new_ids),
                        "verified_receipts": len(receipts), "rejected_receipts": rejected,
                        "censored_skipped": censored_skipped, "scanned_rows": scanned,
                        "pending_rows": len(pending_by_id),
                        "native_body_weights_changed": False}
            if encoder_mode == "predictor_only" and active is None:
                return {"status": "ENCODER_BOOTSTRAP_REQUIRED", "new_receipts": len(new_ids),
                        "pending_rows": len(pending_by_id), "scan_cursor": state["scan_cursor"],
                        "native_body_weights_changed": False, "native_body_consumed": False}
            new_set = set(new_ids)
            candidates = list(prior_rows.values())
            if len(candidates) > MAX_ROWS:
                new_rows = [row for row in candidates if row["action_id"] in new_set]
                old_rows = [row for row in candidates if row["action_id"] not in new_set]
                if len(new_rows) > MAX_ROWS:
                    raise OverflowError("new T8 batch exceeds replay memory")
                keep_old = max(0, MAX_ROWS - len(new_rows))
                old_rows.sort(key=lambda row: (row["created"], row["action_id"]))
                candidates = new_rows + old_rows[-keep_old:] if keep_old else new_rows
            experience_rows = sorted(candidates, key=lambda row: row["action_id"])
            try:
                split = _source_disjoint_split(experience_rows)
            except ValueError as exc:
                persisted = self._persist_pending(state, version, pending_by_id, next_cursor)
                if persisted != "PERSISTED":
                    return {"status": persisted, "pending_rows": len(pending_by_id),
                            "scan_cursor": state["scan_cursor"],
                            "native_body_weights_changed": False}
                return {"status": "INSUFFICIENT_SOURCE_DISJOINT_T8_COHORT", "reason": str(exc),
                        "verified_receipts": len(receipts), "rejected_receipts": rejected,
                        "censored_skipped": censored_skipped, "new_receipts": len(new_ids),
                        "pending_rows": len(pending_by_id), "scanned_rows": scanned,
                        "scan_cursor": next_cursor, "has_more": has_more,
                        "native_body_weights_changed": False}
            train_ids, holdout_ids = list(split["train_action_ids"]), list(split["holdout_action_ids"])
            if set(train_ids) & set(holdout_ids):
                raise ValueError("train/holdout identity overlap")
            row_by_id = {row["action_id"]: row for row in experience_rows}
            train_rows = [row_by_id[action_id] for action_id in train_ids]
            holdout_rows = [row_by_id[action_id] for action_id in holdout_ids]
            new_train_rows = [row for row in train_rows if row["action_id"] in new_set]
            old_train_rows = [row for row in train_rows if row["action_id"] not in new_set]
            train, holdout = split["train"], split["holdout"]
            if active is not None:
                model = self._load_model(active)
                checkpoint_before = active["checkpoint_sha256"]
            else:
                model = world_jepa.WorldJEPA(seed=self.seed, ensemble=self.ensemble)
                try:
                    model.fit(*train, steps=0, log_every=1, cancel_check=cancel_check)
                except InterruptedError:
                    return {"status":"CANCELLED","pending_rows":len(pending_by_id),
                            "scan_cursor":state["scan_cursor"],"checkpoint_committed":False,
                            "native_body_weights_changed":False}
                checkpoint_before = None
            fit_steps_before = int(getattr(model, "_fit_steps", 0))
            before = _parameter_snapshot(model)
            old_target_snapshot = (
                {key: np.asarray(value).copy() for key, value in model.tgt.items()}
                if active is not None else None
            )
            holdout_before = model.prediction_loss(*holdout)
            old_holdout_before = old_holdout_after = None
            old_holdout_cohorts = ()
            old_holdout_cohort_overflow = False
            old_holdout_cohort_before = {}
            old_receiver_cohort_before = {role: {} for role in ROLE_TARGETS}
            if active is not None:
                old_holdout_ids = set(active["holdout_ids"])
                old_holdout_rows = [row for row in active["experience_rows"] if row["action_id"] in old_holdout_ids]
                if len(old_holdout_rows) >= 2:
                    old_holdout = _arrays(old_holdout_rows)
                    old_holdout_before = model.prediction_loss(
                        *old_holdout, target_snapshot=old_target_snapshot
                    )
                    old_holdout_cohorts = _retention_cohorts(old_holdout_rows)
                    old_holdout_cohort_overflow = old_holdout_cohorts is None
                    if not old_holdout_cohort_overflow:
                        old_holdout_cohort_before = _retention_cohort_losses(
                            model, old_holdout_cohorts, target_snapshot=old_target_snapshot
                        )
                        old_receiver_cohort_before = _receiver_cohort_losses(
                            model, active["receiver_heads"], old_holdout_cohorts
                        )
            # One source/content-disjoint guard partition spans the whole training fold.
            # Prior-session guard rows select retention-safe replay/update scales; current-task
            # guard rows select adaptation-safe scales. Neither guard receives gradients or
            # enters replay. Current guard rows remain in the durable pending queue.
            replay_salt = (active["checkpoint_sha256"] if active else "fresh") + ":" + _cohort_sha(new_train_rows)
            new_fit_rows = list(new_train_rows)
            new_guard_rows = []
            new_guard_cohorts = ()
            new_guard_cohort_overflow = False
            new_guard_cohort_before = {}
            new_guard_manifest = None
            old_fit_rows = list(old_train_rows)
            old_guard_rows = []
            old_guard_cohorts = ()
            old_guard_cohort_overflow = False
            old_guard_cohort_before = {}
            old_guard_manifest = None
            if active is not None:
                combined_guard_split = _source_disjoint_guard_split(
                    train_rows, salt=replay_salt + ":combined"
                )
                combined_guard_ready = combined_guard_split is not None
                if combined_guard_ready:
                    combined_guard_rows = combined_guard_split["guard_rows"]
                    combined_fit_rows = combined_guard_split["fit_rows"]
                    candidate_new_guard_rows = [
                        row for row in combined_guard_rows if row["action_id"] in new_set
                    ]
                    candidate_old_guard_rows = [
                        row for row in combined_guard_rows if row["action_id"] not in new_set
                    ]
                    candidate_new_fit_rows = [
                        row for row in combined_fit_rows if row["action_id"] in new_set
                    ]
                    candidate_old_fit_rows = [
                        row for row in combined_fit_rows if row["action_id"] not in new_set
                    ]
                    combined_guard_ready = (
                        len(candidate_new_guard_rows) >= 2
                        and len(candidate_old_guard_rows) >= 2
                        and len(candidate_new_fit_rows) >= 2
                        and len(candidate_old_fit_rows) >= 2
                    )
                if combined_guard_ready:
                    new_fit_rows = candidate_new_fit_rows
                    new_guard_rows = candidate_new_guard_rows
                    old_fit_rows = candidate_old_fit_rows
                    old_guard_rows = candidate_old_guard_rows
                    old_guard_manifest = combined_guard_split["manifest"]
                    new_guard_manifest = combined_guard_split["manifest"]
                else:
                    # Small or highly skewed batches retain the existing prior-only
                    # guard behavior; no current rows are silently discarded.
                    old_guard_split = _source_disjoint_guard_split(
                        old_train_rows, salt=replay_salt + ":prior"
                    )
                    if old_guard_split is None:
                        persisted = self._persist_pending(state, version, pending_by_id, next_cursor)
                        if persisted != "PERSISTED":
                            return {"status": persisted, "pending_rows": len(pending_by_id),
                                    "scan_cursor": state["scan_cursor"],
                                    "native_body_weights_changed": False}
                        return {
                            "status": "INSUFFICIENT_SOURCE_DISJOINT_GUARD_COHORT",
                            "prior_train_rows": len(old_train_rows),
                            "prior_guard_split_ready": False,
                            "pending_rows": len(pending_by_id),
                            "scan_cursor": next_cursor,
                            "native_body_weights_changed": False,
                        }
                    old_fit_rows = old_guard_split["fit_rows"]
                    old_guard_rows = old_guard_split["guard_rows"]
                    old_guard_manifest = old_guard_split["manifest"]
                old_guard_cohorts = _retention_cohorts(old_guard_rows)
                old_guard_cohort_overflow = old_guard_cohorts is None
                if old_guard_rows and not old_guard_cohort_overflow:
                    old_guard_cohort_before = _retention_cohort_losses(
                        model, old_guard_cohorts, target_snapshot=old_target_snapshot
                    )
                if new_guard_rows:
                    new_guard_cohorts = _retention_cohorts(new_guard_rows)
                    new_guard_cohort_overflow = new_guard_cohorts is None
                    if not new_guard_cohort_overflow:
                        new_guard_cohort_before = _retention_cohort_losses(
                            model, new_guard_cohorts, target_snapshot=old_target_snapshot
                        )

            conflict_probe = {
                "scores": {}, "scored_session_count": 0,
                "unscored_session_count": 0, "legacy_rows_excluded": 0, "probe_rows": 0,
            }
            loss_probe = {
                "scores": {}, "scored_session_count": 0,
                "unscored_session_count": 0, "legacy_rows_excluded": 0,
                "probe_rows": 0, "probe_steps": 0,
            }
            cohort_scores = None
            if replay_mode == "on_demand_conflict":
                # Use source/content-disjoint prior guard anchors to estimate
                # signed interference. Replay examples still come only from
                # old_fit_rows; the final holdout remains promotion-only.
                if active is not None and len(new_fit_rows) >= 2 and len(old_guard_rows) >= 2:
                    conflict_probe = _session_gradient_conflict_scores(
                        model, new_fit_rows, old_guard_rows,
                        train_encoder=(encoder_mode == "full"), salt=replay_salt,
                    )
                cohort_scores = conflict_probe["scores"]
            elif replay_mode == "on_demand_loss":
                if active is not None and len(new_fit_rows) >= 2 and len(old_guard_rows) >= 2:
                    try:
                        probe_model = self._load_model(active)
                        loss_probe = _session_loss_demand_scores(
                            probe_model, new_fit_rows, old_guard_rows,
                            train_encoder=(encoder_mode == "full"),
                            salt=replay_salt, steps=steps, cancel_check=cancel_check,
                        )
                    except InterruptedError:
                        return {"status": "CANCELLED", "pending_rows": len(pending_by_id),
                                "scan_cursor": state["scan_cursor"],
                                "checkpoint_committed": False,
                                "native_body_weights_changed": False}
                cohort_scores = loss_probe["scores"]
            replay_selection = world_jepa_replay.select_replay_rows(
                replay_mode, new_fit_rows, old_fit_rows,
                budget=len(new_fit_rows), salt=replay_salt,
                cohort_scores=cohort_scores,
            )
            replay_rows = replay_selection["rows"]
            if replay_mode == "on_demand_conflict" and replay_selection["budget_matched"] is not True:
                persisted = self._persist_pending(state, version, pending_by_id, next_cursor)
                if persisted != "PERSISTED":
                    return {"status": persisted, "pending_rows": len(pending_by_id),
                            "scan_cursor": state["scan_cursor"],
                            "native_body_weights_changed": False}
                return {
                    "status": "ON_DEMAND_REPLAY_BUDGET_UNMATCHED",
                    "replay_candidate_rows": len(old_fit_rows),
                    "replay_rows": len(replay_rows),
                    "replay_requested_budget_rows": replay_selection["requested_budget_rows"],
                    "replay_budget_rows": replay_selection["budget_rows"],
                    "replay_legacy_rows_excluded": replay_selection["legacy_rows_excluded"],
                    "replay_scored_sessions": conflict_probe["scored_session_count"],
                    "pending_rows": len(pending_by_id), "scan_cursor": next_cursor,
                    "native_body_weights_changed": False,
                }
            replay_start = None
            replay_cohort_ranges = None
            replay_constraint_session_keys = ()
            replay_reference_batches = None
            replay_reference_fold = None
            replay_reference_action_ids_sha256 = None
            projection_fallback_reason = None
            if replay_projection:
                if len(new_fit_rows) < 2:
                    persisted = self._persist_pending(state, version, pending_by_id, next_cursor)
                    if persisted != "PERSISTED":
                        return {"status": persisted, "pending_rows": len(pending_by_id),
                                "scan_cursor": state["scan_cursor"],
                                "native_body_weights_changed": False}
                    return {"status": "INSUFFICIENT_NEW_TRAIN_ROWS",
                            "new_train_rows": len(new_train_rows), "replay_rows": len(replay_rows),
                            "pending_rows": len(pending_by_id), "scan_cursor": next_cursor,
                            "native_body_weights_changed": False}
                # A requested GEM/AGEM constraint can be unavailable when the
                # loss-demand selector finds no prior session with positive
                # replay demand (or when this is the first checkpoint). This is
                # not a reason to discard otherwise useful new-task learning:
                # the independent source-disjoint prior/current guard cohorts
                # and final old-holdout retention gate still decide promotion.
                # Report the fallback explicitly; never claim projection ran.
                if active is None:
                    projection_fallback_reason = "NO_PRIOR_CHECKPOINT"
                elif len(replay_rows) < 2:
                    projection_fallback_reason = "NO_ELIGIBLE_REPLAY_ROWS"
                else:
                    replay_start = len(new_fit_rows)
                    if replay_mode in {"session_contiguous", "on_demand_conflict", "on_demand_loss"}:
                        grouped = _ordered_replay_rows_and_ranges(replay_rows, replay_start)
                        if grouped is None:
                            persisted = self._persist_pending(state, version, pending_by_id, next_cursor)
                            if persisted != "PERSISTED":
                                return {"status": persisted, "pending_rows": len(pending_by_id),
                                        "scan_cursor": state["scan_cursor"],
                                        "native_body_weights_changed": False}
                            return {
                                "status": "INSUFFICIENT_REPLAY_COHORT_CAPACITY",
                                "replay_rows": len(replay_rows),
                                "max_replay_constraints": world_jepa.MAX_REPLAY_CONSTRAINTS,
                                "pending_rows": len(pending_by_id), "scan_cursor": next_cursor,
                                "native_body_weights_changed": False,
                            }
                        replay_rows, replay_cohort_ranges, replay_constraint_session_keys = grouped
                        if replay_mode in {"on_demand_conflict", "on_demand_loss"}:
                            guard_by_key = {}
                            for row in old_guard_rows:
                                session_id = row.get("session_id")
                                if type(session_id) is str and session_id:
                                    key = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:16]
                                    guard_by_key.setdefault(key, []).append(row)
                            guard_batches = []
                            guard_action_ids = []
                            for session_key in replay_constraint_session_keys:
                                guard_group = sorted(
                                    guard_by_key.get(session_key, []),
                                    key=lambda row: (float(row["created"]), row["action_id"]),
                                )
                                if len(guard_group) < 2:
                                    persisted = self._persist_pending(
                                        state, version, pending_by_id, next_cursor
                                    )
                                    if persisted != "PERSISTED":
                                        return {"status": persisted, "pending_rows": len(pending_by_id),
                                                "scan_cursor": state["scan_cursor"],
                                                "native_body_weights_changed": False}
                                    return {
                                        "status": "INSUFFICIENT_PRIOR_GUARD_REFERENCE_ROWS",
                                        "session_key": session_key,
                                        "pending_rows": len(pending_by_id),
                                        "scan_cursor": next_cursor,
                                        "native_body_weights_changed": False,
                                    }
                                selected_guard_rows = guard_group[:MAX_CONFLICT_SAMPLE_ROWS]
                                guard_action_ids.extend(row["action_id"] for row in selected_guard_rows)
                                guard_batches.append(_arrays(selected_guard_rows))
                            replay_reference_batches = tuple(guard_batches)
                            replay_reference_fold = "prior_guard"
                            replay_reference_action_ids_sha256 = hashlib.sha256(
                                "\n".join(sorted(guard_action_ids)).encode("utf-8")
                            ).hexdigest()
            fit_rows = (
                train_rows if active is None
                else list(new_fit_rows) + list(replay_rows)
            )
            conflict_manifest = [
                {
                    "session_key": hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:16],
                    "score": float(score),
                }
                for session_id, score in sorted(conflict_probe["scores"].items())
            ]
            loss_demand_manifest = [
                {
                    "session_key": hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:16],
                    "score": float(score),
                }
                for session_id, score in sorted(loss_probe["scores"].items())
            ]
            replay_metrics = {
                "neuromod_scale": float(neuromod_scale),
                "replay_mode": replay_mode,
                "new_fit_rows": len(new_fit_rows),
                "prior_fit_rows": len(old_fit_rows),
                "prior_guard_rows": len(old_guard_rows),
                "prior_train_rows_total": len(old_train_rows),
                "guard_split_enabled": active is not None,
                "guard_split_source_disjoint": (
                    None if active is None else bool(old_guard_manifest["source_disjoint"])
                ),
                "guard_split_content_disjoint": (
                    None if active is None else bool(old_guard_manifest["content_disjoint"])
                ),
                "prior_guard_manifest_sha256": (
                    None if old_guard_manifest is None
                    else old_guard_manifest["manifest_sha256"]
                ),
                "current_guard_split_enabled": bool(new_guard_rows),
                "current_guard_rows": len(new_guard_rows),
                "current_guard_action_ids": [row["action_id"] for row in new_guard_rows],
                "current_guard_split_source_disjoint": (
                    None if new_guard_manifest is None
                    else bool(new_guard_manifest["source_disjoint"])
                ),
                "current_guard_split_content_disjoint": (
                    None if new_guard_manifest is None
                    else bool(new_guard_manifest["content_disjoint"])
                ),
                "current_guard_manifest_sha256": (
                    None if new_guard_manifest is None
                    else new_guard_manifest["manifest_sha256"]
                ),
                "current_guard_cohort_before": new_guard_cohort_before,
                "loss_demand_probe_fold": (
                    "prior_guard" if replay_mode == "on_demand_loss" and active is not None
                    else None
                ),
                "prior_fit_action_ids_sha256": (
                    None if old_guard_manifest is None
                    else old_guard_manifest["fit_action_ids_sha256"]
                ),
                "replay_projection_reference_fold": replay_reference_fold,
                "replay_projection_reference_action_ids_sha256": replay_reference_action_ids_sha256,
                "replay_conflict_probe_fold": (
                    "prior_guard" if replay_mode == "on_demand_conflict" and active is not None
                    else None
                ),
                "prior_guard_action_ids_sha256": (
                    None if old_guard_manifest is None
                    else old_guard_manifest["guard_action_ids_sha256"]
                ),
                "replay_conflict_probe_action_ids_sha256": (
                    old_guard_manifest["guard_action_ids_sha256"]
                    if replay_mode == "on_demand_conflict" and old_guard_manifest is not None
                    else None
                ),
                "replay_rows": len(replay_rows),
                "replay_budget_rows": replay_selection["budget_rows"],
                "replay_requested_budget_rows": replay_selection["requested_budget_rows"],
                "replay_budget_matched": replay_selection["budget_matched"],
                "replay_session_count": replay_selection["session_count"],
                "replay_window_count": replay_selection["window_count"],
                "replay_manifest_sha256": replay_selection["manifest_sha256"],
                "replay_legacy_rows_excluded": replay_selection["legacy_rows_excluded"],
                "replay_scored_session_count": conflict_probe["scored_session_count"],
                "replay_unscored_session_count": conflict_probe["unscored_session_count"],
                "replay_conflict_probe_rows": conflict_probe["probe_rows"],
                "replay_conflict_scores_sha256": hashlib.sha256(json.dumps(
                    conflict_manifest, sort_keys=True, separators=(",", ":"), allow_nan=False
                ).encode("utf-8")).hexdigest(),
                "replay_loss_demand_probe_rows": loss_probe["probe_rows"],
                "replay_loss_demand_probe_steps": loss_probe["probe_steps"],
                "replay_loss_demand_scored_session_count": loss_probe["scored_session_count"],
                "replay_loss_demand_unscored_session_count": loss_probe["unscored_session_count"],
                "replay_loss_demand_positive_session_count": sum(
                    1 for score in loss_probe["scores"].values() if score > 0.0
                ),
                "replay_loss_demand_max_score": max(loss_probe["scores"].values(), default=0.0),
                "replay_loss_demand_scores_sha256": hashlib.sha256(json.dumps(
                    loss_demand_manifest, sort_keys=True, separators=(",", ":"), allow_nan=False
                ).encode("utf-8")).hexdigest(),
                "replay_projection_requested": replay_projection,
                "replay_projection_enabled": replay_start is not None,
                "replay_projection_fallback_reason": projection_fallback_reason,
                "replay_projection_mode": (
                    "per_session_gem" if replay_cohort_ranges is not None
                    else "aggregate_agem" if replay_start is not None else "off"
                ),
                "replay_constraint_session_count": (
                    len(replay_cohort_ranges) if replay_cohort_ranges is not None
                    else (1 if replay_start is not None else 0)
                ),
                "replay_constraint_session_keys": list(replay_constraint_session_keys),
            }
            if len(fit_rows) < 2:
                persisted = self._persist_pending(state, version, pending_by_id, next_cursor)
                if persisted != "PERSISTED":
                    return {"status": persisted, "pending_rows": len(pending_by_id),
                            "scan_cursor": state["scan_cursor"],
                            "native_body_weights_changed": False}
                return {"status": "INSUFFICIENT_NEW_TRAIN_ROWS",
                        "new_train_rows": len(new_train_rows),
                        "replay_candidate_rows": len(old_fit_rows),
                        **replay_metrics,
                        "pending_rows": len(pending_by_id),
                        "scan_cursor": next_cursor,
                        "native_body_weights_changed": False}
            fit_arrays = _arrays(fit_rows)
            replay_array_bytes = (
                int(sum(int(array.nbytes) for array in _arrays(replay_rows)))
                if replay_rows else 0
            )
            replay_metrics.update({
                "fit_array_bytes": int(sum(int(array.nbytes) for array in fit_arrays)),
                "replay_array_bytes": replay_array_bytes,
            })
            # Train once, then backtrack the resulting parameter delta along a
            # deterministic trust-region ladder. Guard rows select the scale;
            # final holdouts are evaluated only once and never select a retry.
            # This keeps Android cost bounded to one optimizer pass per candidate.
            base_update_scales = ([1.0] if active is None else
                                  [1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125,
                                   0.015625, 0.0078125, 0.00390625])
            previous_scale_value = (
                active.get("metrics", {}).get("selected_update_scale")
                if active is not None and isinstance(active.get("metrics"), dict)
                else None
            )
            previous_selected_scale = (
                float(previous_scale_value)
                if type(previous_scale_value) in (int, float)
                and math.isfinite(float(previous_scale_value))
                and 0.0 < float(previous_scale_value) <= 1.0
                else None
            )
            update_scale_cap = (
                1.0 if active is None
                else min(0.25, max(0.015625, (previous_selected_scale or 0.0625) * 4.0))
            )
            update_scales = [
                scale for scale in base_update_scales if scale <= update_scale_cap
            ]
            if not update_scales:
                update_scales = [min(base_update_scales)]
            replay_metrics.update({
                "prior_selected_update_scale": previous_selected_scale,
                "update_scale_cap": float(update_scale_cap),
                "update_scale_cap_policy": (
                    "INITIAL_FULL_STEP" if active is None
                    else "MIN_0.25_MAX_4X_PREVIOUS_ACCEPTED_SCALE"
                ),
                "update_scale_schedule": list(update_scales),
            })
            attempts = []
            selected_scale = None
            candidate = model
            try:
                candidate.partial_fit(
                    *fit_arrays, steps=steps, log_every=max(1, steps // 4),
                    cancel_check=cancel_check, allow_optimizer_bootstrap=True,
                    train_encoder=(encoder_mode == "full"),
                    drift_control=drift_config, replay_start=replay_start,
                    update_scale=neuromod_scale,
                    replay_cohort_ranges=replay_cohort_ranges,
                    replay_reference_batches=replay_reference_batches,
                )
            except InterruptedError:
                return {"status":"CANCELLED","pending_rows":len(pending_by_id),
                        "scan_cursor":state["scan_cursor"],"checkpoint_committed":False,
                        "native_body_weights_changed":False}
            if cancel_check is not None and cancel_check():
                return {"status":"CANCELLED","pending_rows":len(pending_by_id),
                        "scan_cursor":state["scan_cursor"],"checkpoint_committed":False,
                        "native_body_weights_changed":False}

            candidate_drift_metrics = world_jepa_drift.summary(
                candidate._training_state.get("drift"), enabled=drift_config["enabled"]
            )
            candidate_gradient_projection = dict(
                getattr(candidate, "_last_gradient_projection", {})
            )
            candidate_gradient_projection["requested"] = replay_projection
            candidate_gradient_projection["fallback_reason"] = projection_fallback_reason
            candidate_gradient_projection["mode"] = replay_metrics["replay_projection_mode"]
            candidate_gradient_projection["constraint_session_count"] = replay_metrics["replay_constraint_session_count"]
            replay_metrics["replay_projection_constraint_source"] = candidate_gradient_projection.get("constraint_source")
            replay_metrics["replay_projection_reference_batch_count"] = candidate_gradient_projection.get("reference_batch_count", 0)
            replay_metrics["replay_projection_reference_rows_total"] = candidate_gradient_projection.get("reference_rows_total", 0)
            candidate_gradient_projection["optimizer_direction_scale"] = 1.0
            full_candidate_after = _parameter_snapshot(candidate)
            candidate_fit_steps_after = int(getattr(candidate, "_fit_steps", 0))

            for attempt_index, update_scale in enumerate(update_scales):
                if cancel_check is not None and cancel_check():
                    return {"status":"CANCELLED","pending_rows":len(pending_by_id),
                            "scan_cursor":state["scan_cursor"],"checkpoint_committed":False,
                            "native_body_weights_changed":False}
                _apply_parameter_interpolation(candidate, before, full_candidate_after, update_scale)
                candidate_after = _parameter_snapshot(candidate)
                candidate_encoder_delta = _group_delta(before, candidate_after, ("enc",))
                candidate_predictor_delta = _group_delta(before, candidate_after, ("preds",))
                candidate_parameter_delta = math.sqrt(
                    candidate_encoder_delta ** 2 + candidate_predictor_delta ** 2
                )
                candidate_ema_delta = _group_delta(before, candidate_after, ("tgt",))

                if active is None:
                    candidate_old_guard_cohort_after = {}
                    candidate_old_guard_cohort_gate = {
                        "accepted": True, "reason": "NO_PRIOR_GUARD_COHORT", "cohorts": {},
                    }
                    candidate_old_guard_cohort_retained = True
                else:
                    candidate_old_guard_cohort_after = (
                        _retention_cohort_losses(
                            candidate, old_guard_cohorts, target_snapshot=old_target_snapshot
                        )
                        if not old_guard_cohort_overflow else {}
                    )
                    candidate_old_guard_cohort_gate = _retention_cohort_gate(
                        old_guard_cohort_before,
                        candidate_old_guard_cohort_after,
                        overflow=old_guard_cohort_overflow,
                    )
                    candidate_old_guard_cohort_retained = bool(
                        candidate_old_guard_cohort_gate["accepted"]
                    )

                if new_guard_rows:
                    candidate_new_guard_cohort_after = (
                        _retention_cohort_losses(
                            candidate, new_guard_cohorts, target_snapshot=old_target_snapshot
                        )
                        if not new_guard_cohort_overflow else {}
                    )
                    candidate_new_guard_cohort_gate = _retention_cohort_gate(
                        new_guard_cohort_before,
                        candidate_new_guard_cohort_after,
                        overflow=new_guard_cohort_overflow,
                    )
                else:
                    candidate_new_guard_cohort_after = {}
                    candidate_new_guard_cohort_gate = {
                        "accepted": True, "reason": "NO_CURRENT_GUARD_COHORT", "cohorts": {},
                    }
                candidate_new_guard_cohort_retained = bool(
                    candidate_new_guard_cohort_gate["accepted"]
                )
                candidate_guard_accepted = bool(
                    candidate_old_guard_cohort_retained
                    and candidate_new_guard_cohort_retained
                )

                attempts.append({
                    "update_scale": float(update_scale),
                    "old_guard_cohort_retained": bool(candidate_old_guard_cohort_retained),
                    "old_guard_cohort_gate": candidate_old_guard_cohort_gate,
                    "new_guard_cohort_retained": bool(candidate_new_guard_cohort_retained),
                    "new_guard_cohort_gate": candidate_new_guard_cohort_gate,
                    "guard_accepted": bool(candidate_guard_accepted),
                })
                if candidate_guard_accepted:
                    selected_scale = float(update_scale)
                    break

            effective_scale = (
                float(selected_scale) if selected_scale is not None else float(update_scales[-1])
            )
            candidate_gradient_projection["effective_update_scale"] = effective_scale
            replay_metrics["line_search_mode"] = "POST_FIT_PARAMETER_INTERPOLATION"
            replay_metrics["line_search_optimizer_passes"] = 1
            replay_metrics["selected_update_scale"] = selected_scale
            # Final holdouts are evaluated once after guard-based scale selection.
            # They never choose a retry scale and are never used for gradients.
            candidate_holdout_after = candidate.prediction_loss(*holdout)
            candidate_shuffled_loss = candidate.prediction_loss(
                holdout[0], np.roll(holdout[1], 1, axis=0), holdout[2]
            )
            candidate_zero_loss = candidate.prediction_loss(
                holdout[0], np.zeros_like(holdout[1]), holdout[2]
            )
            candidate_old_holdout_after = (
                candidate.prediction_loss(
                    *old_holdout, target_snapshot=old_target_snapshot
                )
                if old_holdout_before is not None else None
            )
            candidate_old_holdout_cohort_after = (
                _retention_cohort_losses(
                    candidate, old_holdout_cohorts, target_snapshot=old_target_snapshot
                )
                if old_holdout_cohorts is not None else {}
            )
            candidate_old_holdout_cohort_gate = _retention_cohort_gate(
                old_holdout_cohort_before,
                candidate_old_holdout_cohort_after,
                overflow=old_holdout_cohort_overflow,
            )
            candidate_retention_delta = (
                None if old_holdout_before is None
                else float(candidate_old_holdout_after - old_holdout_before)
            )
            candidate_holdout_improved = bool(candidate_holdout_after < holdout_before)
            candidate_negative_controls_separated = bool(
                candidate_holdout_after < candidate_shuffled_loss
                and candidate_holdout_after < candidate_zero_loss
            )
            candidate_old_holdout_retention_tolerance = (
                None if old_holdout_before is None
                else max(1e-12, abs(old_holdout_before) * RETENTION_RELATIVE_TOLERANCE)
            )
            candidate_old_holdout_retained = bool(
                old_holdout_before is None
                or (candidate_old_holdout_after is not None
                    and candidate_old_holdout_after
                    <= old_holdout_before + candidate_old_holdout_retention_tolerance)
            )
            candidate_old_holdout_cohort_retained = bool(
                candidate_old_holdout_cohort_gate["accepted"]
            )
            candidate_retention_gate_accepted = bool(
                candidate_old_holdout_retained and candidate_old_holdout_cohort_retained
            )
            candidate_accepted = bool(
                selected_scale is not None
                and candidate_new_guard_cohort_retained
                and candidate_holdout_improved
                and candidate_negative_controls_separated
                and candidate_retention_gate_accepted
            )

            model = candidate
            after = candidate_after
            holdout_after = candidate_holdout_after
            shuffled_action_loss = candidate_shuffled_loss
            zero_action_loss = candidate_zero_loss
            old_holdout_after = candidate_old_holdout_after
            fit_steps_after = candidate_fit_steps_after
            drift_metrics = candidate_drift_metrics
            gradient_projection = candidate_gradient_projection
            encoder_delta = candidate_encoder_delta
            predictor_delta = candidate_predictor_delta
            parameter_delta = candidate_parameter_delta
            ema_delta = candidate_ema_delta
            retention_delta = candidate_retention_delta
            holdout_improved = candidate_holdout_improved
            negative_controls_separated = candidate_negative_controls_separated
            old_holdout_retained = candidate_old_holdout_retained
            old_holdout_cohort_retained = candidate_old_holdout_cohort_retained
            retention_gate_accepted = candidate_retention_gate_accepted
            old_holdout_cohort_gate = candidate_old_holdout_cohort_gate
            utility_gate_accepted = bool(selected_scale is not None and candidate_accepted)
            replay_metrics["old_retention_target_reference"] = (
                "PRE_UPDATE_EMA_SNAPSHOT" if old_target_snapshot is not None else "NONE"
            )
            replay_metrics["old_retention_target_sha256"] = _target_snapshot_sha256(
                old_target_snapshot
            )
            replay_metrics["optimizer_steps_added"] = fit_steps_after - fit_steps_before
            replay_metrics["backtracking_attempts"] = len(attempts)
            replay_metrics["backtracking_scales"] = [
                item["update_scale"] for item in attempts
            ]
            replay_metrics["selected_update_scale"] = selected_scale
            replay_metrics["backtracking_trace"] = attempts
            replay_metrics["backtracking_selection_fold"] = (
                "source_disjoint_training_guard" if active is not None else "single_initial_step"
            )
            replay_metrics["current_guard_selection_fold"] = (
                "source_disjoint_current_training_guard" if new_guard_rows else "NONE"
            )
            replay_metrics["current_guard_cohort_after"] = candidate_new_guard_cohort_after
            replay_metrics["current_guard_cohort_gate"] = candidate_new_guard_cohort_gate
            replay_metrics["current_guard_gate_accepted"] = candidate_new_guard_cohort_retained
            replay_metrics["holdout_used_for_backtracking"] = False
            replay_metrics["guard_gate_accepted"] = bool(candidate_guard_accepted)
            replay_metrics["old_guard_cohort_gate"] = candidate_old_guard_cohort_gate
            replay_metrics["retention_relative_tolerance"] = RETENTION_RELATIVE_TOLERANCE
            replay_metrics["old_holdout_retention_tolerance"] = (
                candidate_old_holdout_retention_tolerance
            )
            if not utility_gate_accepted:
                persisted = self._persist_pending(state, version, pending_by_id, next_cursor)
                if persisted != "PERSISTED":
                    return {"status": persisted, "pending_rows": len(pending_by_id),
                            "scan_cursor": state["scan_cursor"],
                            "native_body_weights_changed": False}
                return {
                    "status": "UTILITY_GATE_REJECTED",
                    "utility_gate_accepted": False,
                    "holdout_improved": holdout_improved,
                    "negative_controls_separated": negative_controls_separated,
                    "old_holdout_retained": old_holdout_retained,
                    "old_holdout_cohort_retained": old_holdout_cohort_retained,
                    "retention_gate_accepted": retention_gate_accepted,
                    "holdout_loss_before": float(holdout_before),
                    "holdout_loss_after": float(holdout_after),
                    "shuffled_action_holdout_loss": float(shuffled_action_loss),
                    "zero_action_holdout_loss": float(zero_action_loss),
                    "old_holdout_loss_before": None if old_holdout_before is None else float(old_holdout_before),
                    "old_holdout_loss_after": None if old_holdout_after is None else float(old_holdout_after),
                    "old_holdout_retention_delta": retention_delta,
                    "old_holdout_cohort_gate": old_holdout_cohort_gate,
                    "drift_control": drift_metrics,
                    "gradient_projection": gradient_projection,
                    "parameter_delta_norm": float(parameter_delta),
                    "encoder_parameter_delta_norm": float(encoder_delta),
                    "predictor_parameter_delta_norm": float(predictor_delta),
                    "encoder_mode": encoder_mode,
                    "encoder_updated": bool(encoder_delta > 0.0),
                    "ema_updated": bool(ema_delta > 0.0),
                    "ema_target_delta_norm": float(ema_delta),
                    "fit_steps_before": fit_steps_before,
                    "fit_steps_after": fit_steps_after,
                    "new_train_rows": len(new_train_rows),
                    "replay_candidate_rows": len(old_fit_rows),
                    **replay_metrics,
                    "fit_rows": len(fit_rows),
                    "fit_action_ids": [row["action_id"] for row in fit_rows],
                    "new_train_action_ids": [row["action_id"] for row in new_fit_rows],
                    "pending_rows": len(pending_by_id),
                    "scan_cursor": next_cursor,
                    "native_body_weights_changed": False,
                    "native_body_consumed": False,
                    "runtime_wired": False,
                }
            # The accepted candidate is the first scale that passed all utility and
            # aggregate/per-session retention gates; rejected trials are never published.
            if cancel_check is not None and cancel_check():
                return {"status":"CANCELLED","pending_rows":len(pending_by_id),
                        "scan_cursor":state["scan_cursor"],"checkpoint_committed":False,
                        "native_body_weights_changed":False}
            new_guard_ids = {row["action_id"] for row in new_guard_rows}
            checkpoint_rows = [
                row for row in experience_rows if row["action_id"] not in new_guard_ids
            ]
            checkpoint_ids = {row["action_id"] for row in checkpoint_rows}
            checkpoint_fingerprints = {
                action_id: prior_fingerprints[action_id] for action_id in checkpoint_ids
            }
            checkpoint_train_ids = [
                action_id for action_id in train_ids if action_id in checkpoint_ids
            ]
            checkpoint_holdout_ids = [
                action_id for action_id in holdout_ids if action_id in checkpoint_ids
            ]
            if set(checkpoint_train_ids) | set(checkpoint_holdout_ids) != checkpoint_ids:
                raise ValueError("checkpoint rows are not covered by the source-disjoint split")
            receiver_train_rows = list(new_fit_rows) + list(old_fit_rows)
            receiver_heads, receiver_metrics = _fit_role_receivers(
                model, _arrays(receiver_train_rows), holdout,
                receiver_train_rows, holdout_rows,
            )
            receiver_cohort_after = _receiver_cohort_losses(
                model, receiver_heads, old_holdout_cohorts
            )
            receiver_retention_gates = {}
            for role in ROLE_TARGETS:
                gate = _retention_cohort_gate(
                    old_receiver_cohort_before[role], receiver_cohort_after[role],
                    overflow=old_holdout_cohort_overflow,
                )
                receiver_retention_gates[role] = gate
                receiver_metrics[role.lower() + "_old_session_retention_gate"] = gate
            receiver_metrics["receiver_old_session_retention_gate_accepted"] = all(
                gate["accepted"] is True for gate in receiver_retention_gates.values()
            )
            source_sha = _cohort_sha(checkpoint_rows)
            if cancel_check is not None and cancel_check():
                return {"status":"CANCELLED","pending_rows":len(pending_by_id),
                        "scan_cursor":state["scan_cursor"],"checkpoint_committed":False,
                        "native_body_weights_changed":False}
            checkpoint_name = "jepa-" + uuid.uuid4().hex + ".npz"
            checkpoint_path = self.home / checkpoint_name
            saved = world_jepa_shadow_checkpoint.save(model, checkpoint_path, source_sha)
            checkpoint_after = _sha(saved.get("sha256"))
            if cancel_check is not None and cancel_check():
                try: checkpoint_path.unlink(missing_ok=True)
                except OSError: pass
                return {"status":"CANCELLED","pending_rows":len(pending_by_id),
                        "scan_cursor":state["scan_cursor"],"checkpoint_committed":False,
                        "native_body_weights_changed":False}
            previous_updates = int(active["self_state"].get("update_count", 0)) if active else 0
            metrics = {
                "source_verified": True, "verified_receipts": len(receipts),
                "rejected_receipts": rejected, "censored_skipped": censored_skipped,
                "scanned_rows": scanned, "has_more": has_more,
                "scan_cursor_before": state["scan_cursor"], "scan_cursor_after": next_cursor,
                "replay_candidate_rows": len(old_fit_rows),
                **replay_metrics,
                "new_train_rows": len(new_train_rows),
                "new_fit_rows": len(new_fit_rows),
                "new_guard_rows": len(new_guard_rows),
                "new_guard_action_ids": sorted(new_guard_ids),
                "new_holdout_rows": len(set(new_ids) & set(holdout_ids)),
                "fit_rows": len(fit_rows),
                "fit_action_ids": [row["action_id"] for row in fit_rows],
                "new_train_action_ids": [row["action_id"] for row in new_fit_rows],
                "checkpoint_experience_rows": len(checkpoint_rows),
                "checkpoint_processed_rows": len(checkpoint_ids),
                "checkpoint_train_rows": len(checkpoint_train_ids),
                "checkpoint_holdout_rows": len(checkpoint_holdout_ids),
                "pending_rows": len(new_guard_rows),
                "train_rows": len(train_ids), "holdout_rows": len(holdout_ids),
                "train_source_count": split["manifest"]["train_source_count"],
                "holdout_source_count": split["manifest"]["holdout_source_count"],
                "train_holdout_id_disjoint": True,
                "train_holdout_source_disjoint": split["manifest"]["source_disjoint"],
                "train_holdout_source_sha256_disjoint": split["manifest"]["source_sha256_disjoint"],
                "train_holdout_content_disjoint": split["manifest"]["within_supplied_records_content_disjoint"],
                "holdout_loss_before": float(holdout_before), "holdout_loss_after": float(holdout_after),
                "holdout_loss_delta": float(holdout_after - holdout_before),
                "holdout_improved": holdout_improved,
                "shuffled_action_holdout_loss": float(shuffled_action_loss),
                "zero_action_holdout_loss": float(zero_action_loss),
                "negative_controls_separated": negative_controls_separated,
                "utility_gate_accepted": utility_gate_accepted,
                "update_scale": selected_scale,
                "old_holdout_retained": old_holdout_retained,
                "old_holdout_cohort_retained": old_holdout_cohort_retained,
                "retention_gate_accepted": retention_gate_accepted,
                "old_holdout_loss_before": None if old_holdout_before is None else float(old_holdout_before),
                "old_holdout_loss_after": None if old_holdout_after is None else float(old_holdout_after),
                "old_holdout_retention_delta": retention_delta,
                "old_holdout_cohort_gate": old_holdout_cohort_gate,
                "parameter_delta_norm": float(parameter_delta),
                "encoder_parameter_delta_norm": float(encoder_delta),
                "predictor_parameter_delta_norm": float(predictor_delta),
                "encoder_mode": encoder_mode,
                "encoder_updated": bool(encoder_delta > 0.0),
                "ema_updated": bool(ema_delta > 0.0),
                "ema_target_delta_norm": float(ema_delta),
                "fit_steps_before": fit_steps_before, "fit_steps_after": fit_steps_after,
                "checkpoint_sha_before": checkpoint_before, "checkpoint_sha_after": checkpoint_after,
                "optimizer_moments_persisted": saved.get("optimizer_state_persisted") is True,
                "inverse_dynamics_optimizer_persisted": saved.get("optimizer_state_persisted") is True,
                "optimizer_state_bootstrapped": saved.get("optimizer_state_bootstrapped") is True,
                "drift_control": drift_metrics,
                "gradient_projection": gradient_projection,
            }
            metrics.update(receiver_metrics)
            record = {
                "checkpoint": checkpoint_name, "checkpoint_sha256": checkpoint_after,
                "source_sha256": source_sha, "processed_ids": sorted(checkpoint_ids),
                "fingerprints": checkpoint_fingerprints, "experience_rows": checkpoint_rows,
                "train_ids": checkpoint_train_ids, "holdout_ids": checkpoint_holdout_ids,
                "receiver_heads": receiver_heads, "metrics": metrics,
                "self_state": {"update_count": previous_updates + 1,
                               "last_prediction_error": float(holdout_after),
                               "last_parameter_delta_norm": float(parameter_delta),
                               "last_retention_delta": retention_delta,
                               "last_retention_gate_accepted": retention_gate_accepted,
                               "last_cohort_retention": old_holdout_cohort_gate,
                               "last_scan_cursor": next_cursor},
                "fit_steps": fit_steps_after, "scan_cursor": next_cursor,
            }
            next_state = {"schema": STATE_SCHEMA, "revision": REVISION,
                          "active": record, "previous": active, "scan_cursor": next_cursor,
                          "pending_rows": list(new_guard_rows)}
            if cancel_check is not None and cancel_check():
                try: checkpoint_path.unlink(missing_ok=True)
                except OSError: pass
                return {"status":"CANCELLED","pending_rows":len(pending_by_id),
                        "scan_cursor":state["scan_cursor"],"checkpoint_committed":False,
                        "native_body_weights_changed":False}
            try:
                self.store.set_state(STATE_KEY, next_state, expected=version)
            except ValueError as exc:
                try:
                    checkpoint_path.unlink(missing_ok=True)
                except OSError:
                    pass
                if "Stale state write" in str(exc):
                    return {"status": "CONCURRENT_STATE_CONFLICT_RETRY",
                            "new_receipts": len(new_ids), "checkpoint_discarded": True,
                            "native_body_weights_changed": False}
                raise
            except Exception:
                try:
                    checkpoint_path.unlink(missing_ok=True)
                except OSError:
                    pass
                raise
            pruned_checkpoints, prune_errors = self._prune_checkpoints(next_state)
            return {
                "status": "UPDATED_EXPERIMENTAL_WORLD_JEPA",
                "verified_receipts": len(receipts), "orphan_checkpoints_removed": pruned_checkpoints,
                "checkpoint_prune_errors": prune_errors, "rejected_receipts": rejected,
                "censored_skipped": censored_skipped, "scanned_rows": scanned,
                "has_more": has_more, "new_receipts": len(new_ids),
                "processed": len(checkpoint_ids), "scan_cursor": next_cursor,
                "pending_rows": len(new_guard_rows),
                "checkpoint_sha256": checkpoint_after, "source_sha256": source_sha,
                "metrics": metrics, "utility_gate_accepted": True,
                "native_body_weights_changed": False,
                "native_body_consumed": False, "runtime_wired": False,
                "scope": "WORLD_JEPA_EMA_SELF_MEMORY_AND_B1_B2_NUMERIC_SHADOW",
            }

    def restore(self):
        with self._locked(False):
            state, _ = self._read_state()
            active = state["active"]
            if active is None:
                return {"status": "NO_CHECKPOINT"}
            model = self._load_model(active)
            return {
                "status": "RESTORED",
                "checkpoint_sha256": active["checkpoint_sha256"],
                "fit_steps": int(model._fit_steps),
                "processed": len(active["processed_ids"]),
                "native_body_weights_changed": False,
            }


    def rollback(self):
        with self._locked(True):
            state, version = self._read_state()
            active, previous = state["active"], state["previous"]
            if previous is None:
                return {"status": "NO_PREVIOUS_CHECKPOINT"}
            self._load_model(previous)
            rollback_cursor = previous["scan_cursor"]
            self.store.set_state(
                STATE_KEY,
                {"schema": STATE_SCHEMA, "revision": REVISION,
                 "active": previous, "previous": active, "scan_cursor": rollback_cursor,
                 "pending_rows": []},
                expected=version,
            )
            return {"status": "ROLLED_BACK", "checkpoint_sha256": previous["checkpoint_sha256"],
                    "processed": len(previous["processed_ids"]), "scan_cursor": rollback_cursor,
                    "native_body_weights_changed": False}


    def readout(self, role, state, action):
        if role not in ROLE_TARGETS:
            raise ValueError("unknown receiver role")
        vector = _vector(state, 4)
        if action not in world_model.ACTIONS:
            raise ValueError("unknown action")
        with self._locked(False):
            stored, _ = self._read_state()
            active = stored["active"]
            if active is None:
                raise ValueError("WorldJEPA checkpoint unavailable")
            model = self._load_model(active)
            utility = receiver_utility_gate(active.get("metrics"), role)
            if not utility["accepted"]:
                return {
                    "role": role,
                    "status": "RECEIVER_UTILITY_REJECTED",
                    "receiver_utility": utility,
                    "checkpoint_sha256": active["checkpoint_sha256"],
                    "source_sha256": active["source_sha256"],
                    "native_body_consumed": False,
                    "native_body_weights_changed": False,
                }
            x = np.asarray([vector + [0.0, 0.0, 0.0]], dtype=np.float64)
            a = np.asarray([world_model.onehot(action)], dtype=np.float64)
            latent, spread = model.predict(x, a)
            head = active["receiver_heads"][role]
            weights = np.asarray(head["weights"], dtype=np.float64)
            bias = np.asarray(head["bias"], dtype=np.float64)
            prediction = latent[0] @ weights + bias
            if not np.isfinite(prediction).all():
                raise ValueError("nonfinite receiver prediction")
            if role == "B1_DETAIL":
                output = {
                    "predicted_action_duration_s": max(0.0, math.expm1(min(20.0, float(prediction[0])))),
                    "predicted_output_characters": max(0.0, math.expm1(min(20.0, float(prediction[1]) * 8.0))),
                }
            elif role == "B2_GIST":
                output = {"predicted_success_probability": float(np.clip(prediction[0], 0.0, 1.0))}
            else:
                output = {
                    "predicted_action_duration_s": max(0.0, math.expm1(min(20.0, float(prediction[0])))),
                    "predicted_success_probability": float(np.clip(prediction[1], 0.0, 1.0)),
                    "predicted_output_characters": max(0.0, math.expm1(min(20.0, float(prediction[2]) * 8.0))),
                }
            uncertainty = float(np.asarray(spread).reshape(-1)[0])
            if not math.isfinite(uncertainty):
                raise ValueError("nonfinite receiver uncertainty")
            return {"role": role, "prediction": output, "uncertainty": uncertainty,
                    "checkpoint_sha256": active["checkpoint_sha256"],
                    "source_sha256": active["source_sha256"], "status": "SHADOW_READOUT_ONLY",
                    "receiver_utility": utility,
                    "native_body_consumed": False, "native_body_weights_changed": False}

    def recall(self, state, action, limit=5):
        """Source-linked numeric episodic recall over the persistent T8 replay."""
        vector = _vector(state, 4)
        if action not in world_model.ACTIONS:
            raise ValueError("unknown action")
        if type(limit) is not int or not 1 <= limit <= 32:
            raise ValueError("memory recall limit")
        with self._locked(False):
            stored, _ = self._read_state()
            active = stored["active"]
            if active is None:
                return {"status": "NO_MEMORY", "items": []}
            model = self._load_model(active)
            query = np.asarray([vector + [0.0, 0.0, 0.0]], dtype=np.float64)
            query_latent = model.latent(query, target=False)[0]
            candidates = []
            for row in active["experience_rows"]:
                if row["a"] != action:
                    continue
                x = np.asarray([row["s"] + [0.0, 0.0, 0.0]], dtype=np.float64)
                latent = model.latent(x, target=False)[0]
                distance = float(np.linalg.norm(latent - query_latent))
                if not math.isfinite(distance):
                    continue
                y = row["y"]
                candidates.append({
                    "distance": distance, "action_id": row["action_id"],
                    "source_id": row["source_id"], "source_sha256": row["source_sha256"],
                    "outcome_sha256": row["outcome_sha256"], "created": row["created"],
                    "observed_outcome": {
                        "duration_s": math.expm1(min(20.0, y[0])),
                        "success": bool(y[1] >= 0.5),
                        "output_characters": math.expm1(min(20.0, y[2] * 8.0)),
                    },
                })
            candidates.sort(key=lambda item: (item["distance"], item["created"], item["action_id"]))
            items = candidates[:limit]
            for item in items:
                item["distance"] = round(item["distance"], 8)
            return {"status": "MEMORY_RECALL_SHADOW", "items": items,
                    "checkpoint_sha256": active["checkpoint_sha256"],
                    "source_sha256": active["source_sha256"],
                    "native_memory_consumed": False, "native_body_consumed": False}

@contextmanager
def source_forget_guard(store, source_id):
    """Serialize source deletion with JEPA updates and refuse false unlearning.

    Replay rows are bounded, but their parameter influence can outlive row
    eviction. Check each retained checkpoint's full scanned T8 history, not
    only its current replay rows. Pending-only rows are discarded before the
    source is deleted; any source that may have trained active/rollback weights
    blocks deletion until a real JEPA rebuild/forget path exists.
    """
    if type(source_id) is not str or not source_id or len(source_id) > 256:
        raise ValueError("invalid WorldJEPA source identity")

    root = Path(store.home) / "world_jepa"
    consumer = WorldJEPAStoreConsumer(
        store, root, learning_enabled=False
    )
    with consumer._locked(True):
        state, version = consumer._read_state()
        pending_rows = state["pending_rows"]
        pending_for_source = [
            row["action_id"] for row in pending_rows
            if row["source_id"] == source_id
        ]

        for label, record in (
            ("active", state["active"]),
            ("rollback", state["previous"]),
        ):
            if record is None:
                continue
            if any(
                row["source_id"] == source_id
                for row in record["experience_rows"]
            ):
                raise ValueError(
                    "Source is retained by a WorldJEPA "
                    + label + " checkpoint; safe unlearning is not implemented"
                )

            cursor = record["scan_cursor"]
            if cursor <= 0:
                continue
            query = (
                "SELECT a.id FROM actions a "
                "JOIN events e ON e.id=a.event_id "
                "WHERE a.rowid<=? AND e.source_id=? "
                "AND a.outcome IS NOT NULL AND a.expected LIKE ? "
                "AND a.status IN ('FINAL','FAILED','ERROR','DEADLINE','REJECTED')"
            )
            params = [cursor, source_id, '%"forecast"%']
            if pending_for_source:
                placeholders = ",".join("?" for _ in pending_for_source)
                query += " AND a.id NOT IN (" + placeholders + ")"
                params.extend(pending_for_source)
            query += " LIMIT 1"
            if store.rows(query, tuple(params)):
                raise ValueError(
                    "Source may have trained a WorldJEPA "
                    + label + " checkpoint (including evicted replay rows); "
                    "safe unlearning is not implemented"
                )

        if pending_for_source:
            next_state = dict(state)
            next_state["pending_rows"] = [
                row for row in pending_rows if row["source_id"] != source_id
            ]
            try:
                store.set_state(STATE_KEY, next_state, expected=version)
            except ValueError as exc:
                if "Stale state write" in str(exc):
                    raise ValueError(
                        "WorldJEPA state changed during source forget; retry"
                    ) from exc
                raise

        removed, errors = consumer._prune_checkpoints(state)
        if errors:
            raise OSError(
                "WorldJEPA orphan checkpoint cleanup failed; source deletion refused"
            )
        yield {
            "pending_rows_removed": len(pending_for_source),
            "orphan_checkpoints_removed": removed,
        }

