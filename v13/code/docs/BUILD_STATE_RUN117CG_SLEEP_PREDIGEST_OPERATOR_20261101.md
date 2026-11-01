# Run117CG BUILD_STATE — pre-digest operator workload visibility

2026-11-01 UTC. Review-only child of Run117CF PR #1559 at exact parent `4ff3a7efb657be7c14524fb9c05e954735e1d577`. Owner: Run117CG branch. Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

## Real usability gap

Run117CD's `:sleep digest` backlog counters were available only after the first digest state existed. Before the first Sleep cycle, the operator fallback returned only `session,text,entries`, hiding the number of pending FINAL turns and omitting explicit fact authority. This is misleading when an operator is checking whether a fresh Age-0 session needs a Sleep catch-up cycle.

Run117CG makes `sleep_offline.view` report the same diagnostic schema even with no persisted digest: `entries=0`, `text=''`, `fact_authority=0`, `pending_final_turns` counted from cursor zero and `catchup_pending`. It performs no Store mutation or source-text read for the count. Later persisted digest text still passes `_checked_digest_entries` and `native_history`. Counts may include subsequently revoked FINAL messages and are **not facts**. Source revocation remains authoritative for any displayed text.

## Proof plan and status

- New real Runtime/Store/Operator tests: empty new session, two source-bound FINAL turns before first digest, no state mutation, 2→0 after digest; revoked source before first digest stays absent from operator text and digest.
- Test blob `929f2133e66389a9060aad5edaf8903884e870a4`; source `sleep_offline.py` blob `dcaaf645d303fc4a4b18414fab4e3fa22957b41f`.
- Original RED Actions and terminal corrected GREEN: **PENDING** at initial checkpoint; verify raw ZIP CRC, all SHA256SUMS, all seven stage exits, test counts, privacy, source pins before claiming.
- Exact test command: `cd v13/code && python -m unittest -v tests.test_run117cg_sleep_predigest_operator tests.test_run117cf_sleep_blocked_fairness tests.test_run117cd_sleep_backlog_operator tests.test_run117cb_sleep_session_fairness tests.test_run117bz_sleep_digest_backlog tests.test_run117ca_sleep_context_consumer tests.test_sleep_digest_view_authority_run278 tests.test_sleep_offline tests.test_sleep_digest_live_lineage_run208 tests.test_context_os`.

## Unchanged gates and next work

Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, `jepa_weight=0`, no native/Redmi, no training, tool/output authority or whole-system completion. No production merge or model/cohort change. Next: terminal original raw audit, independent cross-session and restart counterexamples, review for user-facing integration. Remaining platform budget UNKNOWN.
