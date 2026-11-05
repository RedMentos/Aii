"""Opt-in, evidence-only BP5 pair-integrity candidate.

This standalone reviewer does not alter the frozen b3pair module or any runtime
gate.  Its inputs (arrays, source identifiers, revisions, task, seed and HMAC
key) must come from the caller's trusted capture records.  In particular, an
HMAC authenticates the identifiers the caller supplies; it cannot prove that a
caller supplied the true source, that different identifiers have different
content, or that sender/receiver activations were actually captured together.

Use the *same* randomly generated, secret 32+-byte key for every cohort of a
comparison; keep it outside the manifest, code repository and public evidence.
HMACs reveal equality within a key scope.  Different keys cannot establish
cross-cohort disjointness.  Source identifiers should name stable source groups,
not merely capture runs: one source must keep the same identifier across seeds
and revisions.  This code never places identifiers or the key in the manifest.
The caller must also obtain each accuracy from the correct, separately verified
experiment; the provided aggregate values are not recomputed from predictions
and are not themselves cryptographically tied to the arrays by this module.

The GO verdict below is only a conservative precheck, not a significance test,
an authorization to use or train a model, or a B3/L2/L3 promotion.  Any later
use must separately verify the original ladder, consent and all other gates.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import numbers

import numpy as np

SCHEMA = "v13-b3pair-integrity-candidate-v1"
MIN_ROWS = 3000
MIN_SIGNAL_OVER_NO_MESSAGE = 0.02
MIN_HEADROOM = 0.03
_KEY_SCOPE = b"v13/bp5/source-id-key-check/v1"
_ID_SCOPE = b"v13/bp5/source-group-id/v1\x00"


def _text(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise ValueError("invalid " + name)
    return value


def _seed(value):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Integral):
        raise ValueError("invalid seed")
    value = int(value)
    if value < 0 or value >= 2**63:
        raise ValueError("invalid seed")
    return value


def _key(value):
    if not isinstance(value, bytes) or len(value) < 32:
        raise ValueError("source identity key must be at least 32 secret bytes")
    return value


def _source_tokens(source_ids, key, count):
    if isinstance(source_ids, (str, bytes)):
        raise ValueError("invalid source identities")
    try:
        ids = list(source_ids)
    except TypeError as exc:
        raise ValueError("invalid source identities") from exc
    if len(ids) != count:
        raise ValueError("source identity count differs")
    tokens = []
    for identity in ids:
        if isinstance(identity, str):
            identity = identity.encode("utf-8")
        if not isinstance(identity, bytes) or not identity or len(identity) > 4096:
            raise ValueError("invalid source identity")
        tokens.append(hmac.new(key, _ID_SCOPE + identity, hashlib.sha256).hexdigest())
    return tokens


def _tensor(value, label=False):
    try:
        arr = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid tensor") from exc
    if label:
        if arr.ndim != 1 or arr.dtype.kind not in "iu":
            raise ValueError("labels must be a one-dimensional integer array")
    else:
        if arr.ndim != 2 or arr.dtype.kind != "f" or arr.dtype.itemsize not in (2, 4, 8):
            raise ValueError("states must be a two-dimensional float16/32/64 array")
        if not np.isfinite(arr).all():
            raise ValueError("non-finite states")
        if not arr.shape[1]:
            raise ValueError("empty state dimension")
    if not arr.shape[0]:
        raise ValueError("no rows")
    return np.ascontiguousarray(arr)


def _digest(arr):
    # Bind dtype and shape as well as exact bytes; never cast values to float32.
    metadata = json.dumps([arr.dtype.str, list(arr.shape)], separators=(",", ":")).encode()
    return hashlib.sha256(metadata + b"\x00" + arr.tobytes(order="C")).hexdigest()


def build_manifest(sender, receiver, labels, *, sender_source_ids, receiver_source_ids,
                   key, sender_revision, receiver_revision, task, seed):
    """Bind caller-supplied trusted captures; no source identities are stored in cleartext."""
    key = _key(key)
    sender_revision = _text(sender_revision, "sender revision")
    receiver_revision = _text(receiver_revision, "receiver revision")
    task = _text(task, "task")
    seed = _seed(seed)
    sender, receiver, labels = _tensor(sender), _tensor(receiver), _tensor(labels, label=True)
    n = len(labels)
    if len(sender) != n or len(receiver) != n:
        raise ValueError("state and label row counts differ")
    source_tokens = _source_tokens(sender_source_ids, key, n)
    receiver_tokens = _source_tokens(receiver_source_ids, key, n)
    if source_tokens != receiver_tokens:
        raise ValueError("sender/receiver source order differs")
    row_hashes = []
    for i, source_token in enumerate(source_tokens):
        row_data = (source_token, _digest(sender[i:i+1]), _digest(receiver[i:i+1]),
                    _digest(labels[i:i+1]))
        row_hashes.append(hashlib.sha256("\x00".join(row_data).encode("ascii")).hexdigest())
    return {
        "schema": SCHEMA,
        "sender_revision": sender_revision,
        "receiver_revision": receiver_revision,
        "task": task,
        "seed": seed,
        "rows": n,
        "sender_sha256": _digest(sender),
        "receiver_sha256": _digest(receiver),
        "labels_sha256": _digest(labels),
        "source_key_check": hmac.new(key, _KEY_SCOPE, hashlib.sha256).hexdigest(),
        "source_hmac_sha256": source_tokens,
        "row_sha256": row_hashes,
    }


def verify(manifest, sender, receiver, labels, *, sender_source_ids, receiver_source_ids,
           key, sender_revision, receiver_revision, task, seed):
    """Rebuild every field from external trusted inputs, refusing extra/changed fields."""
    try:
        if type(manifest) is not dict:
            raise ValueError("manifest must be a dictionary")
        actual = build_manifest(sender, receiver, labels, sender_source_ids=sender_source_ids,
                                receiver_source_ids=receiver_source_ids, key=key,
                                sender_revision=sender_revision, receiver_revision=receiver_revision,
                                task=task, seed=seed)
        # Canonical JSON also distinguishes JSON true from 1 and rejects NaN.
        encoded = lambda obj: json.dumps(obj, sort_keys=True, allow_nan=False,
                                         separators=(",", ":"), ensure_ascii=True)
        if not hmac.compare_digest(encoded(manifest), encoded(actual)):
            return False, ["manifest differs from trusted capture inputs"]
    except (TypeError, ValueError, OverflowError) as exc:
        return False, ["invalid manifest or trusted capture: " + str(exc)]
    return True, []


def _accuracy(acc):
    if type(acc) is not dict:
        raise ValueError("accuracy must be a dictionary")
    names = ("NO_MESSAGE", "SCALAR", "L1", "L2")
    result = {}
    for name in names:
        value = acc.get(name)
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Real):
            raise ValueError("missing or invalid accuracy: " + name)
        value = float(value)
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("non-finite or out-of-range accuracy: " + name)
        result[name] = value
    return result


def _verified(manifest, inputs, key):
    """All inputs, including identity and metadata, are expected from trusted capture records."""
    if type(inputs) is not dict:
        return False, ["trusted capture must be a dictionary"]
    required = {"sender", "receiver", "labels", "sender_source_ids", "receiver_source_ids",
                "sender_revision", "receiver_revision", "task", "seed"}
    if set(inputs) != required:
        return False, ["trusted capture fields missing or extra"]
    return verify(manifest, **inputs, key=key)


def precheck(manifest_a, inputs_a, accuracy_a, manifest_b, inputs_b, accuracy_b, *, key):
    """Verify two pinned cohorts then check signal, control, headroom and source separation.

    A GO means only that this software precheck passed on both cohorts.  It does
    not establish significance, actual native pairing or L2/L3 authority.
    """
    reasons = []
    ok_a, why_a = _verified(manifest_a, inputs_a, key)
    ok_b, why_b = _verified(manifest_b, inputs_b, key)
    if not ok_a:
        reasons.extend("cohort A: " + x for x in why_a)
    if not ok_b:
        reasons.extend("cohort B: " + x for x in why_b)
    if reasons:
        return {"verdict": "NO_GO", "reasons": reasons}
    if (manifest_a["sender_revision"] != manifest_b["sender_revision"] or
        manifest_a["receiver_revision"] != manifest_b["receiver_revision"] or
        manifest_a["task"] != manifest_b["task"]):
        reasons.append("cohorts must use the same sender, receiver and task")
    if manifest_a["seed"] == manifest_b["seed"]:
        reasons.append("cohorts need distinct pinned seeds")
    if set(manifest_a["source_hmac_sha256"]) & set(manifest_b["source_hmac_sha256"]):
        reasons.append("source identities overlap across cohorts")
    for name, manifest, accuracy in (("A", manifest_a, accuracy_a), ("B", manifest_b, accuracy_b)):
        if manifest["rows"] < MIN_ROWS:
            reasons.append("cohort " + name + ": insufficient rows")
        # Repeated captures of one source do not create independent examples.
        # The original 3000-row rationale assumes enough distinct source groups.
        if len(set(manifest["source_hmac_sha256"])) < MIN_ROWS:
            reasons.append("cohort " + name + ": insufficient distinct source groups")
        try:
            acc = _accuracy(accuracy)
        except ValueError as exc:
            reasons.append("cohort " + name + ": " + str(exc))
            continue
        if acc["L1"] <= acc["NO_MESSAGE"] + MIN_SIGNAL_OVER_NO_MESSAGE:
            reasons.append("cohort " + name + ": L1 has insufficient no-message gain")
        if acc["L1"] <= acc["SCALAR"]:
            reasons.append("cohort " + name + ": L1 does not exceed scalar control")
        if acc["L1"] - acc["L2"] < MIN_HEADROOM:
            reasons.append("cohort " + name + ": insufficient L1-to-L2 headroom")
    return {"verdict": "NO_GO" if reasons else "GO", "reasons": reasons,
            "note": "Software precheck only; original L2 gate and L3 restrictions remain."}
