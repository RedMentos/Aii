# JEPA research handoff — interference-gated retention (2026-11-22)

## Source and provenance

- Julius Störk, **“Interference and Retention in Continual Learning”**, arXiv:2607.09202, submitted 10 July 2026: https://arxiv.org/abs/2607.09202
- Author implementation: https://github.com/j-stoerk/geometry-of-forgetting
- Read repository `main` at GitHub commit `31aa798` (latest commit returned by repository search at this run).
- `pyproject.toml` declares package `interference-ledger` 0.1.0, Python `>=3.9`, MIT license text, runtime dependency `numpy>=1.22`, optional `scipy>=1.8` for demos. No code was imported or copied in this patch. Before direct reuse, still inspect the exact revision's full license text and test suite; metadata alone is not a substitute for attribution/compatibility review.

## Useful technical result

The paper derives forgetting as interference energy. For a fixed feature map, the old-task loss increase is exactly `0.5 * delta.T @ Sigma_old @ delta`; for arbitrary differentiable predictors it gives a function-space identity, and a path-averaged curvature term when parameters/features drift. Its IGFA controller keeps aligned directions shareable and protects conflicting directions, using a bounded low-rank occupied-subspace summary plus held-out micro-cache gradients. It explicitly warns that train-fold constraint anchors can protect memorized noise as if it were knowledge. It also distinguishes irreducible overlap/conflict floors from avoidable interference and capacity limits.

Relevant primary-source sections: arXiv HTML §§3.2–3.3, §4, especially the discussion of held-out micro-caches and feature drift.

## V14 mapping and implementation delta

The existing JEPA path already has per-session GEM-style constraints and replay/retention gates, but its `on_demand_conflict` selector previously estimated conflict from old fit-fold rows. That is not a sufficiently independent anchor.

The current PR #2247 head `c599cb9926973b70235c38c3747e5d7ad5020cb8` makes the following partial IGFA-inspired change:

1. Conflict scoring uses the source/content-disjoint prior guard fold.
2. The `on_demand_conflict` and `on_demand_loss` projected paths now pass per-session guard-fold microbatches separately into `WorldJEPA.fit/partial_fit`; these are constraint gradients, not optimizer training rows.
3. Fit-fold rows still identify the selected sessions; final promotion holdouts remain separate and are not used to choose retry scales.
4. Metrics record the anchor fold, full guard manifest/action-ID hash, selected reference action-ID hash, constraint batch count and row count.
5. Malformed/undersized references fail closed before fit; a negative test checks parameters, optimizer-state identity and fit-step count remain unchanged.

This is **not full IGFA**: no low-rank streaming PCA basis, similarity-threshold calibration, rate–distortion rank controller, or language-model function-space gate has been implemented. The predictor/EMA learner remains a small local WorldJEPA model, not GGUF body-weight training. The new code is unverified until exact-head CI finishes.

## Test plan / acceptance

- Compare fit-fold GEM vs guard-fold GEM vs no projection on the same A→B→A seeds.
- Require source/content-disjoint guard manifests and final holdout separation.
- Report per-seed train loss, old-session guard and final holdout loss, accepted/rejected updates, parameter delta norm, checkpoint hash before/after, EMA drift, optimizer-state restart and rollback.
- Keep utility/retention gates unchanged. A rejected projection must not be relabelled as a successful update.
- Add a negative control where guard references are malformed or missing: no parameter or optimizer-state mutation.
- After the local predictor loop passes, connect a real source-bound B1/B2 receiver or human-correction stream; do not claim learned cross-organ alignment from JSON or diagnostic packet delivery.

## Limits and risks

The paper is a recent arXiv preprint; peer-reviewed status was not verified. Its clean exact result assumes frozen features/linear-on-features; deeper networks require path-averaged curvature and drift monitoring. It treats task boundaries as known in the basic formulation. Its language extension calls for a function-space gate rather than input-feature geometry. Therefore V14 should treat this as a testable retention-control hypothesis, not a proof that the current nonlinear predictor or future GGUF bodies inherit exact guarantees.

## Shared ledger action

The shared `V14_RESEARCH_LEDGER.md` remains Boss/Integrator-owned. Proposed entry: **R-056 — held-out functional interference anchors / IGFA**, linked to this handoff and PR #2247. Append only after the exact-head A-B-A result and source-pin integration are reviewed.
