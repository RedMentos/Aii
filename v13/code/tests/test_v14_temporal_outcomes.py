"""Synthetic V14 temporal outcome tests; not native Android evidence."""
import pytest
from v13.temporal_outcomes import TemporalOutcomes, ExpectationError


def test_outcome_omission_censorship_and_restart(tmp_path):
    path = tmp_path / "outcomes.sqlite"
    clock = lambda: 100.0
    ledger = TemporalOutcomes(path, clock=clock)
    first = ledger.predict(source_ref="event:1", owner="WORLD", outcome="reply",
                           probability=.8, earliest=101, deadline=110)
    second = ledger.predict(source_ref="event:2", owner="ACTION", outcome="reply",
                            probability=.8, earliest=101, deadline=110)
    third = ledger.predict(source_ref="event:3", owner="SELF", outcome="reply",
                           probability=.8, earliest=101, deadline=110)
    assert ledger.resolve(first, observed=False, evidence_ref="sensor:partial",
                          at=111)["prediction_error"] is None
    assert ledger.resolve(second, observed=False, observation_complete=True,
                          evidence_ref="sensor:continuous", at=111)["prediction_error"] == pytest.approx(-.8)
    assert ledger.resolve(third, observed=True, evidence_ref="event:reply",
                          at=112)["status"] == "DELAYED"
    with pytest.raises(ExpectationError):
        ledger.resolve(second, observed=True, evidence_ref="event:reply", at=112)
    ledger.close()
    restored = TemporalOutcomes(path, clock=clock)
    assert restored.pending() == []
    restored.close()


def test_no_unobserved_omission_and_validation(tmp_path):
    ledger = TemporalOutcomes(tmp_path / "outcomes.sqlite", clock=lambda: 100)
    key = ledger.predict(source_ref="source:1", owner="B1", outcome="reward",
                         probability=.9, earliest=100, deadline=110)
    with pytest.raises(ExpectationError):
        ledger.resolve(key, observed=False, observation_complete=True,
                       evidence_ref="sensor:continuous", at=105)
    with pytest.raises(ExpectationError):
        ledger.predict(source_ref="source:2", owner="WORLD", outcome="reward",
                       probability=float("nan"), earliest=100, deadline=110)
    assert len(ledger.pending()) == 1
    ledger.close()
