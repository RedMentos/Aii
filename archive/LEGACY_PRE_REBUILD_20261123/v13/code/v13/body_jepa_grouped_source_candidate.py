"""Default-OFF source-group preflight for experimental Body-JEPA contrastive loss.

No Store authentication, native runner, adapter export, Runtime registration or Age
permission. A caller must separately authenticate every supplied source digest.
Repeated views of one authenticated source are masked as false negatives.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

REVISION = "v13-bjepa-grouped-source-research-candidate-v1"
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_PATHS = frozenset(("B1_DETAIL", "B2_GIST"))


def _row(row):
    if type(row) is not dict:
        raise ValueError("SOURCE_ROW_TYPE_RED")
    keys = ("path", "source_id", "source_sha256", "context_source_sha256",
            "target_source_sha256", "view_id", "eligibility")
    if any(k not in row for k in keys):
        raise ValueError("SOURCE_ROW_FIELDS_RED")
    if type(row["path"]) is not str or row["path"] not in _PATHS:
        raise ValueError("SOURCE_PATH_RED")
    for key in ("source_id", "view_id"):
        value = row[key]
        if type(value) is not str or not 1 <= len(value) <= 128 or value.strip() != value or not value.isprintable():
            raise ValueError("SOURCE_ID_RED")
    for key in ("source_sha256", "context_source_sha256", "target_source_sha256"):
        value = row[key]
        if type(value) is not str or not _HEX.fullmatch(value):
            raise ValueError("SOURCE_DIGEST_RED")
    if not (row["source_sha256"] == row["context_source_sha256"]
            == row["target_source_sha256"]):
        raise ValueError("SOURCE_TARGET_MISMATCH_RED")
    weight = row["eligibility"]
    if type(weight) not in (int, float) or not 0 <= weight <= 1 or not math.isfinite(weight):
        raise ValueError("ELIGIBILITY_RED")
    return {key: row[key] for key in keys}


def validate_training_rows(rows, *, heldout_rows=()):
    """Validate metadata, source-group negatives and disjoint heldout provenance.

    Source hashes here are *claims*, not proof of trusted Store origin. This
    preflight is only suitable after separate Store/source authentication.
    """
    if type(rows) not in (list, tuple) or not 2 <= len(rows) <= 64:
        raise ValueError("TRAIN_ROWS_BOUND_RED")
    if type(heldout_rows) not in (list, tuple) or len(heldout_rows) > 256:
        raise ValueError("HELDOUT_ROWS_BOUND_RED")
    train = [_row(row) for row in rows]
    heldout = [_row(row) for row in heldout_rows]
    paths = {row["path"] for row in train + heldout}
    if len(paths) != 1:
        raise ValueError("MIXED_BODY_PATH_RED")
    views = [row["view_id"] for row in train + heldout]
    if len(views) != len(set(views)):
        raise ValueError("DUPLICATE_VIEW_RED")
    source_to_hash = {}
    hash_to_source = {}
    for row in train + heldout:
        sid, sha = row["source_id"], row["source_sha256"]
        if sid in source_to_hash and source_to_hash[sid] != sha:
            raise ValueError("SOURCE_ID_REBOUND_RED")
        if sha in hash_to_source and hash_to_source[sha] != sid:
            raise ValueError("SOURCE_HASH_ALIAS_RED")
        source_to_hash[sid] = sha
        hash_to_source[sha] = sid
    groups = [row["source_sha256"] for row in train]
    if len(set(groups)) < 2:
        raise ValueError("NO_GENUINE_NEGATIVE_RED")
    if not any(row["eligibility"] > 0 for row in train):
        raise ValueError("ZERO_ELIGIBILITY_RED")
    if set(groups) & {row["source_sha256"] for row in heldout}:
        raise ValueError("HELDOUT_SOURCE_LEAK_RED")
    canonical = {"revision": REVISION, "train": train, "heldout": heldout}
    fingerprint = hashlib.sha256(json.dumps(canonical, sort_keys=True,
                                         separators=(",", ":"),
                                         ensure_ascii=True).encode()).hexdigest()
    return {"groups": tuple(groups),
            "weights": tuple(float(row["eligibility"]) for row in train),
            "source_group_count": len(set(groups)),
            "repeated_view_count": len(groups) - len(set(groups)),
            "cohort_sha256": fingerprint,
            "path": train[0]["path"],
            "source_authentication": "REQUIRED_EXTERNAL",
            "authority": 0, "native_calls": 0,
            "runtime_jepa_weight": 0, "body_jepa_available": False,
            "utility_proven": False, "redmi_measured": False}


def research_loss(torch, student, target, rows, *, heldout_rows=(), temperature=0.1):
    """Source-group masked differentiable loss; no target gradient or authority."""
    binding = validate_training_rows(rows, heldout_rows=heldout_rows)
    from .body_jepa_contrastive_shadow import loss_and_metrics
    loss, metrics = loss_and_metrics(torch, student, target,
                                     temperature=temperature,
                                     weights=binding["weights"],
                                     groups=binding["groups"])
    return loss, {**metrics, **{k: v for k, v in binding.items()
                               if k not in ("groups", "weights")}}
