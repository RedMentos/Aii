# Run340 preregistration — terminal non-FINAL turn releases every resident native role

2026-10-25 UTC. Owner: isolated `v13/code/v13/runtime.py` coordinator finalizer and new regression tests only. Parent Run339 PR #335 exact head `88b4edc8d0bb1368deca2f809f2bdc0190babfac`; do not edit Run339 native/seed/cohort, Run336/334 source, Canon, Age/approval/learning gates, models or weights.

## Exact RED before implementation

Run338 exact-head full Python suite CI 40220291845, raw artifact 12609537785, ZIP SHA256 `281b6502898768ebe5c73be691c21294a5f1abe34a9d28f47b1912d65167942f`, 12/12 SHA manifest entries independently verified: **3009 tests, 2 failures, 39 errors, 15 skips**. One genuine isolated failure: `test_cancel_resident_cleanup_run284.test_cancel_reaps_all_resident_roles_not_only_active_runner` expected empty resident PID list after CANCELLED, observed fake B1/B2 PIDs [284001,284002]. The test substitutes `Runtime._turn` with an actual persisted SQLite turn to exercise the coordinator finalizer, bypassing any internal `_turn` cleanup. `RunnerPool.unload()` already releases all resident roles, but `Runtime._worker` finalizer did not invoke it on terminal non-FINAL turns. Normal FINAL must retain resident roles for reuse.

Other Run338 failures/errors (native firing source-binding drift, missing historical LP3/Run147 fixtures, stale Run177 hash, fastforward duplicate event receipt test) remain separate RED. No whole-suite PASS claim.

## Frozen patch and tests

In the coordinator worker's **terminal turn finalizer**, after `_turn` has returned/failed and before the worker releases its current slot, unload all `RunnerPool` residents and `NeedleRunner` only for terminal statuses `CANCELLED`, `DEADLINE`, `ERROR`, `INTERRUPTED` (never `FINAL`). Do not terminate a runner concurrently inside `Runtime.cancel()`; keep cancellation cooperative. Attempt cleanup even if SQLite finalization fails; log cleanup exceptions without losing the persisted turn or claiming a process was reaped. Do not change `RunnerPool` itself or change normal FINAL reuse.

Tests: original Run284 cancelled/final cases; new source-only worker finalizer negative controls for ERROR and INTERRUPTED, idempotent empty pool and unchanged FINAL retention. Run on exact review branch with privacy and source hashes. Native/Redmi process-reap proof remains MISSING: fake inert PID holders only, no hardware claim. STEP2/B3/Body-JEPA/jepa_weight/V13 gates unchanged.
