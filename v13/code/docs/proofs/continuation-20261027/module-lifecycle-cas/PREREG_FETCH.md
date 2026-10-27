# Post-quarantine-write fetch race — preregistration (2026-10-27)

Parent reviewed lifecycle CAS GREEN commit `2f7f18f25078fb7f828a6866b52a036f0bd4d088` (48 PASS), with durable checkpoint `3adb6bd8236f91f2ead474c89a272f6266f4bf6d`. Review-only branch; no production or frozen SourceHandoff mutation.

**New four tests committed before fix:** `abe9abce1dca53ed5aa717a102a02660a86410ab`, `tests.test_module_lifecycle_cas`. Interpose immediately after `atomic_write` returns but before `StateBox.mutate`. Cases: user revoke(delete=True), module disable, Notaus, typed NETWORK ban. Each must raise PermissionError, not promote to QUARANTINED/SANDBOX_OK, and leave no stale file for the now unauthorized proposal.

**Predicted baseline:** revoke/disable leave a stale file despite existing state CAS; Notaus/typed ban can promote to SANDBOX_OK because the existing post-fetch policy check occurs before file write. Do not change the original tests after observing failures except to fix a demonstrably broken fixture, and preserve all RED receipts.

**Planned bounded fix:** recheck policy and state after write and inside optimistic state transition; clean the just-written file only when no other authorized fetch has already claimed the same module state. Concurrent same-ID fetches and a revocation between final check and filesystem rename remain a separate ownership/transaction design question. Do not claim strict linearizability from these synthetic callbacks.

**Evidence:** synthetic SQLite with injected callbacks, not real network, native, model or Redmi. Existing original cohorts/hashes unchanged; negative gates STEP2 UTILITY_FAIL, B3 L1_FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, complete scope false.

## Observed original RED / preregistration correction

Actions `40465483085` at the test-only head `abe9abce1dca53ed5aa717a102a02660a86410ab`: **52 tests, 3 FAIL**, compile0, privacy CLEAN. The failed tests are disable, Notaus and typed NETWORK ban after `atomic_write`. The revoke(delete=True) case **already passed**: revoke's own unlink removed the file; the predicted stale-file hypothesis for this exact timing was disproved, not silently counted as a defect. ZIP artifact `12716705293` SHA256 `0c596a446a3f06e97fdbfc85d0d35bba0d3110cd77dede54ae7ab402c9c7129e`, CRC/HEAD/exits checked and privately byte-verified at `/V13-Checkpoints/2026-10-27/Module-Lifecycle-CAS/`. The remaining opposite ordering (revoke immediately **before** the atomic write) was not covered by the first four tests and requires an additional test.
