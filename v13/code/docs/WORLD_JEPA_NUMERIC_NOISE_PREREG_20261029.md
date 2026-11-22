# WP-Z12b / World-JEPA collapse diagnostic: floating-point noise control — preregistration

Date: 2026-10-29 UTC. Review-only child of PR #1129 at exact parent `ec7f4e42c1af8bc081e839a03588661678eb0a12`. No production merge; no changes to frozen model/source/seed/cohort registrations, weights, action authority or Age rights.

## Independent observed problem

Parent exact-head focused Actions 40926454088 (ZIP artifact 12919314653) ran 26 tests and failed `test_constant_nonzero_latents_have_zero_rank_despite_roundoff` at an `np.array_equal` assertion. That assertion is not a valid cross-BLAS contract: identical observation rows can produce target latents differing at floating-point rounding scale. The parent source checks only `np.ptp(zt)==0` and may therefore report positive effective rank for a mathematically constant latent. Preserve the parent failure and do not call it a source failure until a deterministic counterexample demonstrates the latter.

## Registered synthetic controls (NumPy software only)

1. Repeated, finite, identical input rows (nonzero latent) must report `effective_rank=0`, `collapsed=True`, without requiring bitwise equality of GEMM outputs.
2. Deterministically injected finite target-latent roundoff of at most 2 ULP around a nonzero constant vector must not create positive rank; no reliance on BLAS implementation.
3. A genuinely varying target-latent coordinate at `1e-6` scale must not be classified as constant, and all diagnostics must remain finite.
4. Zero-variance, malformed, nonfinite, singleton and all existing World-JEPA controls must remain unchanged; source refit and confidence semantics untouched.
5. Original parent failing test may be corrected to assert numerical closeness rather than bitwise identity, but its rank-zero requirement remains. Preserve all original RED/failed runs.

## Procedure and acceptance

Commit this prereg first, then add test-only deterministic controls and run the new branch's source-pinned focused workflow (expected RED on inherited code), preserving raw exits, SHA256SUMS, artifact SHA256, and source blob. Then apply minimal `collapse_stats` source correction; rerun same controls (expected GREEN), compile, privacy scan and diff check. Full software may retain inherited Run34/Run37 frozen-source preflight RED and is never relabeled GREEN. CI on Linux is not Redmi or native model proof. No World-JEPA utility, STEP2, B3, LP3, Body-JEPA or jepa_weight promotion.

## Ownership / continuation

Owner: this child branch only. Owned files: `v13/code/v13/world_jepa.py` (minimal diagnostic only), `v13/code/tests/test_world_jepa_numeric_noise_20261029.py`, `v13/code/tests/test_world_jepa_collapse_rank_20261029.py` (only remove invalid exact-float premise), `.github/workflows/v13-world-jepa-numeric-noise-20261029.yml`, and a dedicated BUILD_STATE file. No parent/Claude branch mutation. Stop on unexpected regression, preserve raw, and continue independent roadmap packages.