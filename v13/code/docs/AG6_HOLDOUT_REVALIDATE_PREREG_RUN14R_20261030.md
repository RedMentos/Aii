# Run14R — AG6 training/approval holdout revalidation (preregistered)

Date 2026-10-30 UTC. Owner GPT-6 scheduled continuation. Review-only child of Run14Q PR #1333, exact parent `b83e19e07c1a662b8b54e98cc99649f95bf48a2e`. Own only `v13/code/v13/agi/weights.py`, `v13/code/tests/test_ag6_holdout_revalidate_run14r.py` and Run14R-scoped docs/workflows. No merge, no age change, no model training or paid provisioning.

## Concrete canonical learning-path gap

`WeightConsolidation.stage` excludes AG12 holdouts only if optional `generality` was passed; direct AG6 use with `generality=None` bypasses the check. `train` and both `approve` transactions revalidate source refs, but not registered historical EN/DE AG12 holdout digests. A suite registered or rotated after staging may make an immutable batch inadmissible while still allowing fit/approval. This threatens generalization evidence if later training consumes unseen tasks.

## Frozen tests and acceptance

1. Real SQLite/Runtime, human fact memory with registered EN unseen prompt. Direct AG6 `WeightConsolidation(...,generality=None)` must reject at stage, not create a batch.
2. Stage a human fact prompt that is not an existing EN seed13 holdout. Register EN seed17 so that exact prompt becomes unseen. AG6 `train` must veto before the counting fake trainer is invoked; durable batch becomes `SOURCE_INVALID` (existing terminal invalid-data state) with a holdout-specific reason. No candidate or request.
3. Repeat (2) for German seed17 while English suite remains active. Historical EN/DE registered unions are both protected.
4. Stage and run a fake measured gate to `PENDING_USER`, then rotate/register the suite. `approve` must reject without activation, preserving the pending request and zero consolidated IDs. Both approval transactions must check current holdouts while holding SQLite write lock.
5. Ordinary human correction without registered holdout remains stageable/trainable (synthetic trainer only). Absent AG12 StateBoxes are not auto-created by AG6. Existing AG6 source-lineage, rated-answer, data-mix, AG12 Run14P/Q and AG9 tests must remain green.

Use Run14Q `registered_holdout_digests(store)` read-only union; compare `digest(normalize(text))` for each staged `prompt`, `target` and `teacher_prompt`. A damaged/unknown-history registered state must veto stage, fit and approval; no silent fallback. Keep original negative gates: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi unmeasured, V13 incomplete. Tests run with explicit SHADOW_UPDATE *test config only*, not actual production learning. Do not claim native/model/AGI success.

Frozen parent blobs: Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7`; AG6 weights `eab5f8440bbfe3a584ac2dfb9fedc1401ae4e7a7`; AG12 union `84ca3580c37a00701286d0d9b00d535ee8c3153f`; Sleep `622f3c202c70464c7426e590979428e41f6e50a6`.
