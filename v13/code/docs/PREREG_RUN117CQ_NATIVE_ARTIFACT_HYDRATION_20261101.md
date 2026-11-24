# Run117CQ prereg — hydrate immutable original native artifacts for software replay

2026-11-01 UTC. Review-only child of Run117CP at exact parent `d03897663dca43287d734119f7663b2d676842bd`. No native/model execution, no production Runtime or frozen source changes, no alteration to registered seed/model/runner/cohort hashes. This is an **environment-prerequisite repair**, not an attempt to waive full-suite RED or prove utility.

Original immutable GitHub Actions artifacts:
- Run117Z seed1065 real JEF→C3: artifact `13054946077`, SHA256 `65939e4dea18f15bf11d5b1b3c5128f5a6128c6d03b9d2beb090f185d03fb69a`; expected path `V13_RUN117Z_ORIGINAL_ZIP`.
- Run117AF seed1067 combined C3: artifact `13055310481`, SHA256 `1082b64fe8d5a8ed3f8026c5913e9712f51217f75d5544b762924016f9bfc888`; expected path `V13_RUN117AF_ORIGINAL_ZIP`.

The unfiltered Run117CI original [Actions 41257747643](https://github.com/RedMentos/Aii/actions/runs/41257747643) is RED: 5,331 tests, 4 failures, 75 errors, 28 skips. Among independent problems, fresh scratch lacks these original ZIPs, while many other failures come from frozen baseline/candidate source identity; restoring ZIPs does **not** solve those source mismatches.

Plan: new read-only Actions workflow with `actions:read` and `contents:read`, no models/weights/downloads, retrieve the two original artifact ZIPs to isolated `RUNNER_TEMP` (never commit them), compare full SHA256 before unzip, reject corrupt ZIPs, then run existing exact native-record audit/replay tests: `test_run117aa_original_real_jef_native_audit`, `test_run117ae_combined_original_native_replay`, `test_run117ag_original_native_mutations`. Preserve original raw stage exits, hash receipts, privacy/diff/compile, and failures on GREEN or RED; do not skip or weaken any assertion. If replay still fails, classify source vs artifact prerequisites and continue another independent Canon package.

All Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, `jepa_weight=0`, no Redmi/learning/output/whole-system promotion. Remaining platform budget UNKNOWN.
