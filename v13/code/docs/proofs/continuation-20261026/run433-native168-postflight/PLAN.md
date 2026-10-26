# Run433 — actual Linux-native O_s21 168-row independent postflight

Date 2026-10-26; owner GPT. Review-only no-model workflow stacked on Run430/PR429 exact head `865a9838fda687773a4cf443d9db87bf259a861b`, which inherits Run429/PR428 verifier and Run421/Run397 frozen source. No new model inference, downloads or competing native owner.

## Actual observed prerequisite

Run427 Actions `40263042202`, source head `f98db0c7bca16c005bc987bcc507aa3abbdf66f4`, completed **success** at ~03:38 UTC. Its actual source log reports `STAGE4_NATIVE_PARTIAL_NO_PROMOTION`, `rows=168`, completed `O_s20,P_s20,S_s20,O_s21`, STEP2 `UTILITY_FAIL`. The producer independently checked its own safe export but this is **not** a separate-host independent postflight.

Observed GitHub artifact metadata (not guesses):
- Small raw ID `12626041558`, outer SHA256 `3f7b66330778bd2129673c74d2917dcfe9b6ef8e2281df7f8557fd5c89bcecf5`, 12,655 bytes.
- No-model safe work ID `12626146409`, outer SHA256 `405e62268b0314c6e852e367a4624a12508e971877afe14afebf05cb2afba6b7`, 29,420,781 bytes.
- Both `expired=false`, `workflow_run.id=40263042202`, same head and repository; source log contains matching SHA256 digests and IDs.

## Independent acceptance

Fresh GitHub Actions runner must verify source/runner/model-catalog Git blobs, Run427 producer conclusion/head, both artifact metadata digest/expiry and exact downloaded ZIP SHA256. Extract only `RUN427_STAGE4_REPORT.json` from the small raw ZIP; reject ambiguous/missing members, inspect required fields, never invent report. Pass safe ZIP through unchanged Run430 atomic importer, which requires Run429 independent 168-row verifier *before* publishing restored directory. Independently invoke Run429 again on restored export. Require identical receipts, manifest, progress, all negative gates. Close and upload only small raw logs and report hashes, never work/models/weights. Failure must be retained, not silently retried. No P_s21 native until independent 168 proof GREEN.

## Claim limits

Even a successful Run433 proves only structural 168/378 Linux-native STEP2 rows; STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi unmeasured, full V13 incomplete.
