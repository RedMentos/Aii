# Core & Harness — fair B1/B2 recovery test checkpoint (2026-11-23 22:08 UTC)

## Verified change
- Branch: `core/v14-fair-b1-b2-preanswer-budget-20261123-run1`
- Release base: `8d93236c753f0194224c19edc7411d8d7082b1d6`
- Commit: `61509b1b061b377d5c19f69d861acda6f7b9f07e`
- PR: [#2458](https://github.com/RedMentos/Aii/pull/2458), DRAFT / NOT_RELEASED.
- Changed only `v13/code/tests/test_observer_schedule.py` in this checkpoint.
- The Runtime integration fixture now explicitly provides a 10-second recovery pre-answer window with a 40-second C3 reserve (50-second total test deadline). It no longer assumes that a 30-second turn has enough time for two pre-answer passes after real setup overhead.
- Added a deterministic 1.5-second scheduler regression: the first role's 0.75-second slice is below the 1-second floor, so it is deferred; the peer receives the full 1.5 seconds and remains eligible. Existing Runtime post-commit logic can then recover the missing role without altering the committed answer.

## Test evidence
- LOCAL_LINUX / CPython 3.13.5: PASS — isolated helper probe compiled; exercised the exact budget arithmetic and sequential scheduler algorithm. For a 30-second recovery turn, reserve=26s and initial pre-answer window=4s; after 3s of setup only the second role has a 1s slice. For a 50-second fixture, reserve=40s and initial pre-answer window=10s; after 3s setup both roles still have 3.5s/7s slices. This is an isolated logic probe, not the repository test suite.
- LOCAL_LINUX full Aii pytest: BLOCKED / NOT_RUN — no checkout mounted; `git ls-remote` cannot resolve `github.com`.
- Exact-head Actions for commit `61509b1b061b377d5c19f69d861acda6f7b9f07e`: run [45276837088](https://github.com/RedMentos/Aii/actions/runs/45276837088), `startup_failure`, no jobs; no CI PASS.
- The previous Boss review on #2458 identified nested Runtime/source-pin and A5 Store-pin failures on an earlier head. This checkpoint does not relax or edit those pins. Exact current-head staged/integrated/migration CI remains unverified.

## User/device effect
- Improves test determinism and explicitly verifies fair role admission under a controlled deadline. It does not change installed Runtime behavior beyond the already-open #2458 candidate.
- Canon path: V14-001, A/B body scheduling -> C4/JEF -> C3; preserves both B1_DETAIL and B2_GIST roles, source-bound offers, peer communication, and the existing post-commit observer fallback.
- Redmi: latest public technical evidence in issue #1904 says the AI runtime is STOPPED_BY_USER; private receipt #826 reported stop/autostart false and native residency unavailable. No restart, CHAT_SEND, UPDATE_REQUEST, shell, permission change, model/weight swap, or data operation was performed. REDMI_UNVERIFIED.

## Blockers and next action
1. Boss/Integrator: rebind the immutable JEPA/integrated-online-world and post-commit Runtime source pins against the current candidate; do not weaken them.
2. QA/Android: re-run the A5 Store lifecycle pin after the Store source restoration.
3. Then run exact-head Python 3.13/3.14 staged, integrated and migration tests; independently review the #2458 scheduler tests.
4. Only after exact CI and release review should any update flow be considered. The device remains stopped; no user action is needed.
