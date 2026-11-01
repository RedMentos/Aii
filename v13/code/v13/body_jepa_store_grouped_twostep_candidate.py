"""Run117CO BF-bound grouped Body-JEPA two-step synthetic Torch research.

Default OFF. No native model, Runtime integration, persistent weights or
learning authority. Existing strict USER event context/target SourceRefs are
authenticated by Run117BF and rechecked around every ephemeral tensor step.
"""
from __future__ import annotations

import hashlib
import math

from .body_jepa_grouped_source_candidate import research_loss
from .body_jepa_store_source_binding_shadow import (
    bind_store_rows, recheck_store_rows)

SEED = 117047
STEPS = 2


def _result(status, **extra):
    return {
        "schema": "v13.body_jepa_store_grouped_twostep_shadow.v1",
        "status": status,
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "world_jepa": "SHADOW", "jepa_weight": 0,
        "authority": 0, "learning_authority": 0,
        "delivery_authority": 0, "tool_dispatches": 0,
        "native_calls": 0, "model_weight_updates": 0,
        "synthetic_tensor_updates": 0, "output_committed": False,
        "model_exported": False, "redmi_measured": False,
        "utility_proven": False, "whole_system_complete": False,
        **extra,
    }




def run(torch, store, session, student_init, target, rows, *,
        heldout_rows=(), operator_opt_in=False, lr=0.05):
    if operator_opt_in is not True:
        return _result("OFF")
    if torch is None:
        return _result("TORCH_REQUIRED_RED")
    if (type(lr) not in (int, float) or not math.isfinite(lr)
            or not 0 < lr <= 0.1):
        return _result("LEARNING_RATE_RED")
    completed = 0
    try:
        binding = bind_store_rows(
            store, session, rows, heldout_rows=heldout_rows,
            operator_opt_in=True)
        if (not isinstance(student_init, torch.Tensor)
                or not isinstance(target, torch.Tensor)
                or student_init.shape != target.shape
                or student_init.ndim != 2
                or student_init.dtype != torch.float32
                or target.dtype != torch.float32
                or student_init.device != target.device
                or not bool(torch.isfinite(student_init).all())
                or not bool(torch.isfinite(target).all())):
            raise ValueError("SYNTHETIC_TENSOR_SHAPE_RED")
        student = torch.nn.Parameter(student_init.detach().clone())
        frozen = target.detach().clone()
        frozen_hash = hashlib.sha256(frozen.cpu().numpy().tobytes()).hexdigest()
        optimizer = torch.optim.SGD([student], lr=float(lr))
        losses, gradients, masked = [], [], []
        for _ in range(STEPS):
            recheck_store_rows(
                store, session, rows, binding,
                heldout_rows=heldout_rows, operator_opt_in=True)
            optimizer.zero_grad(set_to_none=True)
            loss, metrics = research_loss(
                torch, student, frozen, rows, heldout_rows=heldout_rows)
            if not bool(torch.isfinite(loss)):
                raise ValueError("NONFINITE_GROUPED_LOSS_RED")
            loss.backward()
            if student.grad is None:
                raise ValueError("NO_SYNTHETIC_GRADIENT_RED")
            grad = float(student.grad.detach().abs().sum())
            if not math.isfinite(grad) or grad <= 0:
                raise ValueError("NO_FINITE_GRADIENT_RED")
            optimizer.step()
            completed += 1
            recheck_store_rows(
                store, session, rows, binding,
                heldout_rows=heldout_rows, operator_opt_in=True)
            losses.append(float(loss.detach()))
            gradients.append(grad)
            masked.append(metrics["masked_false_negatives"])
        if (hashlib.sha256(frozen.cpu().numpy().tobytes()).hexdigest()
                != frozen_hash or frozen.grad is not None
                or target.grad is not None):
            raise ValueError("TARGET_NOT_FROZEN_RED")
        return _result(
            "STORE_GROUPED_TWO_STEP_SHADOW",
            seed=SEED, synthetic_tensor_updates=completed,
            source_authentication="EXACT_STORE_USER_EVENT_SPANS_PRE_POST",
            event_provenance_sha256=binding["event_provenance_sha256"],
            source_group_count=binding["source_group_count"],
            repeated_view_count=binding["repeated_view_count"],
            cohort_sha256=binding["cohort_sha256"],
            step_losses=losses, step_student_grad_abs_sum=gradients,
            masked_false_negatives=masked,
            target_frozen_sha256=frozen_hash)
    except (ValueError, TypeError, KeyError, AttributeError, OSError,
            OverflowError, RuntimeError):
        return _result("SOURCE_OR_TRAINING_INTEGRITY_RED",
                       synthetic_tensor_updates=completed)
