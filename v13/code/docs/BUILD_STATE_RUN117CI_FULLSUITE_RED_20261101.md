# Run117CI BUILD_STATE — unfiltered current-chain full software suite remains RED

2026-11-01 UTC. Review-only sibling of Run117CJ at exact parent `594143dc778e4317f0b011b862a7b94232567488`. Owner: Run117CI. Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. No source/model/cohort changes, no waivers, no native/Redmi claims.

## Terminal original evidence

[Actions 41257747643](https://github.com/RedMentos/Aii/actions/runs/41257747643) **FAILURE**, exact source `44840c9991bd72aadc9d659934e9d54f39b5b44e`. Original artifact `13064530049`, 19,439 bytes, ZIP SHA256 `10610fb68aa6b801dab1d571153bc4a287ee120a835996f21dea92f1c2ae57f3`. Independently downloaded and verified: CRC clean, **25/25** inner SHA256SUMS, all environment/torch/transformers/peft/pip/compile/privacy/diff/pins stages zero, **FULL_EXIT=1**. Byte-identical private Library backup re-materialized and SHA256 checked at `/V13-Checkpoints/2026-11-01/Run117-Hourly11/Run117CI_FULLSUITE_RED_41257747643_sha10610fb6.zip`.

**Unfiltered result:** 5,331 tests in 491.850 seconds; **4 failures, 75 errors, 28 skips**. Prior Run117CC original 5,326 tests, 5 failures, 75 errors, 28 skips. Run117CH's synthetic C3 no-cache test repair removes its previous `STRUCTURAL_RED` failure; the remaining failures/errors are not silently waived.

Remaining 4 failures:
1. `test_eligibility_fixed.Config.test_chain_link_is_live`: frozen integrated-source identity mismatch.
2. `test_package_source.PackageSource.test_actual_phone_zip_runs_source_handoff_regressions_after_extraction`: nested frozen source-handoff errors in extracted ZIP.
3. `test_package_source.PackageSource.test_actual_phone_zip_runs_isolated_native_firing_candidate_after_extraction`: nested frozen source-handoff errors.
4. `test_package_source.PackageSource.test_actual_phone_zip_runs_approval_reader_and_merged_firing_after_extraction`: nested frozen source-handoff errors.

The 75 errors include original frozen-source baseline/candidate rejection, source catalog guards, and missing historical native artifacts on fresh scratch; do not bypass guards or treat missing artifacts as permission to skip. Test log contains nested subprocess failures; the authoritative count is the outer unittest summary, not a naive grep of `ERROR:` headers.

## Exact next work

1. Preserve original frozen-source mismatch and identify a *complete reviewed* source chain that satisfies the frozen baseline/candidate identity, rather than weakening tests.
2. Retrieve original pinned historical native artifacts from their registered owners/Actions IDs with byte hashes and isolated prerequisites; re-run scoped tests without changing cohort/seed/model/runner hashes.
3. Repeat full unfiltered suite only after a substantive source/artifact prerequisite changes; keep this RED original and all negative gates.
4. For current independently verified functional progress use Run117CK PR #1563 and Run117CM PR #1564 as **review branches**, not production merge. The Run117CI sibling is not an ancestor of Run117CK/CM.

Exact reproduction: `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest discover -s tests -p 'test_*.py'` under the pinned Linux Python/torch/transformers/peft environment in `.github/workflows/v13-run117ci-currentchain-fullsuite-retest.yml`.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; `jepa_weight=0`; no native/Redmi/learning/tool/output/whole-system promotion. Platform budget UNKNOWN.
