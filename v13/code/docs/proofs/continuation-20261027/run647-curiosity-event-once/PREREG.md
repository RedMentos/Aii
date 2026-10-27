# Run647 — AG5 learning-error observations exactly once per source event (2026-10-27)

Review-only child of Run646 PR647 exact head `27b27d6a2d8699c112a6eee093e2edcc7e1007cd`. Files owned: `v13/code/v13/agi/curiosity.py`, one `goal_turn` call in `v13/code/v13/agi/live.py`, new `tests/test_run647_curiosity_event_once.py`, isolated CI/proofs. Other owners' native/World-JEPA/route branches and frozen cohorts untouched.

## Defect and intended functional effect
Run644 fixed false success when FINAL lacked an actual own answer, but `goal_turn` still calls `g.curiosity.observe(region,error)` for every invocation. A retry/duplicate terminal hook on one event adds a second prediction error and visit to AG5's persistent rolling window. This distorts the learning-progress and novelty signals used for future Age-gated practice selection. The event, not the hook invocation, is the observation unit.

## Preregistered acceptance
- Same-event ERROR/ERROR, FINAL/FINAL and ERROR→FINAL each produce exactly one AG5 visit and one original error.
- Two distinct events produce two visits. A SQLite restart cannot duplicate an event.
- A source event cannot be attributed to a foreign session or different route region; malformed IDs and invalid numeric errors fail closed.
- The AG5 region-state update and unique per-event receipt are committed in one SQLite transaction; a forced post-update receipt serialization failure rolls both back and permits a clean retry.
- Existing `Curiosity.observe` for explicit unbound/synthetic data and its Age gates stay unchanged; AG4 Run646, AG5 Run644 and adjacent JEF/AG5 tests remain passing.
- Only bounded IDs and numeric errors in receipts, no private user text. No autonomous permission, semantic correctness, native/Redmi or STEP2/B3/Body-JEPA promotion.

Tests: Linux SQLite/source-only CI with preregistered RED before source, focused GREEN and adjacent regressions; retain failed attempts and original ZIPs. The parent full suite remains RED (5 FAIL, 73 ERROR) and cannot be promoted by this package.
