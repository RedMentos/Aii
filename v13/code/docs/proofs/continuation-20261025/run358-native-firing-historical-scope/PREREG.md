# Run358 prereg — Run177 historical native-firing workflow applicability

Parent: verified Run357/PR353 head `9c74c2d8ed74c5002259da10c4a6b541382dfa14`, review chain, not main. Owner: only `.github/workflows/run177-native-chain-reconcile-20261025.yml` and this proof folder. No original native-firing candidate code, frozen baseline, Runtime, model/seed, learning/age/approval, or tests changed.

## Observed RED
Run357 exact-head lineage workflow `40228294184` PASS (20/20), but inherited historical Run177 workflow `40228294012` FAILED in `Historical native-firing candidate and merged compatibility tests`. The workflow unconditionally executes old native-firing candidate tests on newer Runtime/store that are not equal to the frozen baseline or integrated candidate. This is a legitimate source-binding refusal, not native failure; Run353 phone ZIP already handles the same historical cohort with an exact applicability probe and corrupted-fixture negative control.

## Frozen acceptance
1. Retain Run177 historical identity tests unchanged and PASS on exact branch. For the old native-firing candidate tests, first probe `scripts.native_firing_runtime_candidate.sources()`. If exact binding holds, run the original candidate and merged tests unchanged and require PASS. If stale, require the **exact** known fail-closed ValueError from `sources()`, `load_candidate('runtime')`, and `native_firing_candidate_smoke.merged_sources()`; record `HISTORICAL_NATIVE_FIRING_INAPPLICABLE_FAIL_CLOSED`, never report the historical tests as PASS.
2. Independently execute the existing corrupted-frozen-baseline counterexample `tests.test_package_source.PackageSource.test_historical_candidate_corrupt_fixture_is_not_misclassified_as_stale`. A corrupt archive is not stale and must still fail. No permissive source fallback.
3. Pin checkout to exact PR head, use isolated CPU-only deps, privacy scan, raw logs, closed SHA manifest, and private backup. Keep existing workflow's historical purpose and native negative gates.
4. This is source-only historical test applicability, not native firing, B3, STEP2, Body-JEPA, Redmi or AGI proof. No full-suite PASS claim.

Next command: `python -m unittest -v tests.test_run177_native_chain_reconcile_20261025 tests.test_package_source.PackageSource.test_historical_candidate_corrupt_fixture_is_not_misclassified_as_stale`, then conditional historical candidate suite only on exact applicable source.