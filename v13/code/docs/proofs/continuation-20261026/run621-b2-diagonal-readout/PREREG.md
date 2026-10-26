# Run621 — fixed B2-only learned diagonal metric readout (exploratory, retrospective)

2026-10-26 UTC. Review-only child of Run620 PR615 at exact head `ac25ca8728c3a6b4cb9182ef4f9139438579b9c0`. Owner new `scripts/run621_b2_diagonal_readout.py`, new tests/workflow/proof only. No edits to active native Run618, registered cohorts, native runner, model weights or runtime authority.

**This is exploratory/posthoc** to already-inspected original Run614 frozen Linux-native B2 states; not a new prospective holdout and not Body-JEPA. Original `RUN614_STATES.npz` SHA256 `cb535df87749c0cf5d698d26268e6b03f3d6f57690b95434aebc6c875a3ea189`, original report SHA256 `42ac6d22ef6c9cc59622572f233b2e7b83094af7a9fdd227cfe2fff15e0666e4`, model Qwen3.5 pinned SHA256 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`. Use existing `run615_crosscohort_shadow.load(folder,'614')` for original source/authority/shape/hash verification. 60 train prompts = 30 A/B pairs, 20 heldout prompts = 10 unseen facts across literature/geography. No train/test fact overlap.

Frozen method before this new fit:
1. Unit-normalize B2 states. Fit positive diagonal weights using 30 paired train A/B states: `signal_j = mean(A_j*B_j) - mean(A_j*roll(B,1)_j)`. Standardize signal across 1024 dimensions (subtract mean, divide std+1e-12), `w=clip(exp(0.4*z),0.5,2.0)`, then divide by mean. No gradient, no model weight update; train-only statistical metric readout.
2. Test retrieval by weighted cosine `unit(X*sqrt(w))` on the 20 heldout states, excluding self, fixed original-index tie break. Baselines: unweighted raw cosine and train-mean-centered cosine (train mean only). Metrics top1 and MRR.
3. Fixed seed 2026102621; 200 shuffled train-B pairings as controls with the identical fit and heldout evaluation. Empirical p=(1+controls with top1 >= learned top1)/(201). No hyperparameter search, test-set tuning, automatic activation or receiver injection.
4. Scoped candidate criterion: learned heldout top1 >= best baseline top1 + .10, empirical p <= .05, finite positive weights and original negative gates unchanged. Otherwise `NO_B2_READOUT_GAIN`. Any positive remains exploratory due posthoc source and no prospective replication.
5. Test wrong source SHA/shape/nonfinite/refusal, zero weight updates, and reproducibility; retain raw failed attempts, weights/report hashes, baseline and shuffled controls. Source-only CI must not run native model inference.

No claims of J(E)PA, local plasticity, sparse body training, full V13 or Redmi. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi UNMEASURED, V13 INCOMPLETE.
