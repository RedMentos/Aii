# Run173 prospective full-suite recheck — exact LP3 sibling dependencies

Owner: new Run173 workflow and proof only; base Run172 `f2582d16d45f993a859e5f569efa8322e67f0d01`. Frozen runtime Git blob `a691d27bd0772a4fa1f03d57ec90663237bf6825`, unchanged. No model inference, no production changes or hidden test exclusions.

## Precommitted repair scope

Run164 (`40164614779`) **FAILED 4/2358**: three identical LP3 default-CLI rc1 vs expected rc2 and one live descendant after leader reaping. Run172 (`40166518201`) reproduced CLI rc1 with `ModuleNotFoundError: lp3_native_readiness` when exact Run21 helper reconstructed from Run20 code-only archive without sibling audit modules. Run172 local control with exact two siblings gave rc2/BLOCKED. This is a confirmed *import failure in the reconstruction*, but the original full-suite and live-descendant tests still require an independent rerun.

Run173 reproduces the full Run164 CI environment and pinned dependency set, but stages two **existing, unmodified** source-bound modules into the private temporary Run21 helper directory: `lp3_native_readiness.py` Git blob `2dfa7099541d3f8940817d43b97746c1d4d27092`; `lp3_closed_evidence_audit.py` Git blob `6068ddafa2ae319f66a1cfcd7fb50127372e20a8`. Reconstructed Run21 launcher SHA-256 `05e5bf300f582a03efeaae0133c8e20bf60948a2fa4e05a4867924ac4dc4b831`, original test blob `4e355dd45eda22a486f06af69b6c0d0fc35f178c`. No test assertions changed.

Run full `python -m unittest discover -s tests -p test_*.py -v`, preserve closed raw log and **true nonzero result**. If the three CLI failures disappear but descendant survives, the full suite remains FAIL; do not promote. Official privacy scan and shared serial concurrency group retained.

## Gates and exact next step

`STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `DS2_H2=FAIL`, `V13=INCOMPLETE`. Run171 native predictor heldout `commit_eligible=False` also remains a separate negative result.

After Run173 CI, inspect all failed tests and raw stderr. If orphan descendant persists, review Run24 atomic clone3 candidate with real cgroup kernel evidence before any safe production integration. Do not use old post-reap killpg; PID reuse is unsafe. Do not retry rejected Drive destination.
