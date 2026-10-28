# Run79 prereg — grounded readout after slot-wise ensemble aggregation (2026-10-28)

Owner GPT-6 scheduled continuation. Parent Run78 draft #985 at `7f7cdc1a9c35a72267955f20e3b6480a717650c2`, CI pending at preregistration; Run77 draft #984 pending; Run76 #983 CI GREEN but raw artifact not yet independently audited. This new cohort is **isolated Linux real-file SHADOW**, not a user/runtime/native/Redmi run. No modification of any frozen prior source, seed or result.

## Predeclared source, data, arms, metrics

- Reuse exact Run60 real temporary-file generator and Run78 per-slot action encoding, without modifying either. New seeds **(431, 433, 439)**, four held-out action/slot combinations chosen with `random.Random(seed).sample(NON_NOOP,4)`; 240 training and 60 heldout rows per seed from distinct temporary directories. No historical registered cohort reused. Fit 240 steps, three predictors, slot count six, latent dimension eight.
- Fit `EnsembleMeanSlotWorldJEPA` **once per seed**, then derive two point-estimate arms from the **same fitted encoder, target and predictors**: `member0` via frozen `SlotWorldJEPA.predict(model, X, A)`, `ensemble_mean` via candidate `model.predict(X,A)`. This bypasses any different training trajectory. Both use identical train/holdout rows and target outcomes.
- Supervised readout: separate fixed ridge regression for each arm from `[1, predicted_latent_flat]` on train to 60-dimensional observed `X2`, ridge lambda **0.01**, intercept unpenalized. No heldout outcome is available to the fit. Holdout output metric is **target-slot observed-feature MSE** (primary) and all-slot MSE (secondary). Compare `member0`, `ensemble_mean`, `ensemble_mean_shuffled_test_action` (same mean-trained readout, test actions permuted with seed+7000), and Run60 `slot_local_ridge` baseline trained on same rows.
- Exploratory positive criterion, **not a gate**: mean target-slot MSE at least 5% below member0, nonnegative improvement each seed, below shuffled action and below slot-local ridge baseline. Report every component even if negative. Three seeds are insufficient for broad statistical/generalization claims.
- Negative-control integrity: action/target arrays source-hashed, train/test heldout action disjointness checked, deterministic permutation hash, no target leakage into readout; NaN/Inf reject, exact source blobs pin in CI. All original negative outcomes preserved.
- Source-bound CI runs focused tests, real-file experiment, full software suite, privacy and closed raw hashes. No external tools, downloads of model weights, private data, runtime changes or age rights.

## Interpretation

This is a **supervised grounded readout** experiment. Even positive performance does not establish JEPA-only action understanding, causal world modeling, cross-organ B2↔World-JEPA utility, native or Redmi validity, or whole-system completion. Retain Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0 and all original acceptance gates. Next meaningful step after verified results is compare against heldout source-disjoint real actions and fixed non-JEPA readouts, not tune this frozen cohort posthoc.
