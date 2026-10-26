# Run401 — registered STEP2 full-cohort native stage 1 (O_s20 only)

2026-10-26. Owner: GPT scheduled continuation. Base: Run400/PR395 exact head `c6813d6e5139c5d4675e9b997c06fc9ce44884f9`, stacked review, not main. Own only new `.github/workflows/run401-step2-full-native-stage1.yml` and `v13/code/docs/proofs/continuation-20261026/run401-full-native-stage1/`. Do not edit frozen Run394 fixtures/seed/arms, model catalog, runtime source or Run397 runner.

## Prerequisites and budget

Run395 42-row actual Linux-native pilot completed 2026-10-26 00:33:08Z (Actions `40247992605`) after 23m24s including pinned model/runner bootstrap. Independent Run400 postflight `40250408193` confirms 42/42 actual rows and zero wrong committed actions, with `STEP2 UTILITY_FAIL`. The descriptive `both_exact` P−O +0.20833 across only 2 fixtures is **not** causal proof. Full preregistered Run394 cohort is 6 fixtures × 7 variants × 3 arms × 3 seeds = **378 rows**. Run397 append-only resume wrapper is source-tested (34/34 inherited); real restart remains unproven.

Run401 tests a **single** native full-cohort attempt `O_s20` (42 rows), with `--full --execute --max-new-arms 1`. One owner, same GitHub Actions concurrency group as Run395, no parallel model job, Ubuntu 24.04, exact pinned public model/runner hashes, isolated Python dependencies. No paid provisioning or device access. Expected ~20–35 min including bootstrap; 100-min hard workflow timeout, bounded native invocation. If a stage is RED, preserve partial raw and do not falsely mark complete.

## Verification

- Before native: check exact PR head, frozen Git blob hashes, Python source tests, public model card/license hashes and installed artifacts deep verification. Never upload weights.
- After native: validate Run397 progress, exactly one completed `O_s20` with 42 distinct fixture×variant native rows, actual model/runner/source/consumer hashes and zero wrong committed actions. No other completed arm, all remaining 8 pending.
- Hash-close every log/manifest/attempt JSON, upload complete append-only work tree and raw to Actions artifact even if RED. Record GitHub run/job/artifact SHA and mirror to permitted private Library. Do not omit partial failures.
- Preserve STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA/jepa_weight=0, Age0/approval unchanged, no Redmi proof, Run389 full-suite RED, whole V13 incomplete.

## Continuation

Next stage must **download and verify the exact stage-1 artifact** and restore all original append-only bytes before calling the same Run397 runner with `--max-new-arms 1`; never overwrite an attempt or restart from an empty folder while claiming resume. Independent review required before further stages. A stage-1 success is not a full-cohort or STEP2 acceptance.

Stop this stage only for native errors, resource budget or actual CI limits; preserve RED. Continue other independent blueprint packages while the native owner is active.
