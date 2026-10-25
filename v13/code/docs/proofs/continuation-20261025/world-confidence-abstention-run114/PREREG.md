# Run114 — World counterfactual abstention in historical confidence ablation (preregistered)

Date: 2026-10-25 UTC. Parent: Run113 PR #144, commit `3ec03c37595c450ce78b9754977ca3755ff75c7a`.
Owner: `v13/code/scripts/ablation_world_model_confidence.py`, `v13/code/tests/test_ablation_homeo_meta.py`, new `test_world_confidence_abstention_run114.py`, Run114 CI/evidence files only. No edits to `v13/code/v13/world_model.py`, `episodes.py`, `episodic_route.py`, runtime, canonical blueprint or frozen source/model cohorts. Heavy native/model jobs prohibited here.

## Observed RED (Run113 full suite)
GitHub Actions run 40144632264, job 121023243288: 2151 tests in 150.803 s, 5 ERROR, 15 SKIP. `test_ablation_homeo_meta.WorldModelConfidenceAblation.test_spearman_and_real_fit` crashes at `cf['prediction'][t]` with `TypeError: 'NoneType' object is not subscriptable`. Current World Model correctly returns `prediction=None` when extrapolated outputs are physically impossible; do not weaken its fail-closed guard.

## Locked expected behavior
1. Keep the original `PREREG`, seeds, synthetic generation, arms and original win thresholds unchanged.
2. Treat no/invalid/nonfinite prediction as **abstention**, not a made-up error or correct prediction. Keep exact query accounting: `evaluated_n + abstained_n == Q`. Preserve reason counts; no confidence/spearman row for abstention.
3. If fewer than two evaluated predictions, arm Spearman is unavailable (`None`), not zero. Never rank missing errors as zero or a magic penalty.
4. Report diagnostics on evaluated queries only, with denominator and abstention counts visible. If any seed abstains or lacks comparable data, `run_all` must return `INCOMPLETE_ABSTENTION`, not `SUPPORTED_SYNTHETIC` or `PARTIAL`. The historical original primary protocol is not satisfied by an altered subset.
5. Add test-first RED for one and all abstentions, real World Model regression, and aggregate non-promotion. Run focused tests + privacy scan. Preserve original Run113 failure and new RED logs.
6. No STEP2/B3/Body-JEPA/whole-system gate promotion. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE, DS2 H2 FAIL.

## Next step
Commit RED test, observe failure in CI, patch only owned script/tests, rerun CI and archive closed evidence with source hashes. Other Run113 errors (three missing torch imports and missing `test_lp3_serial_cohort`) remain separately unresolved, not hidden.
