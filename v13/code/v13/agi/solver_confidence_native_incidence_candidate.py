"""Run36 isolated AG12 native confidence incidence, same-output SHADOW vote.

No production integration. Native answer text stays in ephemeral memory; only
aggregate metric-source and correctness counts are exported by the collector.
"""
from __future__ import annotations

from collections import Counter
import math
import threading
import time

from . import solver as original
from .generality import normalize, calibration
from .solver_confidence_finite_candidate import safe_confidence

REVISION = "run36-ag12-native-confidence-incidence-shadow-v1"


class PairedConfidenceBodySolver(original.BodySolver):
    """One native generation per role/item, both confidence rules read same metrics."""

    def __init__(self, pool, roles, cfg=None, name=None, item_seconds=original.ITEM_SECONDS,
                 seed=17):
        super().__init__(pool, roles, cfg, name, item_seconds, seed)
        self._rows = {}  # transient answers, never written to disk
        self._sources = {role: Counter() for role in self.roles}
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
            seed=self.seed, confidence_field="answer"
        ):
            text += tok
        metrics = getattr(runner, "last_metrics", {})
        finite, source = safe_confidence(metrics)
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
            raise ValueError("RUN36_DUPLICATE_ROLE_ITEM")
        self._rows[identity] = (answer, legacy, finite)
        self._sources[role][source] += 1
        return {"role": role, "answer": answer,
                "confidence": finite, "confidence_source": source}

    def aggregate(self, suite, scored_rows):
        """Return only counts; no answer, prompt, native token metric or row export."""
        items = suite["items"]
        if (len(items) != 88 or len(scored_rows) != 88
                or [r["id"] for r in scored_rows] != [i["id"] for i in items]):
            raise ValueError("RUN36_SUITE_ROW_IDENTITY")
        if (len(self._rows) != 88 * len(self.roles)
                or any(self.stats.get(role, {}).get("items") != 88
                       or self.stats[role].get("errors") != 0
                       for role in self.roles)):
            raise ValueError("RUN36_ROLE_CALL_INCOMPLETE")
        old_correct = 0
        new_correct_comparable = 0
        new_correct_all = 0
        old_comparable = 0
        changed = 0
        old_pairs = []
        finite_pairs = []
        for item, scored in zip(items, scored_rows):
            original_votes = []
            finite_votes = []
            for role in self.roles:
                answer, legacy, finite = self._rows[(role, item["id"])]
                finite_votes.append({"role": role, "answer": answer,
                                     "confidence": finite})
                if legacy is not None:
                    original_votes.append({"role": role, "answer": answer,
                                           "confidence": legacy})
            new = original.combine(finite_votes)
            correct = int(normalize(new["answer"]) == normalize(item["answer"]))
            if (type(scored["correct"]) is not int or scored["correct"] != correct
                    or not math.isclose(scored["confidence"], new["confidence"],
                                        abs_tol=0.0001, rel_tol=0.)):
                raise ValueError("RUN36_FINITE_VOTE_SCORE_MISMATCH")
            new_correct_all += correct
            if len(original_votes) == len(self.roles):
                old = original.combine(original_votes)
                old_correct += int(normalize(old["answer"]) == normalize(item["answer"]))
                new_correct_comparable += correct
                changed += int(normalize(old["answer"]) != normalize(new["answer"]))
                old_pairs.append((old["confidence"],
                                  int(normalize(old["answer"]) == normalize(item["answer"]))))
                finite_pairs.append((new["confidence"], correct))
                old_comparable += 1
        by_role = {}
        for role in self.roles:
            sources = dict(sorted(self._sources[role].items()))
            if sum(sources.values()) != 88:
                raise ValueError("RUN36_METRIC_SOURCE_COUNT")
            by_role[role] = {
                "native_calls": 88,
                "source_counts": sources,
                "invalid_present": sum(v for k, v in sources.items()
                                       if k.startswith("invalid:")),
                "missing_confidence": sources.get("none", 0),
                "legacy_errors": self._legacy_errors[role],
            }
        out = {
            "items": 88, "role_calls": 88 * len(self.roles),
            "by_role": by_role,
            "legacy_comparable_rows": old_comparable,
            "legacy_incomparable_rows": 88 - old_comparable,
            "legacy_correct_on_comparable": old_correct,
            "finite_correct_on_comparable": new_correct_comparable,
            "finite_correct_all": new_correct_all,
            "same_output_changed_votes": changed,
            "legacy_calibration_on_comparable": calibration(old_pairs),
            "finite_calibration_on_comparable": calibration(finite_pairs),
        }
        self._rows.clear()  # no retained native answers after aggregate
        return out
