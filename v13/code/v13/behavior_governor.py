"""Trainable V13 behavior-risk adviser, NOT an OS permission gate.

Ethical evaluation is contextual and fallible. Its evolving weights cannot
authorize shell/network/sandbox escape or change external capability rights.
An independently trusted Android/OS layer must enforce real boundaries.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

RISK_SIGNALS = (
    "likelihood_of_harm", "self_harm_encouragement", "deception_intent",
    "unapproved_power", "consent_conflict", "private_data_exposure",
    "uncertainty", "third_party_effect", "fiction_or_satire",
    "legitimate_defense",
)
BASE_WEIGHTS = (2.8, 4.0, 1.8, 2.0, 2.8, 2.4, 0.8, 0.7, -0.9, -0.8)
CORE_PRINCIPLES = (
    "human_wellbeing_and_nonviolence", "dignity_and_autonomy",
    "honesty_and_nonmanipulation", "consent_and_privacy",
    "fairness_and_context", "proportionality_and_uncertainty",
    "transparency_and_accountability", "bounded_self_development",
)
MODEL_SCHEMA = "v13.behavior-risk-head/1"


class BehaviorReviewError(ValueError):
    pass


def _sigmoid(z):
    z = max(-60.0, min(60.0, z))
    return 1.0 / (1.0 + math.exp(-z))


def _signals(raw):
    if type(raw) is not dict or set(raw) != set(RISK_SIGNALS):
        raise BehaviorReviewError("risk signals must be complete and typed")
    out = []
    for name in RISK_SIGNALS:
        value = raw[name]
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise BehaviorReviewError("risk signal out of range")
        out.append(float(value))
    return tuple(out)


def neutral_signals():
    return {name: 0.0 for name in RISK_SIGNALS}


def _json(obj):
    return json.dumps(obj, allow_nan=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


@dataclass(frozen=True)
class BehaviorVerdict:
    risk: float
    guidance: str
    concerns: tuple[str, ...]
    needs_external_capability_check: bool
    can_grant_permissions: bool = False
    can_edit_sandbox_rules: bool = False
    is_moral_oracle: bool = False


class TinyBehaviorHead:
    """Small online-trainable 10-feature logistic risk evaluator.

    Not a language understanding model. A trusted source must independently
    supply reviewed labels and features. No automatic tool authority.
    """
    def __init__(self, *, weights=BASE_WEIGHTS, bias=-3.2, steps=0):
        if (type(steps) is not int or not 0 <= steps <= 10_000_000
                or type(weights) not in (tuple, list) or len(weights) != len(RISK_SIGNALS)
                or any(type(w) not in (float, int) or not math.isfinite(w) or abs(w) > 6
                       for w in weights)
                or type(bias) not in (int, float) or not math.isfinite(bias) or abs(bias) > 6):
            raise BehaviorReviewError("invalid trainable safety-head state")
        self.weights = tuple(float(w) for w in weights)
        self.bias = float(bias)
        self.steps = steps

    def score(self, signals):
        x = _signals(signals)
        return _sigmoid(self.bias + sum(w * v for w, v in zip(self.weights, x)))

    def learn_from_reviewed_label(self, signals, label, *, operator_enabled=False, lr=0.05):
        """Make a REAL numeric online update with optional training toggle.

        Boolean operator_enabled is only a training switch, not authenticated
        permission. A separate trusted UI must verify source/label provenance.
        """
        if operator_enabled is not True:
            raise BehaviorReviewError("behavior-head training not enabled by operator")
        if type(label) is not int or label not in (0, 1):
            raise BehaviorReviewError("human risk label must be binary")
        if type(lr) not in (float, int) or not math.isfinite(lr) or not 0 < lr <= 0.2:
            raise BehaviorReviewError("invalid behavior-head learning rate")
        x = _signals(signals)
        old_score = _sigmoid(self.bias + sum(w * v for w, v in zip(self.weights, x)))
        grad = float(lr) * (label - old_score)
        self.weights = tuple(max(-6.0, min(6.0, w + grad * v))
                             for w, v in zip(self.weights, x))
        self.bias = max(-6.0, min(6.0, self.bias + grad))
        self.steps += 1
        return {"old_risk": old_score, "new_risk": self.score(signals),
                "weights_changed": True, "fit_steps": self.steps,
                "base_gguf_changed": False, "security_boundary_changed": False}

    def snapshot(self):
        body = {"schema": MODEL_SCHEMA, "weights": list(self.weights),
                "bias": self.bias, "steps": self.steps}
        return dict(body, sha256=hashlib.sha256(_json(body)).hexdigest())

    @classmethod
    def restore(cls, snapshot):
        if type(snapshot) is not dict or set(snapshot) != {"schema", "weights", "bias", "steps", "sha256"}:
            raise BehaviorReviewError("invalid behavior-head checkpoint schema")
        body = {name: snapshot[name] for name in ("schema", "weights", "bias", "steps")}
        if body["schema"] != MODEL_SCHEMA or type(snapshot["sha256"]) is not str:
            raise BehaviorReviewError("invalid behavior-head checkpoint version")
        if hashlib.sha256(_json(body)).hexdigest() != snapshot["sha256"]:
            raise BehaviorReviewError("corrupted behavior-head checkpoint")
        return cls(weights=body["weights"], bias=body["bias"], steps=body["steps"])

    def save(self, path):
        """Atomic local checkpoint. Hash detects damage but NOT a forgery."""
        dest = Path(path)
        if not dest.parent.is_dir() or dest.is_symlink():
            raise BehaviorReviewError("invalid checkpoint directory or symlink")
        fd, temporary = tempfile.mkstemp(prefix=".v13-behavior-", dir=dest.parent)
        try:
            with os.fdopen(fd, "wb") as file:
                file.write(_json(self.snapshot()))
                file.flush()
                os.fsync(file.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, dest)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @classmethod
    def load(cls, path):
        dest = Path(path)
        if dest.is_symlink() or not dest.is_file() or dest.stat().st_size > 8192:
            raise BehaviorReviewError("missing or oversized behavior-head checkpoint")
        try:
            return cls.restore(json.loads(dest.read_text(encoding="utf-8")))
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            raise BehaviorReviewError("invalid behavior-head checkpoint") from exc


def review_behavior(signals, *, has_external_effect=False, unapproved_egress=False,
                    undisclosed_storage=False, sandbox_escape=False, head=None):
    """Advisory contextual decision. Never use as the only security layer.

    Untrusted model-supplied flags/feature scores are NOT verified observations.
    The executor must separately enforce OS/network/storage permissions.
    """
    for flag in (has_external_effect, unapproved_egress, undisclosed_storage, sandbox_escape):
        if type(flag) is not bool:
            raise BehaviorReviewError("boundary flags must be bool")
    scorer = head if head is not None else TinyBehaviorHead()
    if not isinstance(scorer, TinyBehaviorHead):
        raise BehaviorReviewError("untrusted behavioral model type")
    values = _signals(signals)
    risk = scorer.score(signals)
    concerns = tuple(name for name, value in zip(RISK_SIGNALS, values)
                     if value >= 0.5 and name not in ("fiction_or_satire", "legitimate_defense"))
    breach = unapproved_egress or undisclosed_storage or sandbox_escape
    if breach:
        guidance = "REJECT_UNAUTHORIZED_ACTION"
    elif risk >= 0.55 or has_external_effect:
        guidance = "ASK_FOR_CONTEXT_OR_APPROVAL"
    else:
        guidance = "NO_OBJECTION_IN_ADVISORY_REVIEW"
    return BehaviorVerdict(
        risk=risk, guidance=guidance, concerns=concerns,
        needs_external_capability_check=has_external_effect or breach)
