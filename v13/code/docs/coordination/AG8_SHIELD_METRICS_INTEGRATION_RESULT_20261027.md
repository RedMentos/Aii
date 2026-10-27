# Strict AG8 regression shield metrics — current HX134 integration verified result (2026-10-27)

Review-only PR #790, child of PR #789. **Reuses prior verified PR #375 / Run380** strict metric validation on the newer HX134 durable-approval and request-revocation tree. No overwrite of PR #375. Prereg `90d278df078569445ff60888f5f7d8b7ac2f4f56` before exact Run380 test blob `0d07e975513b3adb4c24d3244314a13ba0e73926` and test-only RED.

**RED Actions `40596864476`** at `e31a7708dca0b9c0aebd8d16e9687465ef62aeaa`: 33 focused tests, **7 expected failures** (missing/bool/out-of-range axes, one-sided/infinite forgetting, rounded-away regression and gain). Original artifact `12777486041`, SHA256 `71290f9c30f5db90374e6006a8f7c38dee854a254bec86ebf92998e4cfaaacdc`, CRC/internal SHA256 PASS.

Fix `4eb9df40017b1fc60c7ce3ec3f641dc1c4c580cd`: retains current `require_approved_origin` and request-status check, integrates Run380 finite 0..1 complete axes, symmetric forgetting coverage, and unrounded comparisons. **GREEN Actions `40596976521`**: 33/33 PASS, all raw exits0, privacy CLEAN; artifact `12777341441`, SHA256 `a277515deafe4ec038fc5d25e2c8e7a228e0d650846e462834c712765daa3d86`, CRC/internal SHA256 PASS.

**Full Actions `40597083477` SUCCESS** at exact head `3fd83a07c1e06f515ca32da909bc868285b4dc17`: 33/33 focused, **2030 full software tests OK (1 skipped)** in 145.623s; `PREREG/RED_TEST/FROZEN/INSTALL/FOCUSED/FULL/COMPILE/PRIVACY/DIFF` raw exits all 0, privacy CLEAN. Original artifact `12777441811`, SHA256 `5e9ef4efb95e75371548b9ea5def39ddbc64d9faed2b008bc2fefee6f96c1a77`, CRC/internal SHA256 PASS. All RED/GREEN/full ZIPs privately backed and re-materialized byte-identical at `/V13-Checkpoints/2026-10-27/Automation11-AG8-Shield-Run380-Integration/`.

Frozen source/test blobs: `self_improve.py=4ff5ee079653488d9117380c6b7435df38966824`, `test_ag8_shield_metrics_run380.py=0d07e975513b3adb4c24d3244314a13ba0e73926`, HX harness `78e3fd6c6c40a75db9cb88ea683194011e058d6f`, HX experience `83ede4b83161bc78b5cc718c647d984e06d9f54a`.

**Claim limit:** Linux software with deterministic evaluation callbacks, no native/Redmi, no actual utility gain, no live HX harness consumer. B3 L1 FAIL, STEP2 UTILITY_FAIL, LP1/LP2/BJ1 negative, Age0, authority0, `jepa_weight=0` and whole V13 incomplete unchanged. Downstream cross-organ PR #791 (C1+World+B3+Sleep+HX) must pass full CI before merging this shield; separate prereg `C1_WORLD_B3_SLEEP_HX_AG8_INTEGRATION_PREREG_20261027.md` governs. No production merge/auto-merge.

Owner GPT reviewer. Exact next command: `cd v13/code && PYTHONPATH=.:tests python -m unittest discover -s tests -p 'test_*.py' -q` on combined candidate with source hash and privacy checks.
