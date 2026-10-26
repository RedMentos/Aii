# Run425 — actual Run418 S_s20 126-row independent postflight, no models

2026-10-26; owner GPT; review-only branch `codex/run425-actual-native126-audit-20261026` based on Run421/PR419 head `7f56bcae0cf495c9e2c521b116242bb2f575c5ed`. Independent of Run423 HX2 and Run424 WorldState. No frozen Run394/397 changes, no new native model job.

## Observed prerequisite
Run418 exclusive Linux-native Actions 40260347495 completed SUCCESS at source `a09c1b59db063ba0e6dc25d129abaad3e8833049`. Its log reports 126 O/P/S_s20 native rows, no errors, canonical STEP2 `UTILITY_FAIL`. Small raw artifact 12625030366, SHA256 `54a6b12638dfdc0e9f71f362d3357dd70adfe0ba2441d26c4c3eba3e37bb364b`; safe no-model work artifact 12624815819, SHA256 `20ce321d29f04089a087421e16ddd5d854c103d36b7c958e4b0e11815f45cac4`. These are observed Run418 producer receipts, NOT independent Run419 postflight yet.

## Actual-data experiment
New read-only PR workflow downloads **only** the two above immutable GitHub Actions artifacts using the repo-scoped read-only workflow token; checks outer ZIP SHA256 before reading any member; extracts only the named small JSON stage3 report; invokes unchanged Run419 atomic importer and independent verifier against the real no-model export; then runs unchanged Run421 source-only `STAGE4_READY_NO_NATIVE` preparation (without `--execute`). Preserve exact raw stdout, SHA256, exit statuses, and privacy scan in a small artifact; do not upload restored native work, model weights, raw private chat or installed binaries.

## Gates and next
If verified, mark only actual Linux-native 126-row postflight and O_s21 readiness, **not** O_s21 execution or STEP2 success. O_s21 requires separately serialized native owner with exact registered models/runner and explicit `--execute`; Redmi proof remains missing. On any RED, preserve original failure and continue other packages.
