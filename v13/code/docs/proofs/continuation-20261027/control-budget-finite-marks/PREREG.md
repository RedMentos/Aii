# WP-T14 control-budget nonfinite stage-mark review prereg (2026-10-27)

Exact parent `3a14e9bc62e19a58d6fa4bad1fcddbb3e9c179b2`, review-only branch `assistant/v13-control-budget-finite-marks-review-20261027`, not main. Prereg before RED tests and GREEN source. Owner: `v13/code/v13/control_budget.py` **candidate only**, new `v13/code/tests/test_control_budget_finite_marks_review.py`, isolated CI/proof. Frozen runtime not integrated.

Observed static issue: `control_budget.durations` accepts bool, NaN, infinity and negative cumulative stage marks because it only checks `isinstance(t,(int,float))`. It also raises on non-dict marks. These are invalid timing evidence for WP-T14, and may produce silent zero/incorrect control p95 or nonfinite JSON. Fail-closed rule: if any recognized stage mark is nonnumeric, bool, nonfinite or negative, return no durations for that turn; unknown stage keys are ignored. Non-dict metadata also returns no durations. Valid nonnegative finite marks and existing stage ordering stay unchanged.

RED: unit tests for bool, NaN, ±Inf, negative and non-dict marks, plus one valid stage sequence; malformed rows must not enter `latency` denominator. Original source expected to fail/throw on these controls; preserve raw. GREEN: minimal `math.isfinite` and strict type check in `durations`, no change to budget knobs, thresholds, resource/energy measurements, runtime routing or promotion gates. Focused CI and existing control-budget tests, compile/privacy/diff with original raw exits; full suite separately if useful.

No native/Redmi proof, no learned-control improvement, no Age promotion. LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; jepa_weight0; Age authority0; V13 incomplete.
