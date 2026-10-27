# Five-way AG5+World+Claude+PR667+PR669 broad differential (2026-10-27)

## Preregistered exact baseline
Prereg `PREREG.md` was committed at `bcadfabcf26a9bc760fe82a1f939464daf45c368` before the test workflow. Frozen historical AG5+World baseline Actions `40460394112`: 4,424 tests, **5 FAIL / 73 ERROR**, sorted unittest failure-header SHA256 `7fb3abd6ce63db14c0f740248d3cc6740d83f0f9d9812330053b995e32c64e5a`. Baseline original raw ZIP remains private and unchanged. Expected acceptance: exact same signatures, no new failures, test count >= 4,424. This is a differential acceptance only, **not full-suite GREEN**.

## Result and closed evidence
Actions **`40462730803`** at workflow head `c0aaa34f7d4eb85cb03bf3b514378860b3509360`: exact AG5 three-conflict merge/resolve, Claude `e505364c`, PR667 `551d6212`, PR669 `2671f054`, two-command guide repair in the disposable tree. **128 focused tests PASS (2 skipped)**, compile exit0, privacy CLEAN. Broad software suite **4,483 tests, 5 FAIL, 73 ERROR, 28 SKIP**. Full-suite exit **1 (RED)**. Differential audit exit0, status `HISTORICAL_RED_UNCHANGED`: observed fingerprint **exactly equals** `7fb3abd6ce63db14c0f740248d3cc6740d83f0f9d9812330053b995e32c64e5a`. No new failure signatures despite 59 additional tests.

Original ZIP artifact `12714654986`, SHA256 `1ff54f58f1e2e3a3c8aa92564a709dc4ae6bfcbaafbfcbc41675d83b90a90657`, CRC clean, 42 members, exact HEAD/merge/test/compile/privacy/differential exits independently checked. Private Library `/V13-Checkpoints/2026-10-27/AG5-World-Fiveway-Broad/v13-fiveway-broad-40462730803.zip` was byte-compared and SHA256 reverified. All historical errors and original RED runs remain retained.

## Scope, blockers and exact next
The five-way integrated review tree is separately durable at draft PR #672 commit `9eae3cc175512382038cc5f55887e7a8dbc9797f`, Git tree `9ff3f1e7cbe6fe3508ccb38e2265c614e0a8463a`, exact-match with CI tree. It is **not production integrated**. The historical 78 failures remain; their source-lineage/hash-bound expectations and native fixture limitations must be reviewed, not silenced or reclassified as PASS. No Redmi/real network/model/native Body-JEPA proof. STEP2 `UTILITY_FAIL`, B3 `L1_FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, full canonical architecture incomplete.

Next exact command on PR #672 checkout: `cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python -m unittest discover -s tests -p 'test_*.py' -v` in isolated `numpy==2.3.5` / `prompt-toolkit==3.0.52` venv, compare signatures with baseline. Then run phone ZIP source package and extracted startup smoke (software-only), plus independent source-binding review; do not merge main or promote gates.
