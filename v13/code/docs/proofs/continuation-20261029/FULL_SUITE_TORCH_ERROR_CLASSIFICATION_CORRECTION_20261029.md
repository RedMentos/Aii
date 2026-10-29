# Independent raw replay correction — prior torch-only full suite (2026-10-29)

This is an **additive correction**, not a retroactive rewrite of the frozen preregistration `FULL_SUITE_TRANSFORMERS_PREREG_20261029.md`. That preregistration and the initial PR text incorrectly classified all four non-frozen errors as missing Transformers. The exact original raw distinguishes **three** missing `transformers` test-module imports and **one** missing `peft` runtime import.

## Byte-exact source
- GitHub Actions `40957012351`, artifact `12933534420`, original ZIP SHA256 `c3abbd38acc66b12f4bb495849dd3faccbdca74e93286f6d4e3c6102e5dc826d`.
- Downloaded original ZIP, CRC clean; **22/22** internal `SHA256SUMS` entries independently matched.
- Uploaded unmodified ZIP to private Library `/V13-Checkpoints/2026-10-29/Run10-FullTorch-Independent/v13-full-torch-40957012351.zip`; re-materialized file SHA256 matched original byte-for-byte.
- Exact raw summary: 3285 tests, 6 ERROR, 11 skipped, exit 1. Three `unittest.loader._FailedTest` import errors: `test_body_jepa_checkpoint_fit`, `test_lp3_shift_row_control_20261028`, `test_lp3_state_prefix`, all `ModuleNotFoundError: No module named 'transformers'`.
- Fourth dependency error: `test_body_jepa.MinorSubspaceTests.test_wide_and_tall`, `ModuleNotFoundError: No module named 'peft'`. This error is not a Transformers import error.
- Remaining two: Run34 and Run37 frozen `native_source_or_catalog_changed` preflight. Their original pins are not waived or modified.

## Follow-on implications
The already-running preregistered `transformers==4.44.2` workflow `40958983649` must finish and preserve its original raw unchanged. It may resolve three imports but **cannot be expected to resolve the separate missing `peft` error**; Body-JEPA fit may expose more missing-peft behavior. Next independent dependency experiment should pin compatible `peft==0.13.2` (and transitive Accelerate), with original failing run retained, no test exclusions, no source/Canon/cohort changes. Only measured output may determine next action.

Gates unchanged: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight 0; Redmi UNMEASURED; V13 INCOMPLETE.
