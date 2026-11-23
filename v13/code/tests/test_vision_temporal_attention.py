import hashlib
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest

from v13.vision_temporal_attention import (
    REGION_IDS, TemporalUIAttentionError, TemporalUIAttentionRegistry,
)


def feature_rows(value=0.1):
    return [[value] * 37 for _ in REGION_IDS]


def update(registry, lease, *, source="screen", session="session", receipt="receipt",
           generation="gen", start=100, end=133, digest="a", rows=None):
    return registry.update(
        consent_lease=lease, source_id=source, capture_session_id=session,
        consent_receipt_ref=receipt, generation_id=generation,
        start_ms=start, end_ms=end, frame_sha256=hashlib.sha256(digest.encode()).hexdigest(),
        region_ids=list(REGION_IDS), feature_rows=feature_rows() if rows is None else rows,
    )


def test_warmup_then_localized_change_then_stable_frame():
    registry = TemporalUIAttentionRegistry()
    lease = object()
    first = update(registry, lease)
    assert first["status"] == "WARMUP"
    assert first["max_change"] == 0.0
    changed_rows = feature_rows()
    changed_rows[5] = [0.9] * 37
    second = update(registry, lease, start=133, end=166, digest="b", rows=changed_rows)
    assert second["status"] == "MEASURED"
    assert second["changed_regions"] == [REGION_IDS[5]]
    assert second["max_change"] == pytest.approx(0.8)
    assert second["interrupt_signal"] == pytest.approx(0.8)
    third = update(registry, lease, start=166, end=199, digest="b", rows=changed_rows)
    assert third["status"] == "DUPLICATE"
    assert third["changed_regions"] == []
    assert third["max_change"] == 0.0


def test_new_lease_receipt_session_and_generation_never_share_history():
    registry = TemporalUIAttentionRegistry()
    first_lease = object()
    second_lease = object()
    update(registry, first_lease)
    assert update(registry, second_lease, start=133, end=166, digest="b")["status"] == "WARMUP"
    assert update(registry, first_lease, receipt="new", start=133, end=166, digest="c")["status"] == "WARMUP"
    assert update(registry, first_lease, session="new", start=133, end=166, digest="d")["status"] == "WARMUP"
    assert update(registry, first_lease, generation="new", start=133, end=166, digest="e")["status"] == "WARMUP"


def test_time_regression_and_long_gap_reset_without_positive_change():
    registry = TemporalUIAttentionRegistry(max_gap_ms=200)
    lease = object()
    update(registry, lease)
    changed = feature_rows(0.9)
    regressed = update(registry, lease, start=90, end=120, digest="b", rows=changed)
    assert regressed["status"] == "TIME_RESET"
    assert regressed["max_change"] == 0.0
    gap = update(registry, lease, start=500, end=533, digest="c", rows=changed)
    assert gap["status"] == "GAP_RESET"
    assert gap["max_change"] == 0.0


def test_malformed_features_do_not_mutate_previous_snapshot():
    registry = TemporalUIAttentionRegistry()
    lease = object()
    update(registry, lease)
    malformed = feature_rows()
    malformed[0][0] = float("nan")
    with pytest.raises(TemporalUIAttentionError):
        update(registry, lease, start=133, end=166, digest="bad", rows=malformed)
    good = feature_rows(0.9)
    result = update(registry, lease, start=133, end=166, digest="good", rows=good)
    assert result["status"] == "MEASURED"
    assert result["max_change"] == pytest.approx(0.8)


def test_numpy_feature_rows_are_accepted_without_a_numpy_runtime_dependency():
    registry = TemporalUIAttentionRegistry()
    rows = [np.full(37, 0.25, dtype=np.float32) for _ in REGION_IDS]
    result = update(registry, object(), rows=rows)
    assert result["status"] == "WARMUP"


def test_bounds_and_reset_are_source_scoped():
    registry = TemporalUIAttentionRegistry(max_streams=2)
    leases = [object(), object(), object()]
    for i, lease in enumerate(leases):
        update(registry, lease, source=f"screen-{i}", digest=str(i))
    assert registry.stream_count() == 2
    assert registry.reset(source_id="screen-2") == 1
    assert registry.stream_count() == 1


def test_concurrent_updates_are_serialized_and_bounded():
    registry = TemporalUIAttentionRegistry(max_streams=4)
    leases = [object() for _ in range(8)]

    def run(index):
        return update(registry, leases[index], source=f"screen-{index}",
                      digest=str(index))["status"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(run, range(8)))
    assert statuses == ["WARMUP"] * 8
    assert registry.stream_count() == 4


def test_authority_is_never_escalated():
    registry = TemporalUIAttentionRegistry()
    result = update(registry, object())
    assert result["calibrated"] is False
    assert result["truth_authority"] == 0
    assert result["learning_authority"] is False
    assert result["action_authority"] is False
