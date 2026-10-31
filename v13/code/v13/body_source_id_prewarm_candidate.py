"""Run117AL experimental source-ID prewarm boundary; SHADOW only.

Native RunnerPool.get() can persist BodyPort ASSIGNED. Acquire before the
frozen source selector's Store epoch; never hide callback-time Store writes.
This wrapper does not prove model identity, inference, or useful learning.
"""
from __future__ import annotations

from .b1b2_source_id_quote_candidate import (
    _candidates, _receipt, select,
)


def select_prewarmed(runtime, event, role, acquire, generate, release, *,
                     operator_opt_in=False, callback_opt_in=False,
                     approval_receipt=None):
    """Acquire(role) before selector epoch; generate(runner, messages) inside.

    The caller owns actual runner/model validation and native process-reap
    evidence. Release always occurs after the selector's postgen Store check.
    This is a trusted-callback API, not a sandbox or a runtime delivery path.
    """
    if operator_opt_in is not True or callback_opt_in is not True:
        return _receipt("OFF")
    if approval_receipt is not None:
        return _receipt("REAL_TTY_APPROVAL_UNSUPPORTED_RED")
    if not all(callable(f) for f in (acquire, generate, release)):
        return _receipt("INVALID_PREWARM_CALLBACK_RED")
    try:
        # Fail before acquiring a model for stale/deleted/malformed sources.
        # select() performs its own independent pre/post-generation rechecks.
        _candidates(runtime, event, role)
    except Exception:
        return _receipt("SOURCE_PREFLIGHT_RED")
    runner = None
    result = None
    try:
        runner = acquire(role)
        if getattr(runner, "role", None) != role:
            result = _receipt("PREWARM_ROLE_RED")
        else:
            result = select(
                runtime, event, role,
                lambda messages: generate(runner, messages),
                operator_opt_in=True, callback_opt_in=True,
            )
    except Exception as exc:
        result = _receipt("PREWARM_EXCEPTION_RED",
                          error_type=type(exc).__name__)
    finally:
        if runner is not None:
            try:
                release(runner)
            except Exception as exc:
                # A selection packet, if written, stays zero-authority. Never
                # report successful completion without confirmed cleanup.
                result = _receipt("RELEASE_EXCEPTION_RED",
                                  error_type=type(exc).__name__)
    return result
