"""Run388 opt-in AG2 pre-action tool hook, not wired into live Growth by default.

A ToolRegistry explicitly configured with before/after/abort can now take a
frequency prediction after the durable CorollaryCopy but *before* tool effects.
The baseline remains a non-causal frequency model, not Body-JEPA or STEP8.
"""
from ..common import dumps
from ..toolforecast import is_forecast
from .grounding import Grounding


class PreActionGrounding:
    def __init__(self, grounding: Grounding):
        self.grounding = grounding

    def before(self, tx):
        """Called only after action-copy commit and before the actual effect."""
        if tx.get("status") != "APPROVED":
            return None
        predicted = tx.get("predicted")
        if is_forecast(predicted) or not isinstance(predicted, dict) or "outcome" not in predicted:
            predicted = None
        aid, _ = self.grounding.expect(
            "tool:" + tx["tool"],
            dumps(tx["args"])[:120],
            {"tool": tx["tool"]},
            modality="tool",
            predicted=predicted,
        )
        return aid

    def after(self, tx):
        """Close only a genuine pre-action expectation; never backfill post-hoc."""
        if tx.get("status") not in ("EXECUTED", "FAILED"):
            return None
        aid = tx.get("preaction_id")
        if not aid:
            return None
        return self.grounding.observe(aid, {"status": tx["status"], "result": tx.get("result")})

    def abort(self, tx):
        """A hard-blocked or interrupted effect supplies no training outcome."""
        aid = tx.get("preaction_id")
        return self.grounding.discard(aid) if aid else False
