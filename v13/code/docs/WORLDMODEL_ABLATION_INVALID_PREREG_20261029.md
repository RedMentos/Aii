# World-Model ablation invalid-output consumer recovery — preregistration

UTC 2026-10-29. Review-only child of PR #1135 at `32e6f4846ef03f3d8934f3824f809ff43763a70d`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. This is a response to **observed** exact-head full-suite RED `40938719557`, not a new preregistered scientific cohort.

## Observed cross-organ regression

After the correct World-Model output-domain guard (PR #1135), `scripts/ablation_world_model_confidence.py:run_seed` still assumes every `counterfactual` has a numeric `prediction`. Its historical synthetic world can generate physically invalid target values; the new guard correctly returns `prediction=None`, `SIMULATION_UNCERTAIN`, zero confidence. The ablation crashes with `TypeError: 'NoneType' object is not subscriptable`. Full suite: **3257 tests, 3 ERROR, 11 skipped**: this new consumer error plus two separately proven inherited Run34/Run37 historical scorer pins. Original raw SHA256 `b095dc55d48add692bcff5ade22c454a25e0e996a76af7b0ebe76c869c479741` is closed and privately backed up.

## Binding repair, without post-hoc metric promotion

Keep `PREREG`, `SEEDS`, `N=300`, `Q=400`, original synthetic `world()`, action policy, target generation, noise and query order **byte-identical**. For a counterfactual with `prediction=None`, retain the query in the fixed denominator with `invalid_output=True`, label `SIMULATION_UNCERTAIN`, confidence 0 and `err=None` (unknown; never invent an error). Report `invalid_output_n` and `error_measured_n`. If **any** invalid output exists, every registered primary Spearman value is **None**, and the per-seed `status` is `UNSCORABLE_INVALID_OUTPUT`; do not silently drop rows and calculate a misleading primary on a changed subset. Optional valid-only descriptive diagnostics may be labeled post-hoc, never the registered primary. Label counts still sum to original query count; mean errors use only rows with actual numeric error and declare that denominator.

At `run_all`, if any seed is unscorable, return `verdict='UNSCORABLE_INVALID_OUTPUT'`, `wins_of_5` and `summary` numeric values None, and no `SUPPORTED_SYNTHETIC` or `PARTIAL` claim. For a genuinely complete all-valid cohort, retain the old primary and verdict arithmetic exactly. The historical cohort remains immutable; no rewrite of scorer/source/model/seed pins, no synthetic failure hidden, no World-Model guard weakening.

## Tests and evidence

1. Original `test_ablation_homeo_meta.py` WorldModelConfidenceAblation must not crash; fit status FITTED, 20 original queries accounted for.
2. Force invalid output on all queries: no invented error/primary, all invalid counted, verdict UNSCORABLE.
3. Force valid predictions on all queries: old numeric Spearman and label accounting remain available.
4. Focused original world-model and ablation suites pass; compile/privacy/diff pass; full software suite rerun and all raw preserved. The two historical Run34/Run37 current-source errors remain negative, not waived.
5. Software/synthetic only, no native/Redmi or whole-system gate promotion.

Owned files: `v13/code/scripts/ablation_world_model_confidence.py` (consumer only), `v13/code/tests/test_worldmodel_ablation_invalid_20261029.py`, `.github/workflows/v13-worldmodel-ablation-invalid-20261029.yml`, this prereg, dedicated BUILD_STATE.
