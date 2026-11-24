"""Run13Z: AG9 source-disjoint heldout calibration diagnostic, no authority.

Read-only synthetic/explicit-evidence evaluation. Never writes Store, updates
model weights, changes the production AG9 age metric or promotes an Age gate.
"""
from __future__ import annotations

import math

from .generality import calibration
from .metacog import BINS, MIN_SUPPORT, Metacognition
from .metacog import _binary_label, _finite_confidence

SCHEMA = "v13.run13z.ag9_heldout_shadow.v1"
MIN_HELDOUT = 10
DEGRADATION_BRIER_MARGIN = 0.02


def _pairs(rows, split, seen):
    if type(rows) is not list:
        raise ValueError("RUN13Z_ROWS_REQUIRED:" + split)
    expected = {"source_id", "confidence", "correct"}
    result = []
    for row in rows:
        if type(row) is not dict or set(row) != expected:
            raise ValueError("RUN13Z_ROW_SCHEMA_RED:" + split)
        source = row["source_id"]
        if (type(source) is not str or not source or source != source.strip()
                or len(source) > 128
                or any(ord(c) < 32 or ord(c) == 127 for c in source)
                or source in seen):
            raise ValueError("RUN13Z_SOURCE_DISJOINT_RED:" + split)
        seen.add(source)
        result.append((_finite_confidence(row["confidence"]),
                       _binary_label(row["correct"])))
    return result


def audit_heldout(train, heldout):
    """Never calls age.record or Metacognition.record; no Store needed."""
    seen = set()
    training = _pairs(train, "train", seen)
    testing = _pairs(heldout, "heldout", seen)
    if len(training) < MIN_SUPPORT or len(testing) < MIN_HELDOUT:
        raise ValueError("RUN13Z_INSUFFICIENT_DISJOINT_SUPPORT")
    table = Metacognition._fit(training)
    if (type(table) is not list or len(table) != BINS
            or any(type(x) is not float or not math.isfinite(x)
                   or not 0 <= x <= 1 for x in table)
            or table != sorted(table)):
        raise ValueError("RUN13Z_CALIBRATOR_INVALID")
    def calibrated(pairs):
        return [(table[min(BINS - 1, int(confidence * BINS))], correct)
                for confidence, correct in pairs]
    raw_train, fitted_train = calibration(training), calibration(calibrated(training))
    raw_test, fitted_test = calibration(testing), calibration(calibrated(testing))
    if any(metric["ece"] is None or metric["brier"] is None
           for metric in (raw_train, fitted_train, raw_test, fitted_test)):
        raise ValueError("RUN13Z_METRICS_MISSING")
    delta = round(fitted_test["brier"] - raw_test["brier"], 6)
    return {
        "schema": SCHEMA,
        "status": ("HELDOUT_DEGRADATION" if delta > DEGRADATION_BRIER_MARGIN
                   else "HELDOUT_NONDEGRADATION_SHADOW"),
        "train_n": len(training), "heldout_n": len(testing),
        "calibrator_bins": len(table), "monotone": True,
        "train_raw": {"ece": raw_train["ece"], "brier": raw_train["brier"]},
        "train_calibrated": {"ece": fitted_train["ece"], "brier": fitted_train["brier"]},
        "heldout_raw": {"ece": raw_test["ece"], "brier": raw_test["brier"]},
        "heldout_calibrated": {"ece": fitted_test["ece"], "brier": fitted_test["brier"]},
        "heldout_brier_delta": delta,
        "source_disjoint": True, "store_written": False,
        "native_calls": 0, "age_metric_admissible": False,
        "utility_gate_promoted": False, "learning_mode": "RECORD_ONLY",
        "step2_status": "UTILITY_FAIL", "b3_status": "NO_PROMOTION",
        "body_jepa_status": "UNAVAILABLE", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
    }
