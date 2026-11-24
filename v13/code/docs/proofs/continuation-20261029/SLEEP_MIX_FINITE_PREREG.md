# Sleep/Dream replay-mix finite-input integrity — prospective prereg (2026-10-29)

Owner: GPT-6 independent Sleep A/B/C policy package, child of Self/World PR #1085 exact parent `46d0b7e665bb88c3a6e76c51a6ec201010704d1c`. No edits to Context OS, Self/World, JEF, frozen model or evidence cohorts.

## Source-level failure

`v13/sleep.py::validate_policy` validates individual bounded sleep knobs but accepts `mix.recent=float('nan')` and `mix.recent=float('inf')` because `v<0` is false and `sum(mix.values())<=0` is also false for NaN. An unbounded sum of large finite mix weights can overflow to infinity. `ReplayQueue.sample` subsequently computes `int(n * mix / total)`, which may raise ValueError/OverflowError on nonfinite quota. `quiet_hours=[True,False]` is also accepted because bool subclasses int. Invalid input must be rejected *before* persistence or scheduling, not deferred to JSON serialization or background sampling.

## Scope and acceptance

Make `validate_policy` reject non-dict mix, nonfinite/non-numeric/bool/negative weights, nonfinite or zero total, and bool quiet-hour values. Preserve existing valid weights, overnight quiet hours, default policy, sleep phase gates, DREAM.fact_write_gain=0 and all locked authorities. No behavior change for valid replay sampling. Red-first direct policy tests for NaN, +/-inf, overflowed sum, bool quiet hours, bad shape; valid zero component with positive total and overnight hours accepted. Integration test `SleepCycle.set_policy('mix.recent','nan')` rejects with no Store state mutation; existing Sleep scheduler and full software suite remain green. Hash-bound source-only CI and raw artifacts; no model/native/Redmi evidence.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; AG6 unapproved; Redmi unmeasured; V13 INCOMPLETE. A verified checkpoint is not a stopping condition.
