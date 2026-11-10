"""Offline B1/B2 candidate trial: measured heldout utility, never deploys weights.

The caller owns isolated candidate construction and independently authenticated
operator approval. This module never accepts review flags as authorization.
"""
import hashlib
import json
import math
from pathlib import Path
from .body_dataset_training_input import prepare_body_training_items

def _digest(path):
    data = Path(path).read_bytes()
    return hashlib.sha256(data).hexdigest()

def _loss(evaluate, candidate, items):
    scores = []
    for item in items:
        score = evaluate(candidate, item["prompt"], item["target"])
        if type(score) not in (float, int) or not math.isfinite(score) or score < 0:
            raise ValueError("invalid heldout loss")
        scores.append(float(score))
    if not scores:
        raise ValueError("empty heldout")
    return sum(scores) / len(scores)

def run_body_candidate_trial(directory, role, *, manifest_sha256, authorize,
                             make_candidate, train_candidate, evaluate,
                             max_items=256, max_retention_increase=0.0):
    """Train an isolated candidate only, compare identical heldout examples.

    authorize is a trusted operator-side callback, not a dataset field.
    make_candidate MUST return an independent candidate; train_candidate MUST
    modify only that candidate. This API cannot verify object isolation.
    Returns metrics and the candidate for separate human-controlled review;
    it never activates/deploys the candidate.
    """
    if (type(manifest_sha256) is not str or len(manifest_sha256) != 64
            or any(c not in "0123456789abcdef" for c in manifest_sha256)):
        raise ValueError("invalid pinned manifest digest")
    if type(max_retention_increase) not in (int, float) or not math.isfinite(max_retention_increase) or max_retention_increase < 0:
        raise ValueError("invalid retention tolerance")
    if not all(callable(f) for f in (authorize, make_candidate, train_candidate, evaluate)):
        raise TypeError("trusted callbacks required")
    manifest = Path(directory) / "manifest.json"
    if manifest.is_symlink() or _digest(manifest) != manifest_sha256:
        raise ValueError("manifest not pinned")
    train, heldout = prepare_body_training_items(directory, role, max_items=max_items)
    if not train or not heldout:
        raise ValueError("both partitions required")
    if _digest(manifest) != manifest_sha256:
        raise ValueError("manifest changed during read")
    if authorize(role, manifest_sha256) is not True:
        raise PermissionError("operator authorization denied")
    candidate = make_candidate(role)
    before = _loss(evaluate, candidate, heldout)
    train_candidate(candidate, train)
    after = _loss(evaluate, candidate, heldout)
    if _digest(manifest) != manifest_sha256:
        raise ValueError("manifest changed during trial")
    return {"role": role, "manifest_sha256": manifest_sha256,
            "train_rows": len(train), "heldout_rows": len(heldout),
            "heldout_before": before, "heldout_after": after,
            "heldout_delta": after - before,
            "retention_pass": after <= before + max_retention_increase,
            "deployment": "NOT_AUTHORIZED"}, candidate
