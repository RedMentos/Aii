# Run164 full-suite CI result — FAIL retained (2026-10-25)

Exact head `fb4d4f163b04e4b1b90d0f63209d65c5bf77c89b`; GitHub Actions `40164058854`, full-suite job `121081414527`. Privacy job PASS. Frozen Runtime, reconstructed LP3 helper Git hashes, pinned Run147 native fixture and isolated dependencies all PASS. **2358 tests, 5 FAIL, 11 SKIP, suite FAIL**; no claim of full-suite success. Closed raw log artifact `12587458300`, ZIP SHA256 `5895b6febf1e9410e6a9b04158d8a99cf312e6af0add527ba48a79b12f7daed0`.

The two Run159 ERROR conditions are no longer errors: reconstructed LP3 test module is imported and optional inaccessible /root fixture does not crash. The newly visible failures:
- `test_lp3_serial_cohort.SerialCohortTests.test_default_cli_read_only_blocks_missing_assets` and its inherited copies in `OrphanGroupReview` and `LockPoisonReview`: expected CLI rc=2, observed rc=1 (three failures). The captured stderr is not printed by the test; **cause unverified**.
- `test_lp3_serial_review_run18.OrphanGroupReview.test_successful_leader_with_live_descendant_is_not_success`: descendant remained alive after wrapper unlocked. Run21 test's `SyntheticCgroup.finish` is a no-op; no actual cgroup isolation or kernel cleanup was exercised. This is a **real software/synthetic regression/failure**, not evidence of successful kernel containment.
- `test_sleep_wake_index_run96.SleepWakeIndexRun96.test_real_scheduler_pending_survives_runtime_restart`: pending `REPLAY_DUE` not observed, **cause unverified**, could be scheduling timing or logic.

No failures are waived or converted to PASS. Next: reproduce CLI subprocess rc=1 with stderr capture and isolate the synthetic cgroup lifecycle; separately investigate Sleep/Wake timing. Do not run native LP3 model cohort or promote gates. `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `DS2_H2=FAIL`, `V13=INCOMPLETE`.
