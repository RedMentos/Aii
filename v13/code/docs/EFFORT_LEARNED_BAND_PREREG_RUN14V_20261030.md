# Run14V — learned wake cannot exceed per-turn reasoning-effort band (2026-10-30)

Parent: World F4 Run14U PR #1337 at exact head `09f6ce79d1a7684a0421c6d509dc934218b71bf2`. Owner: GPT-6. Scope: `v13/code/v13/effort.py`, new `v13/code/tests/test_effort_learned_band_run14v.py`, workflows/checkpoint only. No canon, model, registered cohort or approval change.

## Observed bug

`resolve_wake(plan, learned)` applies only `plan['wake_ceiling']` (resource/deadline observer ceiling) and ignores `plan['band']` (actual per-turn effort budget). Under an adaptive DIRECT_C_NATIVE plan with observers available, a learned `both` proposal can wake both B bodies despite the no-body effort band; under C_NATIVE_ONE_BODY, `both` can also bypass the one-body budget. This violates the §10.2/§59 effort budget, creates unapproved latency/memory use and undermines C2/JEF routing evaluation. It is software logic, not native utility proof.

## Test-first contract

1. DIRECT_C_NATIVE never wakes a B body from any learned proposal, even when resource ceiling is `both`.
2. C_NATIVE_ONE_BODY can choose detail or gist but never both. Learned `both` is deterministically capped to the plan's preferred one body; `none` remains allowed.
3. FOCAL_TARGETED / DEEP_FOCAL may choose both if resource/deadline/observer rights allow it.
4. Hard resource/deadline/observers-off ceilings still win; explicit user-forced `detail`/`gist` modes remain nonlearned.
5. Unknown band or learned action rejects, not silently widened. Existing Effort, C2 deadline, resource-mode and runtime tests must pass.

Implement band-specific maximum `DIRECT_C_NATIVE→none`, `C_NATIVE_ONE_BODY→one`, `FOCAL_TARGETED/DEEP_FOCAL→both`, then apply existing resource/deadline `wake_ceiling`. No age or approval promotion, no autonomous body weights, no native model calls. Original test-first RED and candidate raw retained and privately backed up. Historical full-suite RED unwaived. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi unmeasured, whole system incomplete.
