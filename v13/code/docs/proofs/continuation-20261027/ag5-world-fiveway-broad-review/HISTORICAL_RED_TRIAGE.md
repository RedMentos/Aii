# Historical broad-suite RED: 78 failure blocks classified without changing frozen tests (2026-10-27)

**Source:** byte-verified original five-way Actions `40462730803` artifact `12714654986`, `UNIT_RAW.log`. 4,483 tests, 5 FAIL, 73 ERROR, 28 SKIP, full-suite exit1. Exact sorted failure-header fingerprint `7fb3abd6ce63db14c0f740248d3cc6740d83f0f9d9812330053b995e32c64e5a`, unchanged from historical 4,424-test baseline. No source/test files were modified for this classification.

## Error categories (73 total)
| Count | Observed terminal exception | Interpretation / next proof |
|---:|---|---|
| 36 | `ValueError: Live sources differ from complete baseline/candidate` | Source-binding reject, not a verified runtime functional failure. A newly registered, fully hash-bound candidate and frozen cohort isolation would be required; do **not** weaken frozen lineage tests. |
| 27 | `ValueError: Runtime is neither exact frozen baseline nor complete reviewed candidate` | Same class of source-binding reject in a separate set of archived experiments. Preserve original baseline and candidate hashes. |
| 2 | `ValueError: Current reviewed source digest changed: v13/runtime.py` | Current runtime differs from registered reviewed digest; verify exact source change/provenance before any new registration. |
| 6 | `ModuleNotFoundError: No module named 'torch'` | Isolated Linux test environment lacks PyTorch; tests for FP32 Body and LP3 did not execute. Resolve dependency in separately budgeted CPU-only run; no native result may be inferred. |
| 1 | `FileNotFoundError: /mnt/data/RUN147_native.zip` | External pinned native audit artifact unavailable in CI. Retrieve exact hash-bound source or retain UNAVAILABLE. |
| 1 | `ModuleNotFoundError: No module named 'test_lp3_serial_cohort'` | Test module import/path prerequisite; independently reproduce under registered test harness, do not silently skip. |

## Failure categories (5 total)
- 2 `test_current_source_lineage_run357` assertions expect current reviewed source digest changes in `store.py`, but observe `runtime.py` mismatch first.
- 1 `test_native_jef_goal_run554` fixture reports `INTEGRATION_FAIL` (fixture only; not native).
- 1 `test_run177_native_chain_reconcile_20261025` exact integrated chain SHA mismatch for `v13/runtime.py`.
- 1 `test_run543_integrated_chain` byte-exact frozen reviewed chain mismatch for `v13/runtime.py`.

**Priority:** (1) independent read-only source-lineage diff and candidate eligibility; (2) isolated CPU-only `torch` + import-path prerequisites without changing cohort/model hashes; (3) locate exact RUN147 artifact or leave negative; (4) re-run 78 relevant tests with explicit evidence levels and compare. These are **historical known failures**, not successes, and their unchanged status does not promote STEP2, B3, Body-JEPA, `jepa_weight` or full-system completion.

Current owner: independent GPT-6 broad auditor. Exact command: `cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python -m unittest discover -s tests -p 'test_*.py' -v` on review commit `9eae3cc175512382038cc5f55887e7a8dbc9797f` with isolated `numpy==2.3.5` / `prompt-toolkit==3.0.52`. A different dependency set is a **new** run/cohort, not a reinterpretation of the frozen baseline.
