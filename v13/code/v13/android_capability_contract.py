"""Android companion protocol contract. No Android permissions are granted here.

The OS-side companion MUST authenticate the local caller, check Android grants
and foreground/background restrictions, and issue a fresh per-action approval.
This module is only a fail-closed Termux-side planner/receipt validator.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Mapping
import secrets
import time

class Capability(str, Enum):
    LAUNCH_APP = "launch_app"
    READ_UI = "read_ui"
    TAP = "tap"
    TYPE_TEXT = "type_text"
    BACK = "back"

class OutcomeStatus(str, Enum):
    DENIED = "DENIED"
    DRY_RUN = "DRY_RUN"
    CANCELLED = "CANCELLED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

@dataclass(frozen=True)
class ActionRequest:
    request_id: str
    capability: Capability
    target: str
    created_monotonic: float
    dry_run: bool = True

@dataclass(frozen=True)
class ActionOutcome:
    request_id: str
    capability: Capability
    status: OutcomeStatus
    companion_receipt: str | None
    observed_at: float

class CapabilityRegistry:
    """Explicit local configuration; no default Android action authority."""
    def __init__(self, enabled: Mapping[Capability, bool] | None = None):
        self._enabled = {c: bool((enabled or {}).get(c, False)) for c in Capability}
        self._stopped = False
        self._pending: dict[str, ActionRequest] = {}
        self._outcomes: list[ActionOutcome] = []

    def stop(self) -> None:
        self._stopped = True
        self._pending.clear()

    def request(self, capability: Capability, target: str, *, dry_run: bool = True) -> ActionRequest:
        if not isinstance(capability, Capability):
            raise ValueError("unknown capability")
        if not isinstance(target, str) or not target or len(target) > 256 or any(ord(c) < 32 for c in target):
            raise ValueError("invalid target")
        if self._stopped:
            raise PermissionError("stop switch engaged")
        if not self._enabled[capability] and not dry_run:
            raise PermissionError("capability OFF")
        req = ActionRequest(secrets.token_hex(16), capability, target, time.monotonic(), dry_run)
        self._pending[req.request_id] = req
        return req

    def settle(self, outcome: ActionOutcome) -> None:
        req = self._pending.pop(outcome.request_id, None)
        if req is None or req.capability != outcome.capability:
            raise ValueError("unknown or mismatched request")
        if outcome.status == OutcomeStatus.SUCCESS:
            if self._stopped or req.dry_run or not self._enabled[req.capability]:
                raise PermissionError("success forbidden for OFF/dry-run/stopped request")
            if not outcome.companion_receipt:
                raise ValueError("successful action requires companion receipt")
        self._outcomes.append(outcome)

    def history(self) -> tuple[ActionOutcome, ...]:
        return tuple(self._outcomes)
