import pytest

from v13.vision_temporal_evidence import (
    TILE_IDS,
    TemporalVisualEvidenceError,
    TemporalVisualEvidenceRegistry,
)


def tiles(value=0.25):
    return {tile: [value] * 16 for tile in TILE_IDS}


def update(registry, start_ms, end_ms, receipt):
    return registry.update(
        capture_session_id="capture-session",
        generation_id="generation",
        consent_receipt_ref=receipt,
        session_consent_receipt_ref="session-consent",
        start_ms=start_ms,
        end_ms=end_ms,
        tile_luminance=tiles(),
    )


def test_backward_start_is_rejected_even_when_end_advances_and_state_recovers():
    registry = TemporalVisualEvidenceRegistry()
    first = update(registry, 100, 140, "receipt-1")
    assert first["status"] == "WARMUP"
    with pytest.raises(TemporalVisualEvidenceError, match="starts must be monotonic"):
        update(registry, 90, 180, "receipt-2")
    recovered = update(registry, 140, 180, "receipt-3")
    assert recovered["status"] == "MEASURED"
    assert recovered["gap_ms"] == 0
    assert recovered["state_reset"] is False


def test_equal_start_cumulative_windows_remain_valid():
    registry = TemporalVisualEvidenceRegistry()
    update(registry, 100, 140, "receipt-1")
    second = update(registry, 100, 180, "receipt-2")
    assert second["status"] == "MEASURED"
    assert second["gap_ms"] == 0


def test_end_order_rejection_keeps_both_interval_baselines():
    registry = TemporalVisualEvidenceRegistry()
    update(registry, 100, 140, "receipt-1")
    with pytest.raises(TemporalVisualEvidenceError, match="advance monotonically"):
        update(registry, 120, 130, "receipt-2")
    with pytest.raises(TemporalVisualEvidenceError, match="starts must be monotonic"):
        update(registry, 90, 180, "receipt-3")
    recovered = update(registry, 120, 180, "receipt-4")
    assert recovered["status"] == "MEASURED"
