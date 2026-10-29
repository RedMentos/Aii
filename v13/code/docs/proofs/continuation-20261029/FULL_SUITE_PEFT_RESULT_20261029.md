# V13 full unfiltered software replay with PEFT — observed result (2026-10-29)

## Exact run and preserved evidence
- Draft PR #1152, review-only child of #1151. Exact Actions source HEAD `552626808b6fbdff9dc9a5b19c1ff9e946f2b368`; workflow `40960222503` **completed FAILURE**, not full-suite PASS.
- Original artifact ID `12935267907`, ZIP SHA256 `518e5bc842c73e483f38c05dcabe2ea8b3b57556ae709f454047d399258787f1`. Downloaded original ZIP, CRC clean, **30/30** internal SHA256SUMS independently matched. All 13 non-FULL stage exits 0; `FULL_EXIT=1`. No source, test, model, seed, cohort or Canon change.
- Exact pinned imports: CPU `torch==2.5.1+cpu` (CUDA False), `transformers==4.44.2`, `peft==0.13.2`; resolved `accelerate==1.15.0` and other dependencies in `PIP_FREEZE_RAW.log`. `pip check` exit0.
- **Full unfiltered 3304 tests, 2 ERROR, 11 skipped**. The only two remaining errors are the intentionally frozen Run34 and Run37 `test_pinned_source_model_runner_and_negative_gates`, both `native_source_or_catalog_changed`. They remain genuine RED and must not be waived or silently repinned.
- Original raw ZIP saved privately at `/V13-Checkpoints/2026-10-29/Run10-FullPEFT-Independent/v13-full-peft-40960222503.zip`; re-materialized byte-exact SHA256 matched.

## Comparison to earlier preserved failures
- Original torch-only `40957012351`: 3285 tests, 6 ERROR, 11 skipped (3 missing Transformers imports, 1 missing PEFT import, 2 frozen pins), ZIP SHA256 `c3abbd38acc66b12f4bb495849dd3faccbdca74e93286f6d4e3c6102e5dc826d`.
- Transformers-only `40958983649`: 3304 tests, 4 ERROR, 11 skipped (2 PEFT-dependent BJ1 errors, 2 frozen pins), ZIP SHA256 `5be46cb9fc6c73570475bd937692e06748f8267492013033c0e6519e2845d47f`.
- PEFT added: the two PEFT-dependent BJ1 errors disappeared and all other non-frozen tests completed without reported failure. This is **Linux synthetic/software compatibility evidence**, not a learned-utility result or real native Body-JEPA proof.

## Next independent package and negative gates
- PR #1153 has a separate Body-JEPA derangement fail-closed source change, already 4/4 GREEN stdlib-only; next run its existing torch/PEFT BJ1 regression tests against **that changed source** with the same isolated dependency versions. The full suite here ran on the **older** source and cannot validate PR #1153.
- Historical Run34/Run37 preregistration remains frozen. Any future rebaseline requires a new explicitly labeled cohort; never rewrite original pins or report these two errors as PASS.
- Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; Redmi UNMEASURED; V13 INCOMPLETE.
