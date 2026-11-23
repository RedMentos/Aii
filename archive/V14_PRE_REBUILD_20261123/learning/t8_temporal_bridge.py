"""Store-verified T8 outcome bridge with idempotent concurrent consumption.

Only VerifiedT8Transition receipts issued by t8_store_authority may create
learning evidence. A caller-supplied trusted boolean is intentionally absent.
"""
from pathlib import Path
import math
from temporal_outcomes import TemporalOutcomes, Expectation
from temporal_receiver import TemporalReadout
from t8_store_authority import VerifiedT8Transition


class TemporalT8Bridge:
    def __init__(self, directory, *, learning_enabled=False):
        if type(learning_enabled) is not bool:
            raise ValueError("learning_enabled")
        root = Path(directory)
        self.ledger = TemporalOutcomes(root / "outcomes.json", max_pending=512, max_records=4096)
        self.receiver = TemporalReadout(root / "readout.json", learning_enabled=learning_enabled)

    def consume(self, receipt, prediction, *, optimizer_permission=False):
        if not isinstance(receipt, VerifiedT8Transition):
            raise PermissionError("Store-verified T8 receipt required")
        if type(optimizer_permission) is not bool:
            raise ValueError("optimizer_permission")
        if type(prediction) is not dict:
            raise ValueError("prediction")
        expected = prediction.get("expected_outcome")
        probability = prediction.get("probability")
        duration = prediction.get("duration_s")
        tolerance = prediction.get("tolerance_s", max(.25, float(duration) * .2)
                                   if type(duration) in (int, float) and math.isfinite(duration) and duration >= 0 else None)
        if expected not in {"FINAL", "NOT_FINAL"}:
            raise ValueError("expected_outcome")
        if type(probability) not in (int, float) or not math.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("probability")
        if type(duration) not in (int, float) or not math.isfinite(duration) or not 0 <= duration <= 3600:
            raise ValueError("duration_s")
        if type(tolerance) not in (int, float) or not math.isfinite(tolerance) or not 0 <= tolerance <= 3600:
            raise ValueError("tolerance_s")
        actual = receipt.actual
        actual_duration = actual.get("action_duration_s")
        if (type(actual_duration) not in (int, float) or not math.isfinite(actual_duration)
                or not 0 <= actual_duration <= 86400):
            raise ValueError("observed action duration")
        opened = float(receipt.created)
        earliest = opened + max(0., float(duration) - float(tolerance))
        deadline = opened + float(duration) + float(tolerance)
        observed_at = opened + float(actual_duration)
        cancelled = receipt.status in {"CANCELLED", "ABORTED"}
        censored = receipt.status in {"OUTCOME_UNKNOWN", "INTERRUPTED"}
        actual_outcome = None if cancelled or censored else (
            "FINAL" if receipt.status == "FINAL" else "NOT_FINAL")
        ref = receipt.source_ref
        source = "T8:" + ref["source_id"] + ":" + ref["sha256"]
        evidence = receipt.evidence_ref
        expected_record = {"source": source, "owner": "WORLD", "outcome": expected,
                           "opened_at": opened, "earliest": earliest, "deadline": deadline,
                           "probability": float(probability)}
        record = self.ledger.get(receipt.action_id)
        if record is None:
            if self.ledger.count() >= 4096:
                raise OverflowError("temporal outcome record budget")
            try:
                self.ledger.expect(Expectation(receipt.action_id, source, "WORLD", expected,
                                               opened, earliest, deadline, float(probability)))
            except ValueError:
                # Another process may have committed this event between get() and expect().
                pass
            record = self.ledger.get(receipt.action_id)
        if record is None or any(record.get(k) != v for k, v in expected_record.items()):
            raise ValueError("conflicting replayed T8 prediction")
        if record["status"] == "PENDING":
            try:
                result = self.ledger.resolve(
                    receipt.action_id, at=observed_at,
                    observed=not (cancelled or censored), evidence=evidence,
                    observed_outcome=actual_outcome, cancelled=cancelled, censored=censored)
            except ValueError:
                # A concurrent consumer may already have resolved the same receipt.
                result = self.ledger.get(receipt.action_id)
        else:
            result = record
        if not result or result.get("evidence") != evidence or result.get("observed_outcome") != actual_outcome:
            raise ValueError("conflicting replayed T8 outcome")
        intent = self.ledger.learning_intent(receipt.action_id)
        if intent is None:
            return {"outcome": result["status"], "prediction_error": None, "updated": False}
        if self.receiver.has_seen(receipt.action_id):
            return {"outcome": result["status"], "prediction_error": intent["prediction_error"],
                    "updated": False, "duplicate": True}
        if not optimizer_permission:
            return {"outcome": result["status"], "prediction_error": intent["prediction_error"],
                    "updated": False, "pending_optimizer": True}
        if not self.receiver.learning_enabled:
            return {"outcome": result["status"], "prediction_error": intent["prediction_error"],
                    "updated": False, "learning_disabled": True}
        try:
            delta = self.receiver.update(intent, receipt.action_id, authorized=True)
        except ValueError:
            # Close the has_seen()/update() race with the receiver's own lock.
            if self.receiver.has_seen(receipt.action_id):
                return {"outcome": result["status"], "prediction_error": intent["prediction_error"],
                        "updated": False, "duplicate": True}
            raise
        return {"outcome": result["status"], "prediction_error": intent["prediction_error"],
                "updated": True, "parameter_delta": delta,
                "scalar_readout": {role: self.receiver.read(role) for role in ("WORLD", "B1", "B2")}}
