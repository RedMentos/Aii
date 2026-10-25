# Run353 prereg — exact-source applicability for historical source-handoff phone packaging tests

Base: verified Run352 checkpoint `b04fb7678a7ed684c2138e8def24ac0415ed8510`, review chain PR348→PR347→PR346, not main. Owner: `v13/code/tests/test_package_source.py` plus this proof folder and optional isolated CI. No production Runtime, frozen source, source-handoff candidate, model, native runner, learning/age/approval or source cohort edits.

## Observed RED (prior to source change)
Exact Run352 focused CI `40226631286` fails in extracted V13 Phone package `test_actual_phone_zip_runs_source_handoff_regressions_after_extraction`: nested `test_source_handoff_candidate` / `test_source_handoff_ablation` see 15 errors, `ValueError: Runtime is neither exact frozen baseline nor complete reviewed candidate`. This is the historical candidate's **correct fail-closed response** to newer production Runtime; the packaging test erroneously demands those historical tests pass on arbitrary later runtime revisions. The same file already handles obsolete `native_firing_runtime_candidate` correctly with an applicability probe, exact error check, and corrupted fixture counterexample.

## Frozen acceptance
1. On extracted phone ZIP, probe historical `source_handoff_candidate.sources()` first. When source binding is exact, execute the original source-handoff candidate + ablation test suites unchanged and require PASS. When source binding is stale, require the exact known fail-closed error, then separately verify `load_candidate('cognition')` and `source_handoff_ablation.arm_sources()` refuse; never call the old suite against incompatible current sources.
2. Corrupt the archived source-handoff baseline fixture in a fresh extracted ZIP; applicability must NOT classify the digest error as ordinary stale Runtime. The test must fail for corruption. Keep the native-firing precedent and all original frozen tests untouched.
3. Run `python -m unittest -v tests.test_package_source` and the focused extracted-phone workflow against exact PR head. Keep previous failed raw CI receipt, new PASS/FAIL logs, privacy scan and hashes. No native or Redmi claims.
4. If other failures remain, preserve and diagnose them; no relaxation of original source-handoff hash guard or full-system gate promotion.

Next command: `python -m unittest -v tests.test_package_source` from `v13/code`, plus focused Actions exact-head.