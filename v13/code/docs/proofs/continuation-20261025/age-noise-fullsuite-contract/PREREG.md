# Age noise-aware full-suite contract reconciliation (2026-10-25)

Base: independently verified WP-T8 PR252 head `5a1c7b574a96f3a248ab779126f6f3985ed15a1f`. Exclusive ownership: historical `v13/code/tests/test_ablation99.py` **test only**, new CI workflow and this proof folder. No AgeControl implementation, Runtime, native models, DS3 owner, WorldModel owner, permissions or gate edits.

Existing source-bound Run221 full-suite RED: https://github.com/RedMentos/Aii/actions/runs/40180545459 ; 2646 tests, 2 FAIL, 36 historical candidate source-mismatch ERROR, 14 skips. One failure: `AgeNoiseAware.test_noise_band_blocks_demotion_but_not_real_drop` expects `FAIL_WITHIN_NOISE_BAND` when `regression_pass=False`. This conflicts with later Run200 safety hardening (PR228): competence-only noise must never mask an explicit regression failure, or failures in retention/stability/calibration/memory_health/safe_self_control/experience. Run200's dedicated tests explicitly require demotion after two such failures.

Contract: retain the historical noisy high-competence priming, noise MAD observation, stage>0 and low-plasticity checks. Replace the stale false-regression waiver assertion with the stronger expectation: first explicit regression failure is counted (not waived), second demotes; then two severe competence failures cannot promote or erase the demotion. Do not change production AgeControl or delete/skip any test. The separate Run200 test `test_competence_only_noise_still_suppresses_single_metric_failure` must remain PASS for genuine competence-only noise.

Verification: actual-source focused `test_ablation99.py` and `test_age_noise_maintenance_run200.py` on Linux with no native inference; preserve exact raw logs and privacy scan. Full suite still RED for LP3 orphan and historical native-firing source mismatch until separately fixed; do not claim otherwise.

Gates remain STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 incomplete.
