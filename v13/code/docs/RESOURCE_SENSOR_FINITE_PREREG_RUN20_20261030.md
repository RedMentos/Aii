# Run20 preregistration — §97.2 nonfinite live resource sensor fail-closed (2026-10-30)

Review-only child of Run19 PR #1346 at exact parent `07b72767342308567cd32e562d3166fb397f56ce`. Owner GPT-6. Scope `v13/code/v13/resource_modes.py`, new `tests/test_resource_sensor_finite_run20.py`, isolated CI and BUILD_STATE. Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7`, unchanged. Distinct from Run19 calibration: this guards *live* classification and previous-mode hysteresis, not stored profile admission.

## Bug hypothesis

`classify()` treats NaN/Inf in `mem_available_bytes`, `battery_temperature_c`, or measured own process RSS/PSS as ordinary numbers. Comparisons against RED/ORANGE/YELLOW thresholds are false for NaN, potentially reporting GREEN on a malformed sensor snapshot. An invalid reading must never downgrade an already stricter RED/ORANGE state, and should at least enter YELLOW with an explicit invalid-reading reason. Missing `None` sensors remain the legacy unmeasured case (GREEN from fresh boot), not fabricated RED evidence.

Frozen tests before source patch:
1. Valid finite snapshots preserve GREEN/YELLOW/ORANGE/RED boundaries and hysteresis.
2. NaN, ±Inf, booleans, negative memory bytes and nonnumeric memory/temperature readings cannot yield GREEN from a GREEN prior; result YELLOW with explicit reason.
3. From previous ORANGE or RED, malformed sensors cannot relax the mode.
4. With Android RSS profile active, nonfinite/negative/bool process RSS or PSS must fail closed, while missing process measurements remain unmeasured and do not fabricate a number.
5. Real ResourceGuard updates use the fail-closed mode, and existing resource modes/effort/Sleep tests remain unchanged.

No native/Redmi measurement; no new thresholds, models, seed changes or age rights. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0. Preserve test-first original RED and candidate raw, hashes, privacy, private readback, historical unfiltered failures unwaived.
