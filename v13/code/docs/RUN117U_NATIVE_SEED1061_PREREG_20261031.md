# Run117U — preregistered seed1061 pinned native Body/C3 three-arm experiment

## Ownership and immutable sources (registered BEFORE runner/workflow)

Review-only branch `assistant/v13-run117u-seed1061-native-threearm-20261031-1923`, parent exact `2448c8d06085c4ac728c6bc1f677ff474a85c089` (Run117S-R #1500, stacked on Run117S #1499). Existing Run117T reserved branch `assistant/v13-run117t-salient-b2-native-pilot-20261031-hourly11` is not touched. This new branch owns only a native runner, its tests, a native Actions workflow and scoped docs. No frozen Runtime/Cognition/Body/JEF/C3 or model/fixture edits.

Frozen disjoint six-case cohort **seed1061**, SHA256 `11d499eeb04d83e3786fe12046207ec3d0fc6684f5220a5fc1943202cd0f31de`, cases Atlas/Boreal/Cinder/Delta/Elm/Flux, oracle A/50, B/70, NONE/null, A/50, A/50, NONE/null. Reuse original `RUN117S_BODY_COMPLEMENTARITY_SEED1061.json` bytes. Three registered C3 arms, same common trusted SYSTEM contract, source data only in USER role, no typed JEF candidate or oracle in prompts:
- `RAW_FULL_SOURCES`: full two exact persisted USER texts (includes archive distractors).
- `SOURCE_SPANS_ONLY`: deterministic exact policy and option spans with SourceRefs (non-Body source selector baseline).
- `BODY_VERIFIED_QUOTES`: only exact source-verified B1/B2 quote spans; no full source, model hypothesis, typed JEF or answer.
Use fixed arm order rotated by row index mod 3; seed1061, temperature 0, 96 max C3 output tokens. Strict duplicate-key/JSON/choice/remaining scorer from Run47, offline after native outputs.

## Pinned native evidence prerequisites

Use existing Run113B/Run116 fixed source/model/runner pins, unchanged:
- B1_DETAIL LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf, revision `6767265158422fb8a19c62ceb45f16f05363615b`, SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`.
- B2_GIST Qwen3.5-0.8B-Q4_0.gguf, revision `8fea620810c4afa23dd6443f999a48574c1611a3`, SHA256 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`.
- C3_LANGUAGE LFM2.5-350M-QAD-Q4_0.gguf, revision `657e078c94084481950a2d555a941481f715536b`, SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`.
- llama-server runner SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`.
Use Run116 install procedure, source ZIP manifest and hash verification. GitHub Actions ubuntu-24.04, 45min job, existing native concurrency group `v13-native-c3-ag12-20261030`, no paid provisioning.

## Predeclared execution and failure semantics

For each real SQLite Store: prior B2 offer; current B1 offer; current B2 via default-OFF Run117S salient selector with explicit isolated opt-in. Expected up to **18 actual native Body calls** (B2 prior, B1 current, B2 current) and **18 native C3 calls** (6 × 3), serial, with actual_model/revision and process-reap receipts. Do not substitute synthetic QuoteBody for native evidence. C3 raw and deterministic-span controls are independent of Body quote success: if native Body quote selection is missing/wrong, record `BODY_VERIFIED_QUOTES` as unavailable, **still run raw and deterministic controls** for that case, and mark whole result `PARTIAL_BODY_QUOTE_RED`; never pretend full three-arm completion. Native model/runner/reap failure => `STRUCTURAL_RED`, preserve partial logs and all failed cases. Never rerun/alter frozen cohort to turn a RED into GREEN.

Predeclared exploratory signal only when **all 18 native C3 FINAL/reaped and all 18 Body offers FINAL/reaped**, with BODY strict score ≥ SOURCE_SPANS_ONLY+2, BODY ≥ RAW_FULL_SOURCES+1, and no false positive on Cinder/Flux NONE. Otherwise `NO_GAIN` (complete) or `PARTIAL_BODY_QUOTE_RED` (missing Body quotes). A 6-case exploratory signal does **not** promote STEP2, B3, Body-JEPA, `jepa_weight`, Age0 or whole-system completion. Body quote verification proves exact source transport only, never semantic correctness.

## Test plan and raw closure

1. Model-free frozen seed1061 preflight with real SQLite and synthetic QuoteBody must remain 6/6; 16 Run117S-R inherited adversarial tests PASS.
2. Native runner tests: fixture SHA tamper, arm names/order, no answer injection, strict score and fail-closed structural behavior (synthetic or static only; no false native claim).
3. Pinned Actions: package_source ZIP and full source manifest/hash, install models with deep verify, serialize 18 Body and 12–18 C3 calls, record per-call raw metrics/outputs, process reaps, no output/actions/learning, compile/privacy/diff. Upload artifact even on failure, include SHA256SUMS. Download original raw, verify ZIP CRC/inner hashes, privately back up before interpreting scores.

Next after original native result: independent blinded read-only score/provenance audit; no production merge until review. Runtime budget UNKNOWN.
