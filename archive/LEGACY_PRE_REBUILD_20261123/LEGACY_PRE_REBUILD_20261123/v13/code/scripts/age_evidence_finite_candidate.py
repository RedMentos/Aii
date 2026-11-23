"""Run131 Age evidence finite/type preflight candidate, default-off.

A wrapper for review: does NOT alter v13.age runtime or raise BUILD_CEILING.
"""
from __future__ import annotations
import math
from v13 import age


def validate(metrics):
    """Fail before any durable AgeControl mutation; preserve unrelated metadata."""
    if not isinstance(metrics, dict):
        raise ValueError("AGE_EVIDENCE_NOT_DICT")
    experience = metrics.get("experience")
    if type(experience) is not int or experience < 0:
        raise ValueError("AGE_EXPERIENCE_INVALID")
    if type(metrics.get("regression_pass")) is not bool:
        raise ValueError("AGE_REGRESSION_FLAG_INVALID")
    for name in age.METRICS:
        value = metrics.get(name)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("AGE_METRIC_INVALID:" + name)
    return dict(metrics)


def gate_pass(metrics, stage, band=0.):
    if type(stage) is not int or not 0 <= stage <= 5:
        raise ValueError("AGE_STAGE_INVALID")
    if type(band) not in (int, float) or not math.isfinite(band) or not 0 <= band <= 1:
        raise ValueError("AGE_BAND_INVALID")
    return age.gate_pass(validate(metrics), stage, band)


def record(controller, subject, metrics, evidence_id=None):
    """Validate before controller.record writes state, events or telemetry."""
    checked = validate(metrics)
    if not isinstance(controller, age.AgeControl):
        raise ValueError("AGE_CONTROLLER_INVALID")
    if subject != "system" and subject not in age.CAPABILITIES:
        raise ValueError("AGE_SUBJECT_INVALID")
    return controller.record(subject, checked, evidence_id=evidence_id)
