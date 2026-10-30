# G13 dispatch-time clock admission — isolated review-only candidate (2026-10-30)

Owner: GPT-6 scheduled continuation. Base: Run13A #1280 commit `5ba394d08ab9494d77f0b406b74ea931532b0388`. This is a separate G13 organ from active Context OS #1283 and full-task native Run13A. No production merge or native job.

## Observed code gap (before change)

`EventScheduler._post` rejects NaN/Inf clocks, but `EventScheduler._next` reads `self.clock()` without a finite check. For NaN, both `due > now` and `expires < now` are false. A due/TTL-bound event can be dispatched even though the clock is invalid. This violates the same G13 admission boundary already enforced at post time. For Inf, an event can expire without a valid clock.

## Prospective acceptance and counterexamples

- Fresh scheduler with two pending TIMERs: at NaN, +Inf, -Inf and nonnumeric clock values, `next()` must raise ValueError before any queue mutation, dispatch, expiry, telemetry, or counter changes. Compare full `report()` and `pending()` before/after each rejection.
- Restore finite clock: higher-priority due event dispatches once; valid TTL expiration continues to work; restart/retry accounting stays unchanged.
- Run existing `tests.test_scheduler_finite_boundary_20261029` and `tests.test_sleep_scheduler.SchedulerTests` plus new regression tests, compile, privacy scan, diff check.
- Explicitly keep Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 no promotion, Body-JEPA unavailable, jepa_weight=0, Redmi unmeasured. This is software-only infrastructure, not learned utility.
- No frozen source/model/seed/score change; no native model jobs. Failures remain failures; do not waive tests.

Exact next command after prereg: implement the minimal dispatch-clock guard and focused regression in an isolated review branch, then run the pinned GitHub Actions software workflow. Save original raw evidence and record tested HEAD before reporting GREEN.
