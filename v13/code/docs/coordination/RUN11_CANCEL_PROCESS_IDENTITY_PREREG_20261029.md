# Linux-native cancel process identity — independent prereg (2026-10-29)

Isolated review child of historical 20-stage native acceptance PR #871 head `e719910f02b4d4af50ac245cd8175cef287dff4b`, **not** the current integrated V13 branch. Owner: this branch only, `v13/code/tests/integration_real.py`, one new software regression, scoped CI, this prereg. No frozen model/source/seed/20-stage evidence edited.

## Closed original evidence

Original 20-stage native run `40649812006` at workflow source `4f106ad6b63977cdec1a4d9050ee2c361fe36260`: **15 PASS / 5 FAIL**; original FINAL raw artifact `12800785500`, ZIP SHA256 `5d496cc71fe72a8b79aa5a099019b5872c5c6f9dbec064e7f8cea662966228fb`, 75/75 internal SHA256SUMS and CRC verified, private Library byte-exact. Failed stages: readouts (halt gate), control-calibration (support), memory-retrieval (native human-source answers), output-adapter (calibration and first-token accuracy), cancel-restart (cancel_native_process_stopped only). The cancel-stage JSON records `runner.interruption_unload.process_reaped=true` and original native worker PID 8454, but `native_process_stopped=false` is defined as `not r.pool.pids()`; the pool includes **all resident roles**, so an unrelated resident model can cause a false-negative. Do not declare cancellation GREEN until an exact new native rerun.

## RED/GREEN tests

- Synthetic pool with canceled PID absent but unrelated live PID present, and authentic-shaped `runner.interruption_unload.before.pid`, `process_reaped=true`: worker-specific check passes while old `not pool.pids()` fails.
- Canceled PID still resident or `process_reaped=false` or missing PID: check fails.
- Process-aliveness check: if PID is still alive in OS, check fails; synthetic software unit test uses mocked process query, no native claims.
- Candidate helper in `tests/integration_real.py` only: verify reaped cancellation PID no longer in pool and no longer OS-live; preserve other roles and the existing restart/record-only checks. No relaxation of real native kill/reap requirement.
- Original software RED before patch, focused/full tests after patch, then **separate serial pinned native cancel-stage rerun** (not the whole 20-stage cohort) with raw model/runner/seed/source hashes, no concurrency with other heavy native owners. If unavailable, leave native cancel gate RED and document.

No native run is authorized to alter the original cohort. Negative gates unchanged: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; Redmi unmeasured; full V13 incomplete.
