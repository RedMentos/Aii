"""Run117AO default-OFF authenticated USER event + prewarmed Body source-ID.

Composes unchanged sibling Run117AI authoritative event->SourceRef/packet
verification with Run117AL prewarm-before-epoch. SHADOW only; not sandbox,
native proof, source semantic truth, or production output.
"""
from __future__ import annotations

from .b1b2_source_id_quote_candidate import _candidates
from .b1b2_source_id_event_binding_candidate import (
    _canonical, _result, select_bound,
)


def select_bound_prewarmed(runtime, event, role, acquire, generate, release, *,
                           operator_opt_in=False, callback_opt_in=False,
                           approval_receipt=None):
    """Only trusted generate(runner,messages) executes within frozen epoch.

    Acquire/release may persist BodyPort lifecycle and must remain outside
    the selector window. The caller separately proves real native identity,
    release/reap and closed Store evidence; this wrapper never asserts them.
    """
    if operator_opt_in is not True or callback_opt_in is not True:
        return _result("OFF")
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED_RED")
    if not all(callable(f) for f in (acquire, generate, release)):
        return _result("INVALID_PREWARM_CALLBACK_RED")
    try:
        _canonical(runtime, event)
        _candidates(runtime, event, role)
    except Exception:
        return _result("EVENT_SOURCE_PREFLIGHT_RED")
    runner = None
    result = None
    try:
        runner = acquire(role)
        if getattr(runner, "role", None) != role:
            result = _result("PREWARM_ROLE_RED")
        else:
            result = select_bound(
                runtime, event, role,
                lambda messages: generate(runner, messages),
                operator_opt_in=True, callback_opt_in=True,
            )
    except Exception as exc:
        result = _result("PREWARM_EXCEPTION_RED",
                         error_type=type(exc).__name__)
    finally:
        if runner is not None:
            try:
                release(runner)
            except Exception as exc:
                # The original selection packet (if any) is zero-authority.
                result = _result("RELEASE_EXCEPTION_RED",
                                 error_type=type(exc).__name__)
    return result
