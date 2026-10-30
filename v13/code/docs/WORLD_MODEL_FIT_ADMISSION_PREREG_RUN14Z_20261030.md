# Run14Z — T8 fit provenance and real SQLite source admission (2026-10-30)

Parent Run14Y PR #1340 exact `9a69c3a6799091f2aaea34cd40f620614d8d3f51`. Owner GPT-6. Scope `v13/code/v13/world_model.py`, new `tests/test_world_model_fit_admission_run14z.py`, CI/checkpoint. No model download, no heavy inference, no Canon/registered cohort rewrite.

## Observed cross-version risk

Run14Y rejects ambiguous JSON in **new** World T8 observations. However `world_model.load()` currently accepts every persisted `t8-world-model-v3` fit, including an old fit trained from duplicate-key source rows before Run14Y. An explicit `counterfactual(st=...)` can also use such a legacy state. These are not source-proven models. A cache admission marker must be required before any fitted state can supply counterfactual confidence. The existing `REVISION` and fit formulas are not changed; existing fit rows are not silently migrated or deleted.

## Frozen test-first contract

1. A new `fit()` state (including TOO_FEW_TRANSITIONS) carries `source_admission='T8_JSON_UNIQUE_KEYS_V1'`, and restart load accepts a newly fitted state.
2. An otherwise valid legacy fitted state lacking that marker, or with an unknown marker, is refused by `load()` and by direct `counterfactual(..., st=legacy)`; return no model/confidence, never reuse unproven weights.
3. Real SQLite action, C5 packet and action outcome with unique JSON are accepted. Mutating expected/outcome/selection to duplicate-key bytes excludes that transition; restore exact original bytes and acceptance returns; restart does not silently turn invalid evidence into valid. No raw mutation by the model.
4. Historical numeric optional-latent test, World F4 receipts, stage-binding, selection-binding, T8 held-out and Run14Y duplicate-key tests all remain passing. Original RED, candidate GREEN and unfiltered historical RED separately preserved.
5. No claim of native model utility, Redmi, JEPA gain or Age promotion. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 incomplete.

If compatibility regression appears, preserve it and isolate the fix; do not change historical tests or old fitted state bytes.
