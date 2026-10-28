# Run67 — action-sensitive latent-displacement inverse objective, real-file study (2026-10-28)

Owner GPT-6 scheduled continuation. Review-only child of Run64 #972 **exact software GREEN but outcome NEGATIVE** head `20d3054f783e9091446ff329f25fac99f1f09426`; original Actions `40765954706`, ZIP SHA256 `737d65358a8cc55a58b272cb1f9f493700045ffeaaa31f26f5734857eae2bce3`, CRC clean, 20/20 SHA256SUMS, 28 focused/2610 full OK, privacy CLEAN; private Library backup byte-hash verified. Run64 observed-action WorldJEPA+supervised readout heldout overall MSE 0.128708, zero-action 0.126325, persistence 0.053449, slot-local 0.015076. No action utility gain; do not refit on those seeds.

## Primary research and controlled architectural question

Delta-JEPA (Zhang et al., 2026, https://arxiv.org/abs/2606.31232) proposes inverse action decoding from **latent displacement** `z(x2)-z(x)`, rather than the frozen V13 WorldJEPA's endpoint concatenation `[z(x),z(x2)]`, to encourage action-sensitive representations. This is a new **adjacent exploratory candidate**; original `v13/world_jepa.py`, original Z12b, original Run60/63/64 source, model pins and registered cohorts remain byte-identical. No copied external code; independently implement the stated mathematical objective with analytic gradients and finite-difference tests. Do not claim paper results transfer to V13.

New fixed seeds **271, 277, 281**, per seed 4 heldout non-noop operation×slot combinations sampled via `random.Random(seed).sample(parent.NON_NOOP,4)`; exactly 240 real isolated Linux temporary-file train actions and 60 heldout test actions. Use Run60 unchanged `_rows`, Run64 unchanged factorized 5-op+6-slot two-hot encoding, train-only normalization, and the same 200 optimizer steps, 1 predictor, EMA tau, learning rate, latent/hidden sizes, anti-collapse terms and inverse loss weight as frozen WorldJEPA. **No posthoc hyperparameter selection**. Delta candidate changes only inverse-head input from 32D concatenated endpoints to 16D latent difference and corresponding encoder gradients; maintain original forward prediction/variance/covariance loss. The candidate's own training loop must be isolated from frozen WorldJEPA; no global monkeypatch or Runtime registration.

Five fixed model arms, same seed for encoder/predictor init and same data:
1. frozen original WorldJEPA observed factorized action;
2. frozen original WorldJEPA zero action;
3. delta-inverse candidate observed action;
4. delta-inverse candidate zero action;
5. delta-inverse candidate shuffled **training** action (permutation `np.random.default_rng(seed+500).permutation(240)`; heldout true action).
Each arm gets a separate train-only supervised ridge readout `[bias,predicted latent16] -> observed x2_60`, lambda 0.01 intercept unpenalized. **Primary** heldout overall MSE and target-slot MSE for all arms plus persistence and unchanged Run63 supervised baselines. **Secondary** per-seed action/row/permutation hashes, actual action success, candidate encoder noncollapse min_std/effective_rank, and analytic gradient finite differences. Original and delta inverse-head sizes and RNG consumption differ; any contrast is a candidate comparison, not isolated causal proof of the inverse objective.

Negative controls and gates: zero/shuffled action, frozen original reference, finite gradients, train-only fit, no holdout labels in training, no model weights published, no native inference, no user files, no Runtime/Store. Factorized two-hot action support is incompatible with frozen WorldJEPA confidence's single-onehot counting, so **counterfactual confidence remains unmeasured**. No outcome threshold, no gate promotion regardless of metrics. Source-only pinned Linux push/PR CI with raw evidence, SHA256SUMS, full/focused tests, privacy and frozen hashes. Preserve original negative results and RED attempts.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi UNMEASURED; whole V13 incomplete.
