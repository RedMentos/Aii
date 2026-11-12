"""Opt-in durable operator session: explicit command -> audited Android dispatch.

Termux-side integration only. The caller must inject a separately authorized
native companion transport and authenticated verifier. No implicit C3 execution.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from .android_action_audit import build_audited_dispatcher
from .android_operator_bridge import dispatch_operator_command


@contextmanager
def audited_operator_session(registry, audit_path: str | Path, *, transport, verifier):
    """Yield an explicit command handler with a durable pre-action journal.

    Fail closed without both dependencies; close the SQLite journal on exit.
    Caller owns native OS grants, local approval, stop switch and process lock.
    """
    if transport is None or verifier is None:
        raise ValueError("native transport and independent verifier required")
    dispatcher, journal = build_audited_dispatcher(
        registry, audit_path, transport, verifier
    )
    try:
        def command(line: str, *, approve_local=None):
            return dispatch_operator_command(
                line, dispatcher, approve_local=approve_local
            )
        yield command, journal
    finally:
        journal.close()
