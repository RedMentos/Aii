"""Run33 SHADOW-only finite token-confidence wiring for AG12 BodySolver.

The frozen original solver and its native Run27 evidence are unchanged.
No production runtime imports this candidate.
"""
from __future__ import annotations

import threading
import time

from . import solver as original
from .solver_confidence_finite_candidate import safe_confidence

REVISION = "run33-ag12-finite-vote-shadow-v1"


class FiniteConfidenceBodySolver(original.BodySolver):
    """Same native generation path as the frozen BodySolver, finite confidence only.

    Inherits original batch, combine, cancellation and error accounting. A
    separate future source-bound native cohort is required before integration.
    """

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
        conf, source = safe_confidence(getattr(runner, "last_metrics", {}))
        return {
            "role": role,
            "answer": original.extract(text),
            "confidence": conf,
            "confidence_source": source,
        }
