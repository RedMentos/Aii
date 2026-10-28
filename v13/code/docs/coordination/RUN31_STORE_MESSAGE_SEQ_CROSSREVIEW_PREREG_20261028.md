# Run31 cross-review: Run28 user-message lineage + Run29 event sequence guard (2026-10-28)

**Parent:** Run28 integration review `731c0dc4b8d4ec9084fa206f853576a28e77ce43` (original Actions `40714867072`: 64 focused PASS, 2513 full tests with one unrelated `test_b3degrade.Live.test_promotion_needs_human_and_evidence_then_resource_mode_demotes` failure; raw preserved). **Independent donor:** Run29 PR #935 executable `5d42dd9c574dcb1474194995182b1daf0a464fed`, bridge blob `d958df02327034e644dc31185ccc71e5492d033f`, new test blob `f8c221691fb3ada5ae7f86e40ae2ed97c6b3b82f`, original RED/ GREEN raw independently verified. Run28's Run24 source adapter blob `fa8e290388386f279aa835633b8564f8f77cbe1f` and Run24 tests remain byte-identical.

**Implementation:** Import *only* Run29's bridge source and new tests byte-identically on a new child. Do not mutate Run28/Run29 owners, Run24 adapter, frozen Runtime/Store, original cohorts, models, seeds or main. The integrated path must reject both original user-message lineage forgery and after-evaluation `events.rowid` reordering with unchanged content SHA. Keep `SHADOW_ONLY`, `authority=False`, no F5/learning permission.

**Proof:** Run all Run17/18/19/20/21/22/23/24/27/28/29 focused tests and full suite on GitHub Actions, preserve raw ZIP, source hashes, privacy and original failure. If the unrelated B3 resource-pressure test fails again, diagnose independently without changing canonical gates or masking a real regression; do not claim GREEN from focused alone. Private backup and independent readback after success.

**Next command:** `cd v13/code && PYTHONPATH=.:tests python3 -m unittest -v tests.test_run24_message_source_lineage_review tests.test_run28_store_message_typed_integration tests.test_run29_store_seq_revalidation`. Continue native B1/B2/C3 utility separately.

**Gates:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi unmeasured; whole V13 incomplete. Remaining platform budget UNKNOWN.
