# G13/WP-V5 scheduler dispatch-time burn-out budget — independent review 2026-10-27

**Owner:** `codex/automation11d-scheduler-dispatch-budget-20261027`; review-only child of LP3 independent review PR #733 exact `40556e426448c00c3c049fbf5b21d834964d00d6`. Does not touch LP3, BP2b, native owners or main.

## Concrete defect and counterexample

`EventScheduler.background_since_input()` previously counted `e['created'] >= last_accepted_user_turn` for `DISPATCHED/DONE/FAILED` background actions. A queued background event created **before** the latest accepted user turn but dispatched **after** that turn did not count against the user's burn-out budget. With budget=1, a second queued event could dispatch despite the first having consumed the post-user budget. This violates the G13/WP-V5 scheduling intent and can silently increase autonomous work.

## Fix and regression

Count the persisted `dispatched` timestamp instead of `created`, including retired history. Add `dispatched` to compact scheduler history when completing/retiring an event; the test posts two background events, records an accepted user turn between posting and dispatch, verifies the first dispatch consumes budget=1, the second stays blocked, and the count survives retirement. Historical retired entries created before this fix lack `dispatched`; fallback to `created` preserves compatibility but **cannot reconstruct unknown legacy dispatch timing**. No Age rights or user permissions were relaxed.

## Evidence at checkpoint

New regression in `tests/test_sleep_scheduler.py`, no native/model run. Isolated Actions workflow `.github/workflows/scheduler-dispatch-budget-review.yml` installs pinned software deps, executes the full unit suite, compileall, privacy scan and diff check; closed raw exits and artifact. Workflow source commit `e61a59d82afd3d037165a3d8660f47ce0edb6869`; Actions **40528070917 PASS**, exact source, **1900 tests OK (1 skipped)**, UNIT/INSTALL/COMPILE/PRIVACY/DIFF exits all 0; privacy CLEAN. Closed raw artifact `12743974557`, ZIP SHA256 `2609fa139f62ae97f30306d419f27259bafa183e4ae811523707219c41a47708`, privately backed up and byte-verified at `/V13-Checkpoints/2026-10-27/Scheduler-Dispatch-Fullsuite/scheduler-dispatch-fullsuite-40528070917.zip`. This is software-only, no native/Redmi/age proof.

## Gates / next

STEP2 UTILITY_FAIL; B3 L1 FAIL; BJ1 NO_SIGNAL; LP1/LP2 negative; `jepa_weight=0`, Age authority 0, Redmi unmeasured, whole system incomplete. Next: independently review retry/CANCELLED attempt accounting and history-cap truncation (separate PR #737 candidate); integrate only after review. No main merge or Age promotion.
