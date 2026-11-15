"""Typed simulation-only Android action outcome, bound to the approved broker envelope.

Native Android execution requires a separately authenticated companion. This
module deliberately cannot attest device execution or promote T8 evidence.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import time

SCHEMA = "v13.android-action-outcome/1"


class InvalidOutcome(ValueError):
    pass


@dataclass(frozen=True)
class ActionOutcome:
    action_id: str
    capability: str
    digest: str
    status: str
    observed_at: float
    origin: str
    error_code: str | None = None

    def as_record(self):
        return {"schema": SCHEMA, "action_id": self.action_id,
                "capability": self.capability, "digest": self.digest,
                "status": self.status, "observed_at": self.observed_at,
                "origin": self.origin, "error_code": self.error_code}


def receipt(envelope, *, status="SIMULATED", origin="simulator",
            observed_at=None, error_code=None):
    """Validate dry-run output; never accept caller-asserted native success."""
    from .android_control import _canonical, ControlDenied
    if type(envelope) is not dict:
        raise InvalidOutcome("invalid envelope")
    try:
        action_id = envelope["action_id"]
        capability = envelope["capability"]
        args = envelope["args"]
        digest = envelope["digest"]
        expected = hashlib.sha256(_canonical(capability, args).encode()).hexdigest()
    except (KeyError, TypeError, ControlDenied) as exc:
        raise InvalidOutcome("invalid action envelope") from exc
    if not (type(action_id) is str and len(action_id) == 32 and
            all(c in "0123456789abcdef" for c in action_id)):
        raise InvalidOutcome("invalid action id")
    if type(digest) is not str or digest != expected:
        raise InvalidOutcome("action digest mismatch")
    if status != "SIMULATED" or origin != "simulator" or envelope.get("status") != "DRY_RUN_ONLY":
        raise InvalidOutcome("unattested native outcome")
    if error_code is not None and (type(error_code) is not str or
                                   len(error_code) > 64 or not error_code.isascii()):
        raise InvalidOutcome("invalid error code")
    now = time.time() if observed_at is None else observed_at
    if type(now) not in (int, float) or not 0 <= now < 1e12:
        raise InvalidOutcome("invalid timestamp")
    return ActionOutcome(action_id, capability, digest, status, float(now),
                         origin, error_code)
