"""Local Android operator console: dry-run, audited commands, status and stop.

This is a Termux-side operator surface, NOT an Android native executor.
Only an explicitly injected transport/verifier can perform real actions.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .android_operator_audited_session import audited_operator_session
from .android_stop_latch import StopLatch


@dataclass(frozen=True)
class ConsoleReply:
    status: str
    detail: str = ""
    request_id: str | None = None


@contextmanager
def android_local_console(registry, audit_path: str | Path, *, transport, verifier):
    """Create a bounded local command handler with durable action audit.

    No automatic approval: callers must supply a trusted local confirmation
    callback for each execute command. Stop is irreversible for this session.
    """
    latch = StopLatch(audit_path)
    if latch.engaged():
        registry.stop()
    with audited_operator_session(
        registry, audit_path, transport=transport, verifier=verifier
    ) as (command, journal):
        def handle(line: str, *, approve_local=None) -> ConsoleReply:
            # Observe a stop marker written by another local session before
            # any further action, not only when this console was opened.
            if latch.engaged() and not getattr(registry, "_stopped", False):
                registry.stop()
            if line == ":android stop":
                registry.stop()
                try:
                    latch.engage()
                except OSError:
                    return ConsoleReply("STOPPED_UNPERSISTED", "stopped in process; durable latch write failed")
                return ConsoleReply("STOPPED", "durable stop engaged; further actions denied")
            if line == ":android status":
                history = registry.history()
                counts: dict[str, int] = {}
                for outcome in history:
                    name = outcome.status.value
                    counts[name] = counts.get(name, 0) + 1
                # Do not disclose action targets, private UI content, or receipts.
                detail = "stopped=" + str(bool(getattr(registry, "_stopped", False))).lower()
                detail += " outcomes=" + str(len(history))
                detail += " " + ",".join(
                    f"{name}:{counts[name]}" for name in sorted(counts)
                )
                return ConsoleReply("STATUS", detail.strip())
            if not isinstance(line, str) or not line.startswith(":android "):
                return ConsoleReply("INVALID", "explicit Android operator command required")
            result = command(line, approve_local=approve_local)
            return ConsoleReply(result.status, result.detail, result.request_id)
        yield handle
