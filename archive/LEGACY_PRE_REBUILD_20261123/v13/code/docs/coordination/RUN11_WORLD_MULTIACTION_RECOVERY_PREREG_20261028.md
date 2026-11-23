# Run11 F4 WorldState multi-action crash recovery — preregistration (2026-10-28)

**Owner:** GPT-6 independent review-only child of PR #861, exact parent `1f8519716444e2c5121a6c3be9adc0eb7bc87346`. New branch `assistant/v13-run11-world-multiaction-recovery-20261028`. No other owner files, Canon, models, seeds, registered cohorts or production/main changes. PR #861 timing candidate remains unmerged.

## Source-level counterexample, before code

`Store.start_action(event_id, ...)` permits multiple distinct action IDs for one authoritative event. `WorldState.observe(aid)` binds its `PredictionOutcome` to the action ID, but `WorldState.recover()` currently uses `NOT EXISTS` at **event level**. If action A of event E has a receipt while completed action B of the same event lacks one after a crash, recovery skips B permanently. `WorldState._refresh()` reports `observed_action_count` as `COUNT(DISTINCT p.event_id)`, which undercounts multiple action receipts in one event. This is a **software/source-level durability defect**, not evidence it occurred on a Redmi.

## Narrow candidate / test plan

- Test with real temporary Runtime/Store: two distinct FINAL actions on the same event, observe only one, close/restart, require both `PredictionOutcome` receipts and two distinct action IDs in `WORLD_STATE.recent`, count 2; second restart idempotent. Repeat with reverse observed/unobserved order.
- Test direct two-observation same-event count 2, and single-action unchanged.
- Change only `WorldState.recover` receipt existence to correlate by `action_id` as well as `event_id`, and `_refresh` count to distinct receipt action IDs. Preserve existing receipt identity checks, source/corollary checks, raw outcomes, no new authority or training. Do not silently reinterpret prior native rows.
- Run source-pinned Linux software focused and full suite, compile, privacy, diff, archive raw stage exits and hashes. First reproduce RED before implementation if practical. No heavy native/model/Redmi runs.

**Acceptance:** same-event two-action recovery and count, restart idempotence, existing `test_world_state` and `test_world_timing_invalid_sample_20261028` still green. No STEP2/B3/Body-JEPA/LP3/jepa_weight/Age promotion. All remain STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY, Redmi not measured, V13 incomplete.

**Persistence:** commit this prereg before test/code. If CI is blocked, retain exact source/test blobs and a truthful scoped BUILD_STATE; do not claim a full pass without closed evidence.
