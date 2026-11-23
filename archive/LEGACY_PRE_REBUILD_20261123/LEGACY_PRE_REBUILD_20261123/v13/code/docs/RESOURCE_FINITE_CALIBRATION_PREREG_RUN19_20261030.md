# Run19 preregistration — §97.2 measured resource profile finite/provenance admission (2026-10-30)

Review-only child of Run18 PR #1345 exact parent `bb271d1f755dea6c8f0cdb4d4cffac0f606e8587`. Owner GPT-6. Scope `v13/code/v13/resource_modes.py`, new `tests/test_resource_finite_calibration_run19.py`, isolated Actions and scoped BUILD_STATE. Canon SHA `218464b12a2d27d92524c751922fa8e1c3fb0ea7`; all model/source/seed cohorts and other organs unchanged.

## Defect hypothesis

`calibrate()` accepts `float('inf')` as positive body RSS, and accepts nonfinite or boolean measured thermal values. `validate()` permits some infinite numeric threshold sets; a corrupted stored profile can thus be reloaded as measured instead of BOOT. Both `boot_profile()` and `calibrate()` use truthiness of `device_info['android']`, so string `"false"` can falsely promote host measurements to `DEVICE_MEASURED`/Redmi evidence.

Frozen test-first:
1. `calibrate()` rejects NaN/Inf/booleans and nonpositive B1/B2 RSS before any measured profile is returned; exact finite positive measurements preserve existing thresholds.
2. Thermal RED/ORANGE/YELLOW rejects nonfinite, boolean and nonnumeric values; valid ordered finite thermal values accepted.
3. `validate()` rejects persisted NaN/Inf/boolean mem/temp/rss thresholds. `load_profile()` returns UNCALIBRATED BOOT for corrupted Store state (does not silently claim device calibration).
4. `device_info.android` must be exact boolean True to mark `DEVICE_MEASURED`; `"false"`, `1`, `None` and false default remain `HOST_MEASURED_NOT_REDMI` (BOOT status not Redmi).
5. Existing resource modes, body residency, Sleep F9, effort C2 and age tests remain unchanged.

No claim that host synthetic measurements are Redmi proof. Preserve Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE and jepa_weight=0. Software-only Linux test-first RED then candidate GREEN; raw hashes, stage exits, private readback, historical full-suite failures unwaived.
