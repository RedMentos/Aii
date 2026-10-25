# Run341 preregistration — repair obsolete Fast-Forward sleep test without weakening receipt integrity

2026-10-25 UTC. Owner: `v13/code/tests/test_sleep_offline.py` and isolated source-only proof only; parent Run340 PR #336 exact head `28f0a0a5bb7aafaafb2720ecd453b3f8661d0f06`. No changes to `v13/fastforward.py`, Store, Runtime, native models, Canon, Age/learning/approval gates or any frozen cohort.

## Observed RED and cause

Run338 exact-head full suite CI 40220291845, raw ZIP SHA256 `281b6502898768ebe5c73be691c21294a5f1abe34a9d28f47b1912d65167942f`, 3009 tests, 2 FAIL, 39 ERROR, 15 skips. `test_sleep_offline.PredictorTests.test_consolidation_keeps_only_if_heldout_error_does_not_rise` calls `FastForward.learn('e', ...)` **40 times with different features/outcomes**. Current `FastForward.learn` intentionally binds one exact outcome to one event ID with a durable SQLite receipt and rejects conflicting replay; the test is obsolete, not evidence to relax idempotency. This is separate from Run340 cancellation and other source/fixture errors.

## Frozen patch

Replace only the repeated constant event ID in that test loop with unique `'e-%d' % i` IDs. Add an explicit regression that replaying the **same** event ID with conflicting features/outcome raises `ValueError('Conflicting Fast-Forward outcome replay')` and does not increment learned count, while exact duplicate replay remains idempotent. Run `tests.test_sleep_offline.PredictorTests` and existing `tests.test_fastforward` if available, source-only with pinned deps, privacy, raw SHA. No synthetic pass promotes native learning or full-suite green; preserve all other Run338 failures/errors and original negative gates.
