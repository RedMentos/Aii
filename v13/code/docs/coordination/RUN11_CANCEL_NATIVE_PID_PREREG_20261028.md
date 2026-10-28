# Run11 stage-19 cancellation PID proof — preregistration (2026-10-28)

**Owner:** GPT-6, review-only child of #872, based on `6862310c72db09522aaeb8da0817013c5b475c54`; parent #871 source-pinned native run 40649812006 remains RED (15 PASS, 5 FAIL). No production merge, no frozen evidence edit, no model/seed/fixture changes.

**Observed defect hypothesis:** Original `tests/integration_real.py` asserts `not r.pool.pids()` after cancellation. This conflates a cancelled runner's process with any unrelated resident role process; the original raw report records `cancel_native_process_stopped=false` while `runner.interruption_unload.process_reaped=true`. This *might* be a false-negative due to unrelated residents, but original artifact lacks `r.pool.pids()` and post-cancel OS PID identity, so **not yet proven**. Do not flip the original stage 19 verdict.

**Proposed narrow candidate:** After cancel, obtain the actual interrupted runner's PID from `runner.interruption_unload.before.pid` and require: (1) actual `CANCELLED` status, (2) explicit `process_reaped=true` from the real native runner, (3) positive integer PID, (4) that PID absent from current RunnerPool PIDs, and (5) the OS reports the exact PID no longer alive. Other resident PIDs are not automatically a failure. If the cancelled PID is still alive, missing, or the process-reaped proof is missing/false, fail closed. Record the PID set and the independent result in a new candidate report. No relaxation of cancellation timeout or process reaping itself.

**Counterexamples fixed before candidate:** missing/malformed/boolean PID; no reaped proof; wrong runner status; cancelled PID still in pool; cancelled PID alive in OS; unrelated resident PID alive while cancelled PID gone (must pass); unknown OS status/permission (must fail closed). Pure software tests exercise all cases. Do not monkeypatch actual native execution in the stage test.

**Verification:** compileall, focused unit tests, full existing Linux software suite, privacy and `git diff --check`, then only if heavy native owner free and exact installed models available, separately preregistered actual-weight stage-19 run on fresh isolated home. Keep original run 40649812006 RED regardless of new candidate results. No Redmi inference.

**Gate boundary:** STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight0, Age0 RECORD_ONLY, full V13 incomplete. Next command after prereg: implement helper and integration harness candidate, write independent negative-control tests, run CI and review.
