# World-JEPA collapsed latent effective-rank integrity — prereg (2026-10-29)

Review-only child of PR #1128 exact parent `185c19652f146f44fea2e996f5f5ad4f0058c21a`. Separate organ, own `v13/code/v13/world_jepa.py` **only on this child**, `v13/code/tests/test_world_jepa_collapse_rank_20261029.py`, own CI and prereg. Do not edit parent, native source/seed/model cohorts, or promote any JEPA/STEP2/B3 gate.

## Independent defect hypothesis

`WorldJEPA.collapse_stats` computes `p=ev/ev.sum()` without handling zero covariance. A fitted zero-step or genuinely collapsed target encoder can yield all zero eigenvalues; NumPy emits invalid divide, `p[p>0]` is empty, and `exp(-sum(empty))` silently returns **effective_rank=1** rather than an explicit collapsed/no-evidence status. Nonfinite or singleton probe inputs are not explicitly rejected. This is a diagnostic integrity bug: it must never turn degenerate latents into a positive effective-rank measurement.

## Original RED and negative controls

1. Real NumPy WorldJEPA fitted with 4 zero observations, valid one-hot actions and `steps=0` (synthetic software only), then `collapse_stats` must return finite `effective_rank=0`, `min_std=0`, `collapsed=True`; original expected RED (effective_rank=1).
2. A noncollapsed two-dimensional probe must retain finite positive effective rank and `collapsed=False`; no change to trained weights or prediction.
3. Invalid probe shape, singleton probe and nonfinite values must fail closed with ValueError rather than silently yielding NaN or a misleading rank.
4. Run inherited World-JEPA fit, confidence, zero-step, checkpoint and atomicity controls; source-only CI, privacy/diff and raw SHA256/CRC. Full suite separately, preserving inherited frozen-source errors.

## Candidate / limits

Guard finite 2D probe inputs with at least 2 rows and the fitted feature width; calculate finite target latents; if covariance trace is zero/nonpositive return a documented zero-evidence collapsed result, otherwise stable entropy effective rank. Do not infer learned utility from rank, do not alter fit/weights/EMA, data, action labels, model or seed hashes. No native/Redmi; Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, World-JEPA unpromoted, V13 incomplete.
