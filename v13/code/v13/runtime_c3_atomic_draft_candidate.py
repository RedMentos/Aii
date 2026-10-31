"""Isolated default-OFF Runtime C3 -> F1/F5 -> C5/C6 atomic DRAFT bridge.

This module is not installed in Runtime's live path. Even an opted-in call
only creates a source-bound local SHADOW DRAFT; no C6 output authority.
"""
from __future__ import annotations

import math
import time

from .f1f5_c5c6_atomic_draft_candidate import stage_draft, check_staged_draft


def _result(status, **extra):
    return {"schema": "v13.runtime_c3_atomic_draft_shadow.v1",
            "status": status, "delivery_authority": 0,
            "output_committed": False, "tool_dispatches": 0,
            "learning_authority": 0, "native_proof": False, **extra}


def _idle(runtime):
    return (not getattr(runtime, "closed", False)
            and not runtime.cancel_event.is_set()
            and getattr(runtime, "current", None) is None
            and runtime.jobs.empty())


def stage_runtime_c3_draft(runtime, event_id, deadline, *,
                           operator_opt_in=False, model_call_opt_in=False,
                           max_tokens=96):
    """Use the real Runtime pool API, but never deliver its candidate.

    Both opt-ins are software test switches, not human TTY consent. The caller
    must supply an isolated idle Runtime; active concurrent producers are not
    supported by this candidate.
    """
    if operator_opt_in is not True or model_call_opt_in is not True:
        return _result("OFF", model_called=False, runner_released=False)
    if (type(event_id) is not str or not event_id
            or type(max_tokens) is not int or not 1 <= max_tokens <= 256
            or type(deadline) not in (int, float) or not math.isfinite(deadline)):
        return _result("INVALID_INPUT", model_called=False, runner_released=False)
    if time.monotonic() >= deadline:
        return _result("DEADLINE_EXPIRED", model_called=False, runner_released=False)
    if not _idle(runtime):
        return _result("RUNTIME_NOT_IDLE", model_called=False, runner_released=False)
    try:
        revision = runtime.models.revision("C3_LANGUAGE")
    except Exception:
        return _result("C3_REVISION_RED", model_called=False, runner_released=False)
    invoked = False
    released = False
    metrics = {}

    def generate(messages):
        nonlocal invoked, metrics
        if not _idle(runtime) or time.monotonic() >= deadline:
            raise RuntimeError("RUNTIME_CHANGED_BEFORE_C3")
        if runtime.models.revision("C3_LANGUAGE") != revision:
            raise RuntimeError("C3_REVISION_CHANGED")
        runner = runtime.pool.get("C3_LANGUAGE")
        invoked = True
        output = "".join(runner.generate(
            messages, runtime.cancel_event, deadline, max_tokens, None, seed=13))
        metrics = dict(runner.last_metrics)
        if (metrics.get("status") != "FINAL" or not _idle(runtime)
                or time.monotonic() >= deadline
                or runtime.models.revision("C3_LANGUAGE") != revision):
            raise RuntimeError("C3_NOT_FINAL_OR_RUNTIME_CHANGED")
        return output

    try:
        staged = stage_draft(
            runtime.cfg, runtime.memory, runtime.session, event_id,
            generate, operator_opt_in=True)
    except Exception:
        staged = {"status": "BRIDGE_ERROR"}
    finally:
        if invoked:
            try:
                runtime.pool.unload()
                released = True
            except Exception:
                released = False
    if invoked and not released:
        return _result("RUNNER_RELEASE_RED", model_called=True,
                       runner_released=False)
    if staged.get("status") != "DRAFT_STAGED_SHADOW_NO_COMMIT":
        return _result(staged.get("status", "BRIDGE_ERROR"),
                       model_called=invoked, runner_released=released)
    checked = check_staged_draft(
        runtime.cfg, runtime.memory, runtime.session, event_id, staged)
    if checked["status"] != "DRAFT_BOUND_SHADOW_NO_COMMIT":
        return _result("POST_STAGE_BINDING_RED", model_called=invoked,
                       runner_released=released,
                       draft_message_id=staged["draft_message_id"])
    return _result("RUNTIME_C3_DRAFT_BOUND_SHADOW_NO_COMMIT",
                   model_called=invoked, runner_released=released,
                   c3_revision=revision, c3_status=metrics.get("status"),
                   draft_message_id=staged["draft_message_id"],
                   c5_action_id=staged["c5_action_id"],
                   candidate_sha256=staged["candidate_sha256"])
