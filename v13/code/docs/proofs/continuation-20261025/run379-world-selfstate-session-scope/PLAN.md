# Run379 preregistration — F4 SelfState session-scoped unfinished actions

2026-10-25; owner: this independent Codex continuation. Parent: verified Run376/PR371 review head `29669bbe05049199feb7cda2be233d11f08e3362`. Run377 Context OS and Run378 B3 Callosum remain independently owned, unintegrated RED branches. Scope of this package: `v13/code/v13/world.py` (only the SelfState unfinished-action count), `v13/code/tests/test_world_selfstate_session_run379.py`, `.github/workflows/run379-world-selfstate-session.yml`, and this proof directory. No change to frozen source cohorts or model, seed, configuration, authority, age or permission.

## Bug hypothesis / RED-first contract

`WorldState.self_state()` reports a `session_id` and persists `SELF_MODEL:<session>`, but its `unfinished_actions` SQL counts **all** DISPATCHED/OUTCOME_UNKNOWN actions in the database, including unrelated chat sessions. The WorldState forecast and observation paths already isolate sessions. This misreports another session's work as the current session's unfinished work.

RED test on actual Runtime/SQLite: create one DISPATCHED action in session A, two unfinished actions in session B (including OUTCOME_UNKNOWN); assert A=1 and B=2 despite global=3. Finish a B action and assert A remains 1, B=1. Restart runtime, switch between sessions, assert values and session_id remain stable. Include zero-action session C, plus ordinary single-session baseline. Do not invent native/model measurements. Before production patch, require expected failure from cross-session assertions, while existing `tests.test_world_state` and `tests.test_world_multiaction_recovery_run343` remain green.

GREEN fix candidate: replace only the global unfinished count query with a join to `events` filtered on `r.session`. Keep statuses and result schema unchanged; do not alter any other SelfState counters until their scope is independently established. Run new + inherited suites, compileall and official privacy scan. Exact HEAD and raw logs + sha256 manifest must be preserved; preserve RED evidence. No promotion of STEP2, B3, Body-JEPA, jepa_weight, phone-native, or whole V13.

## Claim limit and continuation

This tests a local SQLite session accounting invariant only. No evidence of learning quality, physical concurrency or Redmi performance. After verified GREEN checkpoint, next independent work should address blueprint utility/learning gates rather than expanding unrelated helper scaffolds. Record current owner, source hashes, CI run, next command and unresolved blockers in BUILD_STATE_RUN379.json.