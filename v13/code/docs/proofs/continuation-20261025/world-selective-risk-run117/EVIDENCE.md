# Run117 — closed fresh 20-seed selective-risk evidence (2026-10-25 UTC)

Parent: Run114 PR #145 `6fce98c2111429b1951e6e527608cb9c543c21b3`. PR #148. All model data **synthetic own digital transitions**; no native model or Redmi.

## Test-first evidence
- **RED** GitHub Actions run `40145847019`, job `121026883262`, head `ebb8bc2272b7df918d13cfbfebb641156938c819`: `test_world_selective_risk_run117 ... ERROR`; `ModuleNotFoundError: No module named 'ablation_world_selective_risk_run117'`; `Ran 1 test ... FAILED (errors=1)`. The new script did not exist yet.
- **GREEN** run `40145901308`, focused job `121027051080`: `Ran 5 tests in 0.140s — OK`; privacy CLEAN; fresh cohort job `121027118044` PASS with negative scientific verdict.
- **Closed full JSON** run `40146015102`, job `121027470022`, head `52910321a2bf7efa494efee42b79cda620c50db4`: complete `RAW_20_SEED_OUTPUT.json`, 20 seeds × 400 queries, original CI SHA-256 `55d23c892c4add4d3d937c8ed0f2c4b4b1ff20f4b82f6fcb7b76199b3282ffab`. Exact Git blob `ad502e8ef904a2a50b4dbe05f1a15fda3fb7217b`; verified byte-for-byte against the CI log output. No post-hoc cohort or threshold changes.

## Observed outcome (NOT a positive result)
- `NOT_SUPPORTED_SYNTHETIC_SELECTIVE`. All 20 seeds eligible, 8,000 queries, **2,605 valid predictions, 5,395 abstentions**. Top quartile of valid queries selects 643 total, only **8.0375% of all queries**.
- Strict paired wins of actual confidence vs controls: samples-only **15/20**, spread-only **7/20**, random **20/20**. Preregistered positive rule requires at least 16/20 against **all three**, plus lower mean risk against each. **FAIL**.
- Mean selected absolute error: confidence **0.45398068**, samples-only **0.48839680**, spread-only **0.42877628**, random **0.59084627**. Spread-only is better on this synthetic task; confidence is not established as the best confidence estimator.
- This result does not establish the utility of the 5,395 abstentions, a real-world calibrated risk bound, causal utility, generated-answer improvement or any AGI capability.

## Primary methodology
Selective prediction evaluates error conditional on accepted coverage; compare Geifman & El-Yaniv, *Selective Classification for Deep Neural Networks*, NeurIPS 2017, https://papers.neurips.cc/paper_files/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html . Run117 is a simple synthetic fixed-quartile diagnostic, **not** their statistical guarantee.

## Source binding
- `scripts/ablation_world_selective_risk_run117.py`: Git blob `aa814ccb3ccea794339e1c68222db6fadedfdada`
- `tests/test_world_selective_risk_run117.py`: Git blob `a135a938602c7fdbe997678edea837f4dc142977`
- `scripts/ablation_world_model_confidence.py`: Git blob `fb7a60def4abb75c76d269222adc3da6da96aebf`
- `v13/world_model.py`: Git blob `17aa0abd22ae0c67b0a3a3de5d7e5ef3d7e2c915`

All original gates remain: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; DS2 H2 FAIL; V13 INCOMPLETE. No changes to World runtime, registered original Run114 seeds, native cohorts or approval gates.

Exact reproduction in a full checkout: `cd v13/code && python scripts/ablation_world_selective_risk_run117.py /tmp/world-run117.json && sha256sum /tmp/world-run117.json`. Requires Python with NumPy; expected SHA-256 above. This is Linux synthetic evidence, not Redmi.
