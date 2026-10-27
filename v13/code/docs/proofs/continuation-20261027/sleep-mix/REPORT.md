# WP-E Sleep replay mix / locked policy finite integrity — 2026-10-27

**Owner:** `codex/automation11-sleep-mix-finite-20261027`; review-only, based on PR #718 head `edd0212c1774f893433040f48fa6b57c3d2d4209`, not old `main`.

## Defect
`v13.sleep.validate_policy` accepted NaN and Infinity in the replay mix because `v<0` and `sum(m.values())<=0` are false for NaN. `ReplayQueue.sample` then computes bucket quotas and `int(quota)`, which raises or produces invalid sampling when the stored mix is nonfinite. An infinite total from individually finite large weights was also accepted. `quiet_hours` accepted bool as int; locked zero-valued safety fields could be replaced with bool and pass equality.

## Patch
- Reject replay mix unless it is a dictionary with exactly the three canonical keys, every weight is a finite nonnegative exact int/float, and the sum is finite and strictly positive.
- Require real integer hour values (no bool) and exact type+value for locked Sleep safety fields.
- No changes to replay mix defaults, sampling algorithm, Dream fact-write authority, age rights, native model execution, or scheduler timing.
- Regression tests reject NaN, +Inf, -Inf, negative values, overflowing total, bool hours, and bool-for-float locked authority. Failed `:sleep policy` updates must not alter persisted mix; a valid update remains accepted.

## Evidence and limits
Focused Linux software CI `.github/workflows/sleep-mix-finite-review.yml` at exact source SHA `70825cd1f96c0f1cd230bdbb0f07b9eccdf08f4c`, Actions run `40516161120`: **26/26 tests PASS**, compile PASS, privacy CLEAN, diff check PASS, no models downloaded. Native sleep, long-term retention, mobile power/thermal and complete V13 acceptance remain unproven. Original STEP2/B3/BJ1/age gates unchanged.

**Next command:** `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_sleep_scheduler tests.test_sleep_validation`.

**Next prerequisite:** exact-head CI PASS, independent review, then source-bound retention/utility tests. Do not treat finite-policy validation as a Dream/learning promotion.
