# G13 burnout-budget rollback guard — prospective isolated candidate (2026-10-30)

Owner GPT-6; base verified G13 dispatch clock PR #1284 at docs checkpoint 501042c1581b226bf1cc24be0e939880a2393cd4. Independent of active native Run13A and Context OS. No production merge.

## Observed failure mode before implementation

`EventScheduler.background_since_input()` counts dispatch timestamps `>= MAX(accepted_turns.accepted_at)`. If the last accepted turn timestamp is in the future relative to a rolled-back wall clock, all current dispatch timestamps are older than the future timestamp. The counter then stays zero and a configured burnout budget may never exhaust, allowing repeated background dispatches despite the user-turn boundary. A malformed accepted timestamp can also make comparisons fail.

## Prospective checks and claim limits

1. With burnout budget 1, a real Store accepted-turn timestamp ahead of scheduler clock must conservatively exhaust the budget (return >1000), and a queued background `IDLE/sleep_a` must not dispatch. Pending state and dispatch counter remain unchanged.
2. After clock catches up to the accepted timestamp, the same queued wake can dispatch normally and subsequent background attempts obey budget 1.
3. A malformed accepted-turn timestamp (TEXT in SQLite REAL column) must fail closed, not cause a TypeError that kills a worker or a zero-count bypass. A direct invalid scheduler clock must raise ValueError without modifying state.
4. Foreground `USER_INPUT` remains available; a clock rollback must not suppress the user's own input path. Existing retry, priority, finite admission and pause tests remain passing.
5. All gates unchanged: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi UNMEASURED. Software-only, no learning/native jobs.

Implementation plan: use a finite scheduler clock and validated accepted timestamp in `background_since_input`; if accepted timestamp is future/malformed, return conservative `DISPATCH_LEDGER_MAX` (1001) rather than zero. Preserve historical dispatch ledger and no-clock-drift behavior. Run prospective focused tests and pinned CI with raw evidence, privacy, diff, compile, and Canon pin. No source/model/seed/scorer changes.

Exact next command: implement guard in `v13/code/v13/scheduler.py`, new `tests/test_scheduler_burnout_rollback_20261030.py`, run GitHub Actions on review branch, inspect result before any promotion.
