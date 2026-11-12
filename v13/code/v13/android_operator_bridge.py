"""Explicit operator-to-Android dispatcher bridge (Termux-side only).

Not a native companion or an authorization boundary. The trusted local UI must
supply an approval callback for non-dry-run actions; the companion independently
enforces OS grants and per-action consent. Natural-language C3 text never calls
this bridge implicitly.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import re
from .android_capability_contract import Capability, OutcomeStatus
from .android_companion_dispatch import AndroidDispatcher, DispatchResult

@dataclass(frozen=True)
class OperatorResult:
    status: str
    request_id: str | None = None
    capability: str | None = None
    detail: str = ""

_COMMANDS = {
    "launch": Capability.LAUNCH_APP,
    "observe": Capability.READ_UI,
    "back": Capability.BACK,
    "tap": Capability.TAP,
    "type": Capability.TYPE_TEXT,
}

def dispatch_operator_command(
    line: str,
    dispatcher: AndroidDispatcher,
    *,
    approve_local: Callable[[Capability, str], bool] | None = None,
) -> OperatorResult:
    """Parse `:android dry|execute launch|observe|back|tap|type TARGET`.

    An origin string is not authorization. The local confirmation hook is not
    a substitute for native OS authentication. Targets are never echoed.
    """
    if not isinstance(line, str) or not line.startswith(":android "):
        return OperatorResult("INVALID", detail="explicit :android command required")
    parts = line.split(" ", 3)
    if len(parts) < 3 or parts[1] not in ("dry", "execute") or parts[2] not in _COMMANDS:
        return OperatorResult("INVALID", detail="invalid Android command")
    mode, verb = parts[1:3]
    target = parts[3] if len(parts) == 4 else ""
    if verb == "back" and not target:
        target = "system_back"
    if not target or len(target) > 256 or any(ord(ch) < 32 or ord(ch) == 127 for ch in target):
        return OperatorResult("INVALID", detail="invalid target")
    # The command grammar is a boundary, not a free-form Android intent API.
    # Only package identifiers may be launched; tap coordinates must be finite
    # integer screen coordinates. Never let malformed commands reach a companion.
    if verb == "launch" and not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)+", target):
        return OperatorResult("INVALID", detail="invalid package identifier")
    if verb == "tap":
        match = re.fullmatch(r"([0-9]{1,5}),([0-9]{1,5})", target)
        if match is None or any(int(v) > 32767 for v in match.groups()):
            return OperatorResult("INVALID", detail="invalid tap coordinates")
    if verb == "back" and target != "system_back":
        return OperatorResult("INVALID", detail="invalid back target")
    capability = _COMMANDS[verb]
    if mode == "execute":
        if approve_local is None:
            return OperatorResult("DENIED", capability=capability.value, detail="trusted local approval unavailable")
        try:
            if approve_local(capability, target) is not True:
                return OperatorResult("DENIED", capability=capability.value, detail="local approval declined")
        except Exception:
            return OperatorResult("DENIED", capability=capability.value, detail="local approval failed")
    try:
        result: DispatchResult = dispatcher.dispatch(capability, target, dry_run=mode == "dry")
    except (ValueError, PermissionError):
        return OperatorResult("DENIED", capability=capability.value, detail="capability or request rejected")
    return OperatorResult(
        result.outcome.status.value, result.request.request_id, capability.value,
        "native execution unverified" if result.outcome.status == OutcomeStatus.SUCCESS else "",
    )
