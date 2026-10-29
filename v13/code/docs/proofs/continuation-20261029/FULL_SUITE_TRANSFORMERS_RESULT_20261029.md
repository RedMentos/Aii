# V13 independent full unfiltered software replay with Transformers — observed result (2026-10-29)

## Exact experiment and evidence
- Draft PR #1151, review-only child of #1150, source/CI exact HEAD `3d78cebfbea84ba5b21ee1c77fc2c3a3cfa1ddcb`. No runtime/model/seed/cohort/Canon changes.
- GitHub Actions `40958983649` **completed FAILURE**, original artifact ID `12935131558`, ZIP SHA256 `5be46cb9fc6c73570475bd937692e06748f8267492013033c0e6519e2845d47f`.
- Downloaded the exact original ZIP: CRC clean, **26/26** inner `SHA256SUMS` verified; all 11 non-FULL stages `CANON/VENV/DEPS/TORCH/TRANSFORMERS/PIP_CHECK/TORCH_IMPORT/TRANSFORMERS_IMPORT/COMPILE/PRIVACY/DIFF` exit0; `FULL` exit1. Original raw ZIP retained unchanged and backed up privately at `/V13-Checkpoints/2026-10-29/Run10-FullTransformers-Independent/v13-full-transformers-40958983649.zip`, byte-exact re-materialization SHA256 matched.
- Installed imports confirmed `torch 2.5.1+cpu`, `transformers 4.44.2`, no CUDA. All installed package versions are recorded in original `PIP_FREEZE_RAW.log`.
- **Full unfiltered** `unittest discover`: **3304 tests, 4 ERROR, 11 skipped**. No test exclusions or waivers.

## Error classification from original raw
1. `test_body_jepa.MinorSubspaceTests.test_wide_and_tall`: `ModuleNotFoundError: No module named 'peft'`.
2. `test_body_jepa_checkpoint_fit.OptInFitResumeTests.test_interrupted_fit_exactly_matches_uninterrupted`: `KeyError: 'steps'`; the Body-JEPA fit returns an unavailable result when PEFT is missing, so no successful two-step fit was observed. Do not classify this as a proven training defect until PEFT is installed and retested.
3. Frozen Run34 `test_pinned_source_model_runner_and_negative_gates`: `native_source_or_catalog_changed`.
4. Frozen Run37 same test name: inherited `native_source_or_catalog_changed`.

The earlier raw-based correction remains in `FULL_SUITE_TORCH_ERROR_CLASSIFICATION_CORRECTION_20261029.md`: the original torch-only run had **3** missing Transformers imports, **1** missing PEFT import and **2** frozen errors. The current experiment resolved all three missing Transformers imports but revealed the second PEFT-dependent BJ1 fit error. Neither the historical source pins nor the test assertions were modified.

## Next package and claims
- Next already preregistered independent child: PR #1152, `FULL_SUITE_PEFT_PREREG_20261029.md`, pinned `peft==0.13.2` plus existing isolated torch/Transformers. Start its full suite only after this run completes; retain both original RED ZIPs. If new failures occur, classify them from raw, do not waive.
- Linux software/synthetic HF only, **not** Linux-native LFM2/Redmi, not Body-JEPA utility, not LP3 utility, not a complete V13.
- Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, Redmi UNMEASURED, V13 INCOMPLETE.
