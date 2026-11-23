# AG6 staged-source revocation before trainer.fit — preregistration (2026-10-29)

Review-only child of PR #1124 exact source `edcbb279dc1503ee0c7f7f556a0d24714eef4972`; owner only this child branch, `v13/code/v13/agi/weights.py`, `v13/code/tests/test_ag6_staged_source_revocation_20261029.py`, scoped CI and this prereg. No changes to source/model/seed cohorts, frozen runs, AG6 activation or Age rights.

## Defect hypothesis

`WeightConsolidation.stage` binds source refs, but `train(bid)` currently rechecks data mix and anchor policy only. Between staging and `trainer.fit`, the human can revoke a source (`sources.deleted=1`), yet the staged batch retains its old `source_ref` and still reaches the trainer. That violates the immutable/revocable provenance contract; a source revocation is not a historical quality rating or approval to train.

## Predeclared real-Store tests

- Stage a real human memory with `require_replay_pass=False`, then revoke the exact staged `source_ref.source_id`; a counting no-model trainer must **not** be called, and batch becomes `SOURCE_INVALID` with retained failed attempt. Original expected RED (trainer called).
- Stage two distinct human memories, revoke only one; reject the **whole** batch atomically, never train on the remaining subset under the old dataset hash. Original expected RED.
- Stage a source-valid memory and train with the same counting trainer: training call still occurs; expected `NO_TRAINER` if fake returns no artifact.
- A new batch after revocation must not silently deduplicate the failed one; original immutable batch remains visible.
- No AG6 activation, native model, Redmi or learning-utility claim.

## Narrow fix and proof

Before `trainer.fit`, validate every staged item `source_ref` via `Store.read_source` and reject missing, malformed or revoked references. Mark `SOURCE_INVALID` durably, do not invoke fit, and include it among non-deduplicating terminal failures. Do not rewrite batch source data or reclassify existing failures. This only covers direct staged refs; answer dependency revalidation after staging, other mutable memory metadata and training-time races remain separate open risks. Preregister and run test-only RED first, then candidate focused/full software and independent raw audit.

Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, AG6 unapproved, V13 incomplete.
