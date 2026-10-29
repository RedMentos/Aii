# AG6 rated-answer dependency admission — preregistered counterexample (2026-10-29)

Review-only child of PR #1120 source `bfcb3861ee023a893b3b2a4a5f4df588f64b730a`. Owner: this child branch only, `v13/code/v13/agi/weights.py`, `v13/code/tests/test_ag6_rated_answer_dependencies_20261029.py`, scoped CI and this prereg. Parent branch is not to be edited. Source/model/seed cohorts and gates unchanged.

## Independent review defect

PR #1120 correctly validates the rated **user input** against immutable SourceRef, but `rated_candidates()` still selects the assistant `text` from `messages` without checking the assistant's `metadata.context_source_refs`. `history.native_history` already refuses an assistant whose referenced source was deleted or invalid. An explicit human quality rating must not override later source revocation: an answer dependent on a now-revoked source is not a permissible AG6 training example. Also, multiple FINAL assistant rows for the same event create ambiguous rated targets, while the candidate currently selects the last row.

## Predeclared test cases

1. Source-valid event and same-session FINAL assistant with `context_source_refs=[event.source_ref, dependency]`, explicit score 9: candidate admitted before revocation.
2. Delete `dependency` from `sources` after rating: candidate must be excluded, with rating and original chat unchanged (original expected RED).
3. Assistant `context_source_refs` containing malformed/dangling ref: candidate excluded (original expected RED).
4. Duplicate same-session FINAL assistant for rated event: candidate excluded (original expected RED).
5. Unrelated valid rated event stays eligible; no global refusal due to one revoked dependency.
6. Original PR #1120 four rated-source admission regressions still pass.

## Narrow candidate behavior

Read assistant metadata, require exactly one same-session FINAL assistant row for rated event, and validate each declared `context_source_refs` entry via `Store.read_source` (including type and bounded count). Fail closed on malformed declared dependency metadata. Do not import unmerged ContextOS code, alter training/age/approval gates, rewrite original ratings, or change source/model/seed cohorts. Legacy answers with no declared context refs remain governed by the existing parent policy; their provenance sufficiency is a separate open question and is NOT claimed solved here. If an active fixed-answer rule is revoked, future work must also enforce typed-rule membership in this candidate path.

## Proof protocol

Commit prereg before test, then original test-only RED and preserve raw. Implement narrow fix, run focused/full software in pinned Actions with closed raw, ZIP SHA/CRC/internal SHA256SUMS and private backup. Original inherited run34/run37 `native_source_or_catalog_changed` failures must remain RED, never rewrite pinned cohorts. No native/Redmi, no gate promotion.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; AG6 unapproved; V13 incomplete.
