# AG6 rated-answer live metadata and rating recheck — prereg (2026-10-29)

Review-only child of PR #1127 exact parent `784e5ea92bc55107482400cb39d9d6a95b6afc1b`, which itself is a review-only child of #1126. Parent branches, original frozen cohorts, model/source/seed hashes and RED/GREEN raw remain untouched. Child ownership: `v13/code/v13/agi/weights.py` only on this branch, new `v13/code/tests/test_ag6_rated_metadata_lifecycle_20261029.py`, child CI and this prereg. No production merge.

## Independent remaining gap

PR #1127 preserves and rechecks *declared supporting source snapshots*, but a human explicit 9/10 rating or the rated assistant FINAL/metadata can change **after stage**. The current fit/approval checks do not reread the current explicit rating, unique FINAL answer or declared dependency metadata. An old rating may be replaced with 2/10, a FINAL target may be mutated, or `context_source_refs` removed while the stale staged candidate remains eligible.

## Predeclared original RED controls

1. Real Store: stage 9 human memories + one explicitly rated answer (self-share 10%); downgrade that answer to explicit 2/10 before fit. No trainer call; SOURCE_INVALID.
2. Stage then mutate FINAL answer text before fit; no trainer call; SOURCE_INVALID.
3. Stage then remove answer's `context_source_refs` from persisted FINAL metadata; no trainer call; SOURCE_INVALID.
4. Stage, train and gate with authored FakeLora, then downgrade explicit rating before manual approval. Refuse without changing PENDING_USER, request, consolidated IDs or adapter.
5. Unchanged rated answer + 9 human memories still train and approve. Run all inherited AG6 controls, compile, privacy/diff and full suite separately. Original RED and corrected GREEN must be saved independently.

## Candidate and limits

For rated items, compare the persisted `event_id`, `target`, explicit rating score and declared supporting dependency snapshot against the *current* real Store FINAL and rating immediately before fit and again inside the approval Store.mutex transaction. Require exactly one FINAL for the event/session and a current explicit score at least 8, equal to the staged score. Treat malformed metadata or mismatched dependencies as SOURCE_INVALID/approval refusal; do not change underlying ratings or target. This is not a guarantee against arbitrary simultaneous cross-process SQLite rewrites, missing historic source declarations, post-approval revocation or native learned utility. All negative gates unchanged: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, AG6 unapproved, Redmi unmeasured, V13 incomplete.
