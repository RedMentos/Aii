# Run88 prereg — exact human rule authority rollback across offline backup restore (2026-10-29)

Owner GPT-6 scheduled continuation. Independent review-only child of GREEN Run83 #990 exact `3545dab0faa3d548df58557ed8376a6162c51d9a`, Actions 40783355033 SUCCESS. Separate from Run84 #991 (GREEN exact-rule lifecycle) and Run86/87 emergency-stop studies; no import or overwrite of their tests, models, cohorts, hashes or raw evidence. No native model calls, no user data, no production source changes.

## Frozen E2E test plan
1. Real Linux Runtime/SQLite Store/Operator in fresh temporary home, Sleep disabled, Age0 RECORD_ONLY. Capture active rules, rule generation/version and exact-match result None for `What is two plus two?`.
2. Human operator proposes `:rules fixed "What is two plus two?" "4"`, obtaining a PENDING request ID. Confirm no active fixed rule or generation change. Make `:backup` snapshot **before approval** and verify backup manifest hashes/models_included=false.
3. Explicit `:approve <exact request id>` makes exact rule active (`4`, `model_generated=false`, `APPROVED_FIXED_RULE`); generation changes. A near-match remains unmatched. Close runtime.
4. Offline `backup.restore(home,snapshot)` must produce a separate safety backup. Reopen: active rules and generation must match **preapproval snapshot**, and the formerly approved fixed answer must be absent. It must not be silently reapproved by replay, restart, backup metadata or native models.
5. Recovered request may remain PENDING as at snapshot. Only a new explicit `:approve <exact request id>` may reactivate it. Verify exact-only answer after approval and persistence through another restart; no other rule or Age promotion.
6. Source-bound focused/full Linux software tests, compile, privacy, diff and closed SHA256SUMS raw logs. Preserve original RED if observed. Never treat an automatic restore safety backup as proof of real phone durability.

This is a local **authority/recovery** test, not C3/B1/B2 semantic learning or model quality. Keep STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, native/Redmi unmeasured, whole-system incomplete, no main merge.
