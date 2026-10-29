# S7 cross-page unresolved-user barrier — preregistration (2026-10-29)

Review-only child of PR #1118 exact head `4a6326c316042270a57da0b12869cc314b9f70d2`. Owner: this child branch only, `v13/code/v13/sleep_offline.py`, new Store-only test, scoped CI, this prereg. Do not change model/source/seed cohorts, Age rights, authority, or canonical gates.

## Original bug hypothesis

`digest` scans at most 64 oldest user rows and applies the interleaved-pending assistant barrier only if an unresolved user is *inside* that 64-row page. With 65 user rows, user 65 pending, then answers 1..64 committed **after** user 65, `len(settled)==len(users)==64`; the barrier is skipped and 64 entries are emitted. This contradicts the existing S7 conservative cross-interleaving rule exercised by `test_late_earlier_answer_must_not_skip_interleaved_pending_user` for two rows. User cursor may avoid permanent skip, but should not silently change the established source-order barrier at a page boundary.

## RED/GREEN and regressions

- Real Store, 65 users, first 64 FINAL assistants written after user65, user65 pending: `digest` must return 0 until user65 settles; original expected RED (64).
- After user65 FINAL, digest pages 64 then 1 in user order, source-exact, no duplicates, including restart.
- Fully settled 130 users with reverse assistant completion must retain existing 64+64+2 progression.
- Pending user may be beyond page 65 (e.g. 70) with earlier completions after it; cannot bypass through a single next-user check.
- Candidate should check only unresolved user rows in the source-order interval crossed by the current page's assistant completions. Use indexed SQL and `LIMIT 1`, no full source or model scan; retain the existing 64-user/8-session/96-entry caps. If the bound cannot be proven without an unbounded read, fail closed and document.
- Run original test-only RED, exact-head focused/full software, compileall, privacy and diff checks; preserve inherited REDs and all negative gates.

Evidence level: software/real SQLite only, no native/Redmi, no new learning authority. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, AG6 unapproved, V13 incomplete.
