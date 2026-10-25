"""Run388 opt-in AG2 pre-action tool hook, not wired into live Growth by default.

A ToolRegistry explicitly configured with before/after/abort can now take a
frequency prediction after the durable CorollaryCopy but *before* tool effects.
The baseline remains a non-causal frequency model, not Body-JEPA or STEP8.
"""
import math

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
            {"tool": tx["tool"], "action_tx": tx.get("action_tx"), "event_id": tx.get("event_id") or "operator", "origin": tx.get("origin")},
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

    def reconcile(self, stale_after_s=3600):
        """Explicit opt-in crash reconciliation from *durable* action outcomes.

        Call after Transactions.recover() on restart, never during an owned
        live action. UNKNOWN/CANCELLED never train; in-flight actions stay open.
        Only a completed operator action or FINAL assistant turn can be learned.
        This does not execute tools, alter permissions or activate Growth hooks.
        """
        from ..transaction import Transactions

        if type(stale_after_s) not in (int, float) or not math.isfinite(stale_after_s) or stale_after_s < 0:
            raise ValueError("stale_after_s must be finite nonnegative")
        now = self.grounding.clock()
        if not isinstance(now, (int, float)) or not math.isfinite(now):
            raise ValueError("grounding clock must be finite")
        result = {"recovered": 0, "discarded": 0, "deferred": 0, "errors": 0}
        actions = Transactions(self.grounding.s)
        # Grounding's open history is already capped at HISTORY=512. Snapshot
        # first; each observe/discard uses its own optimistic SQLite mutation.
        pending = list(self.grounding.box.load()[0]["open"].items())

        def discard(aid):
            if self.grounding.discard(aid):
                result["discarded"] += 1

        for aid, record in pending:
            created = record.get("created")
            valid_created = type(created) in (int, float) and math.isfinite(created)
            stale = not valid_created or now - created >= stale_after_s
            action = record.get("action")
            action = action if isinstance(action, dict) else {}
            tid = action.get("action_tx")
            if not isinstance(tid, str) or not 0 < len(tid) <= 128:
                if stale:
                    discard(aid)
                else:
                    result["deferred"] += 1
                continue
            tx = actions.get(tid)
            if tx is None:
                if stale:
                    discard(aid)
                else:
                    result["deferred"] += 1
                continue
            try:
                matching = (
                    tx.get("id") == tid
                    and record.get("kind") == "tool:" + tx["tool"]
                    and action.get("tool") == tx["tool"]
                    and action.get("event_id") == tx.get("event_id")
                    and action.get("origin") == tx.get("origin")
                    and record.get("ctx") == dumps(tx["args"])[:120]
                )
            except (KeyError, TypeError, ValueError):
                matching = False
            if not matching:
                discard(aid)
                continue
            state = tx.get("state")
            if state in ("UNKNOWN", "CANCELLED"):
                discard(aid)
                continue
            if state not in ("SUCCEEDED", "FAILED"):
                # The action may still be owned by a live executor; do not
                # infer completion from elapsed time. Transactions.recover()
                # is responsible for classifying interrupted executions.
                result["deferred"] += 1
                continue
            event = tx.get("event_id")
            if event == "operator":
                final = tx.get("origin") == "USER"
                nonfinal = not final
            else:
                row = self.grounding.s.one(
                    "SELECT status FROM messages WHERE event_id=? AND role='assistant' "
                    "AND status IN ('FINAL','CANCELLED','DEADLINE','ERROR','INTERRUPTED') "
                    "ORDER BY id DESC LIMIT 1", (event,)
                )
                final = bool(row and row["status"] == "FINAL")
                nonfinal = bool(row and row["status"] != "FINAL")
            if not final:
                if nonfinal or stale:
                    discard(aid)
                else:
                    result["deferred"] += 1
                continue
            actual = {"status": "EXECUTED" if state == "SUCCEEDED" else "FAILED", "result": tx.get("result")}
            try:
                self.grounding.observe(aid, actual)
            except (ValueError, KeyError, TypeError):
                # Concurrent normal settlement may have won; no second sample.
                if self.grounding.discard(aid):
                    result["discarded"] += 1
                result["errors"] += 1
            else:
                result["recovered"] += 1
        return result
