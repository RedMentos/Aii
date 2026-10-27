# WP-S7 Sleep digest and TTT candidate lineage gate — prereg 2026-10-27

Independent review branch based on PR #659 `949afa149460478661d54cfa944e321d195a7b03`; file owner: `v13/code/v13/sleep_offline.py` and new/extended sleep tests only. No AG5/World merge.

## Concrete discovered defect

`sleep_offline.context_items()` checks the event source deletion flag before showing an old digest in live context. However `sleep_offline.view()` displays the same stored digest without that lineage check, and `sleep_offline.stage_ttt()` uses deleted digest entries as both training target candidates and prior-context text. If a source is marked deleted **after** digest creation, a later `:sleep digest` or TTT export can expose the deleted text despite the live context filter. TTT staging is not weight training, but exporting deleted data violates the Canon's source/retention boundary.

## Frozen expected behavior

1. Reproduce the leak with a real Runtime/SQLite source deletion (not mocking the whole data path). Test that deleted target events never become TTT candidates; deleted earlier events never enter candidate context. `:sleep digest` must hide them as `context_items` already does.
2. Extract one fail-closed live-source check for stored digest entries: source exists and not deleted; linked assistant message exists, belongs to event and is FINAL. Use it consistently for view, context_items and staging. Missing/broken lineage excludes content.
3. TTT rows must carry exact `context_event_ids` and `target_message_id` and remain `CANDIDATE_NOT_TRAINED`, authority 0. Add a read-only validator for persisted candidate files that checks live lineage again immediately before any downstream training. Legacy rows without lineage fields fail closed; no automatic training.
4. Re-check every staged row before the final file write. If deletion happens after export, validator must reject stale files. No silent deletion of original audit history or bypass of user retention rules.
5. Preserve existing Sleep/S7 behavior for valid sources; run focused real SQLite tests, full software suite if possible, compile/privacy scan, closed raw evidence and independent review.

No new Age/approval rights, weight updates, model communications, native/Redmi proof, STEP2/B3/Body-JEPA promotion. Stale digest state may still require a separate storage-purge/migration package; this package prevents reuse/exposure through the known read/staging surfaces and records the residual risk.
