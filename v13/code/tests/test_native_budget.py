import math

from v13.native_budget import admit_output_adapter


def test_c3_native_reserve_blocks_optional_adapter_near_deadline():
    assert not admit_output_adapter(7.9, 1.0)
    assert not admit_output_adapter(10.0, 2.0)
    assert admit_output_adapter(10.01, 2.0)


def test_c3_admission_fails_closed_for_invalid_budgets():
    for remaining, adapter in [(math.nan, 2), (math.inf, 2), (12, math.inf),
                               (-1, 2), (12, -1), ("12", 2), (True, 2)]:
        assert not admit_output_adapter(remaining, adapter)
    assert not admit_output_adapter(12, 1, native_reserve_seconds=0)


def test_c3_optional_admission_does_not_require_device_or_weight_change():
    assert admit_output_adapter(30, 3)
    assert not admit_output_adapter(8, 0)
