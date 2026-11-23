# Run64 — factorized-action World-JEPA trained on real isolated file transitions (2026-10-28)

Owner GPT-6 scheduled continuation. **Conditional** review-only child of Run63 #971 exact head `57ff0d96b2bb095a06779697543a099aa97a176e`; Run63 exact-head software CI and independent raw audit must be GREEN before Run64 results may be treated as verified. Parent Run60 #968 independently GREEN exact push Actions `40762607763`, artifact SHA256 `ef76f76d65627776d906e141571e0cfafe595ec65f76173dee14727ed9957ca7`. No production merge, no edits to original WorldJEPA, Z12b, Run60/63, original registered cohorts, models or Runtime/Store.

## Question

Can the **existing** NumPy WorldJEPA learn an action-conditioned latent transition on actual isolated Linux filesystem changes, then support a train-only supervised latent→observed-outcome readout for **unseen operation×slot combinations**, beyond persistence, global factorized delta ridge and slot-local ridge? This is a new exploratory cohort, not a rerun of original WP-Z12b failed gates. The original Z12b heldout action retrieval 27% and W1 77% remain FAIL.

## Fixed protocol before source/metrics

Use unchanged Run60 `_rows` to execute real private temporary-file operations, and Run63 factorized features to encode actions. Three **fresh** seeds `251,257,263`; per seed 4 heldout non-noop op×slot combos via `random.Random(seed).sample(parent.NON_NOOP,4)`, 240 train and 60 heldout transitions. Train and heldout state walks separate. No user files, Runtime/Store, native weights, network or external actions. Reuse frozen `v13.world_jepa.WorldJEPA` exactly, no architecture/optimizer changes: `steps=200`, `ensemble=1`, `log_every=200`, model seed identical to cohort seed, NumPy deterministic CPU single-thread. Factorized 11D action = 5D operation onehot + 6D slot onehot; each non-noop action has exactly two ones. Its current confidence method expects one-hot, so **confidence and counterfactual support remain UNMEASURED/NOT_PROMOTED**, not claimed from this study.

Three fixed arms:
1. **observed factorized action**: train/infer with correct factorized actions;
2. **zero action**: train/infer with all-zero 11D action vectors;
3. **shuffled training action**: permute train action rows with `np.random.default_rng(seed+500).permutation(240)`, fit and train readout on the same permuted train actions; infer with correct heldout actions. Preserve permutation SHA256 and train/test row digests.

For each arm, fit WorldJEPA on train (X,A,X2) only. Fit **separate supervised ridge** decoder `[bias, predicted_train_latent16] -> observed_train_x2_60` with fixed lambda 0.01 and unpenalized intercept, no holdout target or state leakage. Predict heldout latent from (X_heldout, A_heldout) then decode to heldout next-state features. Primary: per-seed/aggregate **heldout observed outcome overall MSE** for the three arms and unchanged Run63 supervised comparators (persistence, original global exact-action ridge, shared slot-local, factorized global delta ridge, slot-aware local). Secondary: target-slot MSE, training/heldout digests, action-permutation SHA256, actual action success, frozen source hashes, model steps. No threshold, no metric-based retry/selection, no publication of model weights. A positive observed-vs-shuffled contrast is **not** causal or JEPA-only utility: readout is supervised, baselines have different capacities, no real user action or Redmi.

Source-only pinned Linux CI on push/PR: exact frozen hashes, focused/full suite, real temporary-file evidence, metrics raw JSON, privacy/diff, closed ZIP SHA256SUMS. Preserve all REDs and original negative gates. If numerical divergence or source prerequisite RED occurs, retain raw and fix only on a new child/revision, never alter prereg seeds or frozen code.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; phone UNMEASURED; whole V13 incomplete.
