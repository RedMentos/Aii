# Run301 — WorldModel event-group-disjoint heldout: RED → GREEN (software)

UTC 2026-10-25. Owner GPT-6; PR #300, branch `codex/world-event-holdout-run301-20261025`, base Run300 head `5f4e6f7d0735a97aca1f1d3165666307ef5200e3`.

## Implemented
The old WorldModel deterministic 1-in-4 **row** holdout could split two actions from the same USER_TEXT event across training and validation. `transitions()` now preserves each observed `event_id`; `_split(n, groups)` assigns whole event groups together. New fits report event-group train/heldout counts and a disjointness flag. If no independent heldout group exists (24 actions from one event), `fit()` returns `INSUFFICIENT_INDEPENDENT_GROUPS` without persisting fabricated heldout metrics. With one event per action, the original deterministic split is exactly unchanged; legacy synthetic fixtures fall back to action IDs. Existing persisted models, revision, source/seed/model hashes and all negative gates remain untouched.

## Actual closed evidence
- RED prereg/test head `6b63d80cb4363b0615826d2a90dc1fd60d5f9092`; Actions `40203788386`, artifact `12602742081`: **52 tests, 3 errors** (missing grouped split API and event_id), official privacy scan CLEAN. Preserved.
- GREEN source head `b9dcf2913739b17bd3851b0dc0bec3a74e1e084b`; source blob `cb899b099c5c7f5db626b4cf4cf6cc4877a8f6cc`; Actions `40203854229`, artifact `12602509155`: **52 tests OK**, official privacy scan CLEAN.
- New tests run actual production Runtime/Store SQLite with synthetic action durations: 12 real source-grounded events × 2 actions, chronological ActionSelection bindings, valid source bindings after restart; 1 event × 24 actions fails closed; unique-event legacy split is identical. Older WorldModel, Run298 terminal outcomes, source integrity and chronology regressions included.

## Limits and other observed failures
This is **event-level heldout independence**, not proof of causal generalization or cross-source semantic de-duplication. No native model, Redmi or measured utility; STEP2/B3/Body-JEPA/jepa_weight unchanged. A separate full-suite run on the Run298 checkpoint (`40202886433`, artifact `12602378950`) FAILED: 2833 tests, 2 failures, 36 errors, 14 skipped, primarily frozen native candidate source mismatch and resident cancellation cleanup. Preserved in `../fullsuite-run298-failure/OBSERVED.md`; do not claim whole-suite GREEN or silently alter hashes. Broader Run301 workflows may still be running.

## Next
Independent review grouping across repeated identical sources and data ordering, and check Run301 focused CI. Then implement another distinct Canon package on a new branch. Do not overwrite active Run297 native Context OS owner or frozen Runtime/Store.
