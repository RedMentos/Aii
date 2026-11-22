"""V14 C5/C6 Android action-outcome bridge, offline-first and deny-by-default.

The broker owns approvals; this adapter only dispatches already consumed, approved
commands to an explicitly supplied local companion and returns typed evidence.
A Python callback is not an Android OS permission boundary.
"""
from dataclasses import dataclass, asdict
from typing import Protocol
import hashlib
import json
import time


class Companion(Protocol):
    def perform(self, command: dict) -> dict: ...


@dataclass(frozen=True)
class ActionOutcome:
    action_id: str
    capability: str
    command_sha256: str
    status: str
    source_ref: str
    observed_at: float
    companion_revision: str
    evidence_ref: str | None = None
    error_code: str | None = None

    def packet(self):
        return {"schema": "v14.android-action-outcome/1", **asdict(self),
                "learning_authority": "OBSERVATION_ONLY", "model_weight_authority": False}


def dispatch_approved(broker, action_id: str, *, source_ref: str,
                      companion: Companion | None = None, dry_run: bool = True,
                      clock=time.time) -> ActionOutcome:
    """Consume one broker approval, never manufacture or replay an authorization.

    Native dispatch is disabled until an independently authenticated companion
    and OS-enforced permission adapter are reviewed. A supplied companion is
    usable only in simulation, where outcomes are clearly marked SIMULATED.
    """
    if not isinstance(source_ref, str) or not source_ref.strip() or len(source_ref) > 256:
        raise ValueError("source_ref required")
    if dry_run is not True:
        raise PermissionError("native Android dispatch not enabled")
    cmd = broker.execute(action_id, dry_run=True)
    sha = hashlib.sha256(json.dumps(cmd, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    status, evidence, error, revision = "DRY_RUN_ONLY", None, None, "NONE"
    if companion is not None:
        try:
            reply = companion.perform(dict(cmd))
            if not isinstance(reply, dict) or reply.get("status") not in {"OBSERVED", "FAILED"}:
                raise ValueError("invalid companion response")
            revision = str(reply.get("revision", "SIMULATOR"))[:80]
            evidence = reply.get("evidence_ref")
            if evidence is not None and (not isinstance(evidence, str) or len(evidence) > 256):
                raise ValueError("invalid evidence reference")
            status = "SIMULATED_" + reply["status"]
            error = (str(reply.get("error_code", ""))[:80] or None) if status == "SIMULATED_FAILED" else None
        except Exception:
            status, evidence, error, revision = "SIMULATED_FAILED", None, "COMPANION_ERROR", "SIMULATOR"
    return ActionOutcome(cmd["action_id"], cmd["capability"], sha, status,
                         source_ref, float(clock()), revision, evidence, error)
