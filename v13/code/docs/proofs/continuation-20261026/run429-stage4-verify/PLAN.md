# Run429 — independent O_s21 168-row native verifier and safe import, no models

2026-10-26; owner GPT; review-only branch `codex/run429-stage4-168-verifier-20261026` stacked on Run427/PR426, which is currently executing exactly one pinned O_s21 native arm under exclusive concurrency. This package is source-only and **must not start another native/model job**.

## Contract
Run427 native output must be `STAGE4_NATIVE_PARTIAL_NO_PROMOTION` with 168 rows and exactly `O_s20,P_s20,S_s20,O_s21`, 42 per arm, actual Linux-native execution, no errors, no canonical gate promotion. Independently verify complete safe-export inventory and all file SHA256, frozen Run394 fixture/seed/arm manifest, every Run397 source/tool/summary/row replay receipt via unchanged validator, and model/runner hashes. Preserve original negative attempts and avoid rewriting raw evidence. Verify no installed model weights in exported archive. Fail closed on changed or missing bytes. No STEP2/B3/Body-JEPA/Redmi promotion.

## Why separate
Run419 independent verifier is fixed at 126; Run403 full verifier requires all 378. A dedicated partial verifier is required before P_s21; it must never mistake 168 structural native rows for the full STEP2 acceptance gate. New source-only tests include report tamper, expected-prefix order, missing O_s21 and negative gate assertions. Actual-data workflow should be added **only after** Run427 publishes artifact IDs and SHA256, to avoid inventing inputs or launching another native owner.

## Next
Wait for Run427 source/actual result; if GREEN bind its raw and safe ZIP IDs/SHA, run independent 168-row import in a fresh Actions runner, then proceed to P_s21 under same exclusive group. If RED, preserve failure and work another package.
