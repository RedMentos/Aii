# Run589 prospective registration — Sleep FULL truthful completion and cancellation (2026-10-26)

Owner: GPT automation11. Independent review branch based on verified Run588 PR584 checkpoint `5d007b19c7fe4bf5fe361de1c2e3eca07eaab714`. File ownership: `v13/code/v13/sleep.py` only, new `v13/code/tests/test_run589_sleep_full_integrity.py`, Run589 CI/proofs. No Canon/frozen source/model/seed changes, no native/Redmi, no other owner overwrite.

**Read-only defects in existing SleepCycle.run:**
1. In `mode='full'` under `resource_state='PRESSURE'`, Sleep A/B are skipped, only Sleep C runs, yet report status becomes `DONE` and `st.last_full` is advanced. This can misrepresent an incomplete full night and suppress the next full attempt; a caller could also use the DONE result to schedule slow learning/AG6.
2. `st.last_full` is advanced *before* computing the final phase status, even if a phase returned `INTERRUPTED`. A cancelled full sleep therefore delays retry.
3. When an earlier full phase returns `INTERRUPTED`, later phases B/C are still invoked; they should not be entered after cancellation. The scheduler must retain restart/retry opportunity.

**Prospective behavior:** Under PRESSURE, a full request may still perform the already-authorized Sleep C maintenance but must report `SKIPPED_RESOURCE_YELLOW`, not DONE; keep `last_full` unchanged. A full cycle advances `last_full` only after an actual `DONE` report. If Sleep A/offline/B returns INTERRUPTED, skip later phases and return INTERRUPTED. Preserve direct `mode='c'` under PRESSURE as DONE. Do not promote age rights, dream hypotheses, native training, weight changes, or evidence claims. Keep `_finish` raw report/schedule persistence and existing scheduler contract.

**Prospective tests:** Actual Runtime/SQLite cycle with controlled resource and phase hooks: full PRESSURE -> only C, not DONE, last_full unchanged; full interrupted A -> no B/C/offline, last_full unchanged; offline interrupted -> no B/C; B interrupted -> no C; successful full -> last_full advances; explicit C under PRESSURE -> DONE; persistent restart retains last_full. Run existing `test_sleep_scheduler`, `test_sleep_policy_finite` and relevant sleep tests in exact-head Actions with compile/privacy/SHA-closed raw. Preserve failures.

**Claim limits:** software-only, no learned Dream/Sleep, no native or Redmi proof. Original unfiltered suite RED (4 FAIL/65 ERROR) due frozen source lineage; STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, jepa_weight 0, V13 INCOMPLETE. Independent review before integration.
