"""Run12A: experimental contrastive target-discrimination loss for Body-JEPA SHADOW.

This is an alternative to (not a replacement for) the canonical EMA cosine
objective. No model runner, trainer, learning approval or production consumer.
Torch is injected by caller to keep the Age0 import path lightweight.
"""
from __future__ import annotations

import math

REVISION = "body-jepa-contrastive-shadow-run12a-v1"
MAX_BATCH = 64
MAX_DIM = 4096


def _require(ok, code):
    if not ok:
        raise ValueError(code)


def _permutation(perm, n):
    if perm is None:
        return list(range(n))
    _require(type(perm) in (list, tuple) and len(perm) == n,
             "PERMUTATION_SHAPE_RED")
    _require(all(type(i) is int for i in perm)
             and sorted(perm) == list(range(n))
             and all(i != j for i, j in enumerate(perm)),
             "DERANGEMENT_RED")
    return list(perm)


def loss_and_metrics(torch, student, target, *, temperature=0.1,
                     weights=None, groups=None, permutation=None):
    """Return (differentiable loss, detached metrics); no target gradients.

    Source groups mask *only* off-diagonal false negatives. The candidate
    refuses a bank without any genuine negatives rather than fabricating
    evidence. A derangement is a negative control and cannot use groups here.
    """
    _require(type(temperature) in (int, float)
             and math.isfinite(temperature)
             and 0.01 <= temperature <= 1.0, "TEMPERATURE_RED")
    _require(isinstance(student, torch.Tensor)
             and isinstance(target, torch.Tensor), "TENSOR_REQUIRED")
    _require(student.ndim == target.ndim == 2
             and student.shape == target.shape, "SHAPE_RED")
    n, dim = student.shape
    _require(2 <= n <= MAX_BATCH and 2 <= dim <= MAX_DIM, "SIZE_RED")
    _require(student.dtype in (torch.float32, torch.float64)
             and target.dtype == student.dtype
             and target.device == student.device, "DTYPE_OR_DEVICE_RED")
    _require(bool(torch.isfinite(student).all())
             and bool(torch.isfinite(target).all()), "NONFINITE_LATENT_RED")
    _require(bool((torch.linalg.vector_norm(student, dim=1) > 1e-8).all())
             and bool((torch.linalg.vector_norm(target, dim=1) > 1e-8).all()),
             "ZERO_LATENT_RED")
    perm = _permutation(permutation, n)
    _require(not (permutation is not None and groups is not None),
             "GROUPED_DERANGEMENT_UNSUPPORTED")
    if weights is None:
        w = torch.ones(n, dtype=student.dtype, device=student.device)
    else:
        w = torch.as_tensor(weights, device=student.device)
        _require(w.ndim == 1 and w.shape[0] == n
                 and w.dtype in (torch.float32, torch.float64),
                 "ELIGIBILITY_SHAPE_OR_TYPE_RED")
        w = w.to(dtype=student.dtype).detach()
        _require(bool(torch.isfinite(w).all())
                 and bool((w >= 0).all()) and bool(w.sum() > 0),
                 "ELIGIBILITY_VALUES_RED")
    with torch.no_grad():
        t = torch.nn.functional.normalize(target.detach(), dim=-1)
        spread = torch.linalg.vector_norm(t - t.mean(0))
        _require(bool(torch.isfinite(spread)) and float(spread) > 1e-5,
                 "TARGET_COLLAPSE_RED")
    t = t[torch.tensor(perm, dtype=torch.long, device=t.device)]
    s = torch.nn.functional.normalize(student, dim=-1)
    similarity = s @ t.T
    _require(bool(torch.isfinite(similarity).all()), "SIMILARITY_RED")
    mask = torch.zeros((n, n), dtype=torch.bool, device=s.device)
    if groups is not None:
        _require(type(groups) in (list, tuple) and len(groups) == n
                 and all(type(g) is str and 0 < len(g) <= 128 for g in groups),
                 "GROUPS_RED")
        for i in range(n):
            for j in range(n):
                if i != j and groups[i] == groups[j]:
                    mask[i, j] = True
    negative = ~mask
    negative.fill_diagonal_(False)
    _require(bool(negative.any(dim=1).all()), "NO_GENUINE_NEGATIVE_RED")
    logits = (similarity / temperature).masked_fill(mask, float("-inf"))
    labels = torch.arange(n, device=s.device)
    per_row = torch.nn.functional.cross_entropy(logits, labels, reduction="none")
    _require(bool(torch.isfinite(per_row).all()), "LOSS_NONFINITE_RED")
    result = (per_row * w).sum() / w.sum()
    with torch.no_grad():
        hard = similarity.masked_fill(~negative, float("-inf")).max(dim=1).values
        metrics = {
            "revision": REVISION,
            "batch_size": n,
            "dimension": dim,
            "temperature": float(temperature),
            "masked_false_negatives": int(mask.sum()),
            "minimum_negatives_per_row": int(negative.sum(dim=1).min()),
            "positive_cosine_mean": float(similarity.diagonal().mean()),
            "hard_negative_cosine_mean": float(hard.mean()),
            "diagonal_top1": int((logits.argmax(dim=1) == labels).sum()),
            "target_spread": float(spread),
            "permutation_control": permutation is not None,
            "target_detached": True,
            "authority": 0,
            "native_calls": 0,
            "jepa_weight_runtime": 0,
            "body_jepa_available": False,
            "redmi_measured": False,
            "utility_proven": False,
            "whole_system_complete": False,
        }
    return result, metrics
