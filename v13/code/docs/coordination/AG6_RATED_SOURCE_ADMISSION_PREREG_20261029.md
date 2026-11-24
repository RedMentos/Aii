# AG6 explicit-rated answer source admission — preregistration (2026-10-29)

Review-only child of PR #1119 exact parent `33139aeaab7732663e731149413a8eb766ee7d72`; parent itself child of PR #1117. Owner: this child branch only, `v13/code/v13/agi/weights.py`, one new focused regression, scoped workflows, this prereg and handoff. No frozen source/model/seed cohorts changed.

## Independent defect hypothesis

`WeightConsolidation.rated_candidates` reads a rated user/assistant pair from mutable `messages` and only attaches `events.source_id`; it never checks the event's immutable SourceRef, source deletion, exact user text, source hash, or same-session pair. A deleted or tampered user source can therefore become a weight-training candidate from a historical explicit rating. A human quality rating is **not** fact authority or permission to resurrect a revoked source.

## Predeclared tests

- Real Store event, FINAL assistant fixture, `record_rating(..., 9, 'EXPLICIT_NOTE')`. Valid source returns exactly one rated candidate with exact source binding, marked `HUMAN_QUALITY_LABEL_NOT_FACT`.
- Mark original event source `deleted=1` after rating; `rated_candidates` must exclude it (original RED).
- Modify retained user message text while keeping original source bytes; `rated_candidates` must exclude it (original RED).
- Cross-session assistant row for the same event must not create a rated candidate (original RED).
- Repair only this admission path using existing read-only `ContextOS.source(event_id,session)` exact SourceRef restoration, message-source equality, and same-session FINAL pair; no model calls or training.
- Run original test-only RED, candidate focused/full software, compileall, privacy/diff checks. Preserve inherited full-suite REDs separately and do not claim native/Redmi or gate promotion.

No changes to human rating semantics, origin/mix quotas, adapter activation, or training authority. Negative gates unchanged: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; AG6 unapproved; V13 incomplete.
