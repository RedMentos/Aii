"""Run40 isolated AG12 native null-span subtype + triple same-output vote SHADOW.

No production wiring. Transient native answers never leave memory; only
source categories, correctness and calibration aggregates may be exported.
"""
from __future__ import annotations

from collections import Counter
import math
import threading
import time

from . import solver as original
from .generality import normalize, calibration
from .solver_confidence_finite_candidate import safe_confidence
from .solver_confidence_null_sentinel_candidate import safe_confidence_null_aware

REVISION = "run40-ag12-null-span-native-triple-vote-shadow-v1"
ABSENT = object()


def native_field_min_type(metrics):
    """Classify primary native field source without retaining raw token metrics."""
    if type(metrics) is not dict:
        return "metrics_absent" if metrics is None else "metrics_malformed"
    tc = metrics.get("token_confidence", ABSENT)
    if tc is ABSENT:
        return "token_confidence_absent"
    if tc is None:
        return "token_confidence_none"
    if type(tc) is not dict:
        return "token_confidence_malformed"
    v = tc.get("field_min_prob", ABSENT)
    if v is ABSENT:
        return "field_min_absent"
    if v is None:
        return "field_min_none_span"
    if isinstance(v, bool):
        return "field_min_boolean"
    if type(v) in (int, float):
        try:
            f = float(v)
        except (OverflowError, TypeError, ValueError):
            return "field_min_numeric_overflow"
        return "field_min_finite" if math.isfinite(f) else "field_min_nonfinite"
    return "field_min_other_malformed"


class TripleConfidenceBodySolver(original.BodySolver):
    """One real native generation per role/item, three confidence votes."""

    def __init__(self, pool, roles, cfg=None, name=None,
                 item_seconds=original.ITEM_SECONDS, seed=19):
        super().__init__(pool, roles, cfg, name, item_seconds, seed)
        self._rows = {}
        self._types = {role: Counter() for role in self.roles}
        self._finite_sources = {role: Counter() for role in self.roles}
        self._null_sources = {role: Counter() for role in self.roles}
        self._legacy_errors = Counter()

    def ask(self, role, view, cancel=None, deadline=None):
        dl = time.monotonic() + self.item_seconds
        if deadline is not None:
            dl = min(dl, deadline)
        runner = self.pool.get(role)
        text = ""
        ev = cancel if cancel is not None else threading.Event()
        for tok in runner.generate(
            [{"role": "system", "content": original.SYS},
             {"role": "user", "content": view["prompt"]}],
            ev, dl, max_tokens=40, schema=original.SCHEMA,
            seed=self.seed, confidence_field="answer",
        ):
            text += tok
        metrics = getattr(runner, "last_metrics", {})
        finite, finite_source = safe_confidence(metrics)
        null, null_source = safe_confidence_null_aware(metrics)
        try:
            legacy, legacy_source = original.confidence(metrics)
            if type(legacy) not in (int, float) or not math.isfinite(legacy):
                raise ValueError("legacy_nonfinite")
        except Exception:
            legacy, legacy_source = None, "legacy_error"
            self._legacy_errors[role] += 1
        answer = original.extract(text)
        identity = (role, view["id"])
        if identity in self._rows:
            raise ValueError("RUN40_DUPLICATE_ROLE_ITEM")
        self._rows[identity] = (answer, legacy, finite, null)
        self._types[role][native_field_min_type(metrics)] += 1
        self._finite_sources[role][finite_source] += 1
        self._null_sources[role][null_source] += 1
        return {"role": role, "answer": answer,
                "confidence": null, "confidence_source": null_source}

    def aggregate(self, suite, scored_rows):
        """Aggregate only; assert same-output score identity before forgetting."""
        items = suite["items"]
        if (len(items) != 88 or len(scored_rows) != 88
                or [r["id"] for r in scored_rows] != [i["id"] for i in items]):
            raise ValueError("RUN40_SUITE_ROW_IDENTITY")
        if (len(self._rows) != 88 * len(self.roles)
                or any(self.stats.get(role, {}).get("items") != 88
                       or self.stats[role].get("errors") != 0
                       for role in self.roles)):
            raise ValueError("RUN40_ROLE_CALL_INCOMPLETE")
        correct = Counter()
        changed = Counter()
        pairs = {"finite_all": [], "null_all": [], "legacy_comparable": [],
                 "finite_comparable": [], "null_comparable": []}
        comparable = 0
        for item, scored in zip(items, scored_rows):
            votes = {"finite": [], "null": [], "legacy": []}
            for role in self.roles:
                answer, legacy, finite, null = self._rows[(role, item["id"])]
                for key, confidence in (("finite", finite), ("null", null)):
                    votes[key].append({"role": role, "answer": answer,
                                       "confidence": confidence})
                if legacy is not None:
                    votes["legacy"].append({"role": role, "answer": answer,
                                            "confidence": legacy})
            combined = {key: original.combine(votes[key])
                        for key in ("finite", "null")}
            for key in ("finite", "null"):
                is_correct = int(normalize(combined[key]["answer"]) ==
                                 normalize(item["answer"]))
                correct[key + "_all"] += is_correct
                pairs[key + "_all"].append((combined[key]["confidence"], is_correct))
            null_result = combined["null"]
            if (type(scored["correct"]) is not int
                    or scored["correct"] != int(normalize(null_result["answer"]) ==
                                                normalize(item["answer"]))
                    or not math.isclose(scored["confidence"], null_result["confidence"],
                                        abs_tol=0.0001, rel_tol=0.)):
                raise ValueError("RUN40_NULL_VOTE_SCORE_MISMATCH")
            changed["finite_null_all"] += int(
                normalize(combined["finite"]["answer"]) !=
                normalize(null_result["answer"]))
            if len(votes["legacy"]) == len(self.roles):
                combined["legacy"] = original.combine(votes["legacy"])
                comparable += 1
                for key in ("legacy", "finite", "null"):
                    is_correct = int(normalize(combined[key]["answer"]) ==
                                     normalize(item["answer"]))
                    correct[key + "_comparable"] += is_correct
                    pairs[key + "_comparable"].append(
                        (combined[key]["confidence"], is_correct))
                for a, b in (("legacy", "finite"), ("legacy", "null"),
                             ("finite", "null")):
                    changed[a + "_" + b + "_comparable"] += int(
                        normalize(combined[a]["answer"]) !=
                        normalize(combined[b]["answer"]))
        by_role = {}
        for role in self.roles:
            types = dict(sorted(self._types[role].items()))
            finite_sources = dict(sorted(self._finite_sources[role].items()))
            null_sources = dict(sorted(self._null_sources[role].items()))
            if any(sum(d.values()) != 88 for d in (types, finite_sources, null_sources)):
                raise ValueError("RUN40_METRIC_SOURCE_COUNT")
            by_role[role] = {
                "native_calls": 88,
                "native_field_min_types": types,
                "finite_source_counts": finite_sources,
                "null_source_counts": null_sources,
                "legacy_errors": self._legacy_errors[role],
            }
        result = {
            "items": 88, "role_calls": 88 * len(self.roles),
            "by_role": by_role,
            "legacy_comparable_rows": comparable,
            "legacy_incomparable_rows": 88 - comparable,
            "correct": dict(sorted(correct.items())),
            "changed_votes": dict(sorted(changed.items())),
            "calibration": {key: calibration(value)
                            for key, value in pairs.items() if value},
        }
        self._rows.clear()
        return result
