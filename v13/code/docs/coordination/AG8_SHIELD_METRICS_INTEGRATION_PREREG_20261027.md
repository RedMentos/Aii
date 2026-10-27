# AG8 complete regression shield metrics — current HX134 integration prereg (2026-10-27)

Review-only child of current HX134 request/evidence PR #789 at `7a56a53018fa6db9c0d783ee45065ee4dfaf4bed` (full CI running; do not claim it passed before verifying). Independent prior art **PR #375 / Run380**, tested source `8641e5216ee34730d7bfb1649c8c76d9c7cd4f40`, already supplied the precise fix and 7 tests on an older Codex branch; RED Actions `40239120314`, GREEN `40239288549`, original private artifact hashes in `RAW_VERIFIED.md`. This package integrates that proven regression-shield logic with the newer HX approval/request/evidence chain, preserving the new `require_approved_origin` helper.

## Falsifiable issue

Current `SelfImprovement.evaluate` accepts incomplete `overall/seen/unseen` axes, boolean/nonfinite/out-of-range scores, and one-sided forgetting coverage; it rounds deltas to four decimals before testing thresholds. This can create a `PENDING_USER` request from insufficient or regressing evaluation evidence. The user must still approve, but the regression shield must fail closed before asking.

## RED -> GREEN -> full acceptance

1. Commit exact `test_ag8_shield_metrics_run380.py` blob from PR #375 **before** production edit. Expect invalid/incomplete metrics and sub-rounding regressions to fail the test-only RED; preserve raw exits and all failed cases.
2. Merge only Run380's math/validation/unrounded comparison logic into current `v13/code/v13/agi/self_improve.py`; keep all current approval-origin and request-revocation checks intact. No change to model/seed/cohort.
3. GREEN: 17 Run380 checks plus current HX tests. Full Linux software suite, compileall, privacy scan, diff check, source blobs and private byte-verified raw artifacts.
4. No auto-approval, no live harness consumer, no Age/learning promotion; B3 L1 FAIL, STEP2 UTILITY_FAIL, LP1/LP2/BJ1 negatives, `jepa_weight=0`, authority0 and incomplete V13 remain.

Owner GPT independent integration reviewer. Allowed paths: `v13/code/v13/agi/self_improve.py`, `v13/code/tests/test_ag8_shield_metrics_run380.py`, dedicated workflow/coordination. Parent PR #789 and prior PR #375 untouched. Next command: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_ag8_shield_metrics_run380 tests.test_harness_hx tests.test_hx_approval_run133`.
