# JEPA & Memory — run 19: temporal source-forget cursor domain fix

**Date:** 2026-11-24  
**PR:** [#2454](https://github.com/RedMentos/Aii/pull/2454)  
**Branch:** `jepa-memory/v14-temporal-boss-2443-rebase-20261123-run14`

## Finding

The temporal learner's persistent scan cursor is an Action-table cursor: `verify_committed_temporal_page()` selects `a.rowid AS scan_seq` and persists that value as `scan_cursor`. In `_record_references_source()`, the historical source-forget scan compared that cursor against `e.rowid` instead:

```sql
WHERE e.rowid<=?
```

The Events and Actions tables have independent rowid sequences. If earlier events have no Action rows, an older committed Action can have `a.rowid <= scan_cursor` while its Event has `e.rowid > scan_cursor`. The old predicate silently omitted that action from the history scan. If its only reference to a Memory/observer/Enlightened source was in C4 FocalCycle/FocalItem provenance and the action had already rolled out of the bounded experience_rows window, source-forget could fail to notice the dependency.

## Implementation

- Code commit: `540a5881a17f28a472d0c52f5097634bd19308b2`
- File: `v13/code/v13/world_jepa_temporal.py`
- Change: use `WHERE a.rowid<=?`, matching the exact cursor domain emitted by the T8 verifier.
- Regression commit: `9747fcf047ae9249d56681c65fd44463316597d2`
- File: `v13/code/tests/test_v14_world_jepa_temporal_runtime.py`
- Test: `test_temporal_source_forget_scan_cursor_uses_action_rowid_not_event_rowid`
- Test setup inserts twelve actionless Events before two C4-only context actions. It asserts that the first action's C4 source is found despite `event.rowid > scan_cursor`, and that the second action's source is not included because its `action.rowid > scan_cursor`.

This preserves the existing fail-closed provenance checks; it does not weaken source-forget, expand the source cap, or claim gradient unlearning.

## Verification

| Check | Environment | Result |
| --- | --- | --- |
| Added regression function AST parse | LOCAL_LINUX, CPython 3.13.5 | PASS |
| Isolated SQLite reproduction of old vs corrected rowid predicate | LOCAL_LINUX, SQLite | PASS |
| Full Aii compile / temporal pytest / source-forget suite | LOCAL_LINUX | BLOCKED / NOT_RUN: no repository checkout; GitHub DNS unavailable |
| Exact pushed Actions run `45290566774` | CI | STARTUP_FAILURE; 0 jobs, therefore no project test result |
| Redmi native behavior | TERMUX / REDMI | REDMI_UNVERIFIED; no phone test performed |

The local SQLite reproduction established: with one action at rowid 1 whose event is rowid 13, the old event-rowid predicate returns no row while the corrected action-rowid predicate returns the action. A later action at rowid 2 is excluded when the persisted cursor is 1.

## Persistent coordination writes

- `v14/V14_WORK_BOARD.json`: commit `bab5a48054bf9f9265ca085005341f5091f2399b`; updated JEPA tickets V14-004 and V14-011 plus the related Memory ticket V14-012 with exact evidence and next action.
- `v14/V14_USER_NEXT_ACTION.md`: commit `0a6f2f1bed2eb42b66fd017caef851b910756ecd`; prepended the run-19 handoff, explicit device boundary and no-action-required state.
- This handoff is the detailed record for the same checkpoint.

## PR / integration boundary

- Code/test checkpoint: `9747fcf047ae9249d56681c65fd44463316597d2`.
- PR #2454 remains DRAFT / NOT_RELEASED / mergeable=false.
- PR base remains Boss #2443 at `6e9bad8daa9ad9ec97947639600f6c7cdbffb6d4`; current Boss branch head readback is `cdf6b64067ac426ba32194100d3764f6e74c105f`. The compare is diverged, 127 ahead / 47 behind. Do not force-push or blindly rebase.
- Exact Actions run `45290566774` is a runner/workflow startup failure with zero jobs. Boss combined exact-head CI has the same startup-failure boundary. Rebase only after the exact parent matrix is freshly green, then three-way resolve shared Memory/Sleep/bodyview changes and recompute nested pins.

## User-visible / product effect

No release or deployment changed. The latest authenticated phone baseline remains release `8d93236c753f0194224c19edc7411d8d7082b1d6`, auto-updater enabled and Runtime/Dashboard UP_TO_DATE, but AI state `STOPPED_BY_USER`, autostart false, model process STOPPED. The new commits are not installed.

The code candidate continues to represent experimental Store-backed T8 temporal prediction, EMA/checkpoint/replay/rollback and numeric B1/B2 float receiver adapters in SHADOW. This fix does not establish native GGUF/body-weight changes, trained B1↔B2 latent transfer, production learning promotion, Android UI operation, or Redmi learning.

## Next step

After Boss #2443 has a freshly green exact combined matrix:

1. Rebase #2454 onto that exact parent without force-push.
2. Resolve the shared source-lifecycle, Memory, SleepRuntime and bodyview files by three-way review; recompute every immutable nested pin.
3. Run Python 3.13 and 3.14 temporal, postcommit/source-forget, optimizer-resume, restart, positive/missing/corrupt rollback, staged and integrated suites on the exact rebased head.
4. Continue the source-disjoint A→B→A dynamics/outcome-shift experiment with replay-on/off, matched optimizer steps and frozen-baseline negative controls.
5. Keep B1/B2 adapters SHADOW and distinguish source deletion from concept/dynamics drift.

**User action required: NONE.** No device command, restart, update request, model/weight swap, permission change or data mutation.
