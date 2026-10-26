# Run556 prereg — exact frozen FUTURE_002 42-row STEP2 batch executor (source only)

2026-10-26. Base Run555 PR #554 head `8fa4b48496aff2d20031bca4ccef536ad55a8755`; stack includes reviewed Run554 native JEF and Run555 JEF session correction. This prereg is committed before Run556 code or tests. No native model execution or download in Run556.

## Why and frozen scope

The original Run491 heldout10 STEP2 cohort has 75 stages/1,050 rows, fixture SHA256 `c434a5765ed85b7c51022c5aaea0ba4c3150ef0f1490f466b4a8833e41b44c63`; original Run500/504 registration and all 3 model/runner SHA pins remain unchanged. Independently reviewed Run514: Run507 `FUTURE_001` A_s31_p00,p01,p02 = 42 native rows, zero wrong committed, but both_exact utility .0833 vs b1_only .0972, no STEP2 gate gain. Never rerun those stages. Run503 C_s31 70 rows already measured separately.

Run504 immutable future schedule selects next disjoint batch `FUTURE_002`: `A_s31_p03` Boreal/Cascade, `A_s31_p04` Drift/Eon, `A_s32_p00` Vesper/Willow, 14 rows per stage = 42. Expected row-key SHA256 `cbf6ee6fb2237f9de025a0a37029d37758280da77614d6364c5e0767be15a873`. No new fixtures or model/seed changes.

## Implementation / negative tests

Introduce a distinct `run556_future002_batch.py` based on the already reviewed Run505 serialized fail-stop mechanism; hard bind exact batch, schedule, stage map and expected row hash. It writes a one-shot plan with exclusive create, refuses partial/repeated stage directories, serially runs only the three fixed stage IDs after actual installed model/runner/library SHA preflight, fsyncs raw progress and stops on first RED without losing prior receipts. Source-only mocked tests: correct frozen 42 keys/no overlap, tampered manifest and plan rejection, success, second-stage failure with third not run, wrong receipt/JEPA gate rejection, existing stage refusal. Test `--plan` only in Run556 CI; native `--execute` requires separate prereg/owner check, independent native CI and raw evidence in later package.

## Claim limits / continuation

`STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `Redmi=UNMEASURED`, `V13=INCOMPLETE`. Preserve old RED/native artifacts and SHA-closed raw, official privacy scan, no production runtime/learning/age/approval changes. If source-only green, Run557 can schedule actual FUTURE_002 42-row Linux-native experiment under existing `v13-native-c3-run131-serialized` concurrency group only when no heavy owner; retain native RED and partial progress, never fake a result.
