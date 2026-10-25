# Run164 — exact-head full-suite portability correction (2026-10-25)

**Base:** Run159 `ff2610d1e2cb3a05ce46da9100d82c348843fcfa`; own review branch `codex/run164-fullsuite-portability-20261025`. Ownership: test-only `v13/code/tests/test_toolforecast.py`, new workflow and proof. No frozen Runtime/model/cohort changes; no other owner's branch overwritten. No native/model job launched locally. CI concurrency uses existing `v13-native-c3-run131-serialized` group.

## Independent closed Run159 failure (preserve as FAIL)
Original GitHub Actions run `40163425395`, full-suite job `121079570618`, exact head `ff2610d1`, raw artifact `12586869669` (ZIP SHA256 `245899a860fdce536860dbda2cc713759cd776d5b4e4a943678f6ade1c20b100`). Official privacy step PASS, pinned dependency install PASS, **2316 tests, 2 ERROR, 11 SKIP, suite FAIL**:
1. `test_lp3_serial_review_run18`: `ModuleNotFoundError: No module named 'test_lp3_serial_cohort'`. Run159 reconstructs LP3 helper from hash-checked Run20 tar and adds only `scripts` to PYTHONPATH, not reconstructed `tests`.
2. `test_toolforecast.CheckpointTests.test_competence_check_scores_states_not_calls`: `PermissionError [Errno 13]` on optional historical `/root/native/restore/round8-note-tool-raw`. Python 3.12 Path.exists can raise on inaccessible ancestors. No claim of a failed forecast algorithm; the test was interrupted before optional comparison.

## Narrow fixes (candidate)
- New Run164 CI adds reconstructed `test_lp3_serial_cohort.py` parent directory to PYTHONPATH after checking expected Git blob `4e355dd45eda22a486f06af69b6c0d0fc35f178c`. Retains frozen Runtime hash, Run20 tar SHA, patched LP3 helper hash, Run147 artifact SHA, pinned CPU dependencies and full discovery.
- Test-only optional legacy fixture helper catches **only** `PermissionError`, treating an inaccessible optional `/root` fixture as absent. Accessible fixture still executes original `cc.plan` comparison. Adds two focused tests for denied and accessible cases.
- Full-suite CI uploads closed raw output even when failing, then enforces the actual exit status. Does not skip or mask other errors.

## Gates and next steps
`STEP2=UTILITY_FAIL`; `B3_L1=FAIL`; `Body_JEPA=UNAVAILABLE`; `jepa_weight=0`; `DS2_H2=FAIL`; `V13=INCOMPLETE`. Software CI is not native model or Redmi proof.

1. Verify Run164 workflow YAML and GitHub CI; preserve any new failures as raw artifact, do not relabel as PASS.
2. Independently cross-review test-only patch; if full suite passes, report exact count, skips, privacy, frozen hash, not full V13.
3. Continue separate BodyTrainPort and A3 canonical packages without changing current registered cohorts.
