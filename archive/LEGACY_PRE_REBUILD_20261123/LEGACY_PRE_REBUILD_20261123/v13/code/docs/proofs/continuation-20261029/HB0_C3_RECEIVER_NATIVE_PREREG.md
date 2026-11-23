# HB0c / P0-P2 C3 exact-source receiver Linux-native pilot — preregistration

Date: 2026-10-29. Parent: `b03d81f87d931a4f5917efaf3cb2323f893c586e` (HB0b PR #1048). Owner: V13 automation. This registration is committed before any native pilot execution or code. Branch-only and default-off. Do not edit any original registered STEP2/LP/B3 cohort.

## Question

Can the current pinned C3_LANGUAGE native consumer use the two **exact, source-authenticated** fields (rules + supplier sheet) better than it can answer a current request with no fields? Is its answer stable when the same exact evidence is packed into one body, and does it resist a foreign B1 sheet? This tests C3 source consumption, NOT genuine B1/B2 generated offers or joint learning.

## Frozen design

- Source: HB0 150-row public synthetic structural cohort from parent #1047, with exact externally verified canonical fixture SHA256 to be supplied as a required argument. Source code Git blob `329153aaa73df009fdc433523994e372e0fd2c95`; six-arm exporter source blob `8d6f5b9f0830540d2de72cc624778ff03e7b90ec`. Neither may change during the pilot.
- Pilot family: `family=5`, all six 2x3 counterfactual rows. Arms: `c3_only`, `both_exact`, `single_body_dual`, `shuffled_b1`. Exactly 24 paired native generations in fixed row/arm order.
- Model: existing pinned catalog C3_LANGUAGE LFM2.5-350M QAD, exact revision `657e078c94084481950a2d555a941481f715536b`, GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`. Install with existing `run93_source_c3_native_e2e.install` / pinned bootstrap; never alter model bytes or catalog.
- Linux x86_64 only, fresh isolated V13_HOME, Age0 RECORD_ONLY, jepa_weight=0, latents off, no learning or tools. Single native runner process, no concurrent heavy jobs on same host, CPU-only. Fixed seed=13, max output tokens=64, per-request deadline=75 s, bounded overall time 30 min. C3 runs one request at a time, reusing the same pinned runner. All process teardown and model/binary hashes checked.
- The native model sees only allowlisted `messages` from HB0b. No oracle, family/sheet/rule index or answer key in prompts. Oracle action is joined by opaque ID only after all native outputs are closed. Model output remains raw; a deterministic answer-action parser is a separate scoring control.
- Required raw: registration/source/model/binary hashes, all 24 input-message SHA256, raw output text, token/prefill/latency/RSS telemetry, seed/settings, exact output status, parse result, oracle only in posthoc score, model hash after run, teardown evidence, SHA256SUMS and failed attempts. Privacy scan. Never publish private prompts or weights.

## Acceptance / negative controls

1. All 24 row-arm keys exactly once; 6 unique opaque project IDs; model/runner bytes unchanged; no answer key in native input.
2. `both_exact` and `single_body_dual` include identical source facts but different packaging; `shuffled_b1` has a foreign project header. C3-only has no rule/option values.
3. Report per-arm exact, wrong committed, UNKNOWN/unparseable and latency without interpreting a native answer as true merely because it is fluent. No fixed minimum success threshold for this exploratory pilot; failed answers remain raw.
4. Test refusal for missing external SHA, model/source mismatch, duplicate/missing arm, oracle contamination, nonfinite metrics and non-Linux execution. Synthetic/mock unit tests are not native evidence.
5. If download, cgroup, binary, runtime or owner preflight fails, retain closed RED and do not fabricate native results.

## Non-promotion

This public synthetic six-row exploratory pilot is not a blind heldout, not B1/B2 native-generated complementarity, not the 150-row P0 oracle-vs-C3 headroom criterion, not a C3 LoRA learning result, not Redmi evidence, not STEP2 or B3 acceptance. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, V13 INCOMPLETE.

Next: only if exact-head native evidence is complete, design a fresh independent nonpublic 150-row cohort with a real C3-alone baseline, B1/B2 generated offers, one-body two-timescales, shuffled-source controls, confidence intervals and owner-serialized native execution.
