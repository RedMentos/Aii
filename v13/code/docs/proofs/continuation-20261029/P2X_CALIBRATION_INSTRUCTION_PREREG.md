# P2X C3 explicit source-instruction calibration — prospective preregistration (2026-10-29)

Owner: GPT-6 independent diagnostic; exact parent PR #1078 head `f8e05e6245fa8c221a89babacc41cd7b76668c23`. **This file is committed before any new implementation, native calls, or inspection of calibration model outputs.** No production merge, training, adapter, AG6 activation, or frozen P2X validation input modification.

## Motivation and frozen scope

PR #1078 verified 360 base-only native calls with the original *single-user-message + JSON grammar* view. All 72 `both_exact` calls returned NONE, and the 24/72 exact answers were exactly the NONE oracles. This result is NEGATIVE; it does not identify whether an explicit source-use instruction could improve the behavior.

This diagnostic uses **only the 36 calibration rows** from the existing P2X fixture, never the 72 frozen validation rows, 252 training rows, or P0X holdout. Generator Git blob `8135fa2792df2c541dc1719e49d941c775703697`, seed `2026102921`, full fixture SHA256 `cd3edfdb464c6f99650b1ea32b5b09854268f0b53faa79df22ddcd135f21985a`. Do not change generator, partition, project IDs, source text, or oracle.

## One-factor comparison (360 serial calls)

For each calibration ID sorted lexically, run all five source views in the generator's order `c3_only,b1_only,b2_only,both_exact,shuffled`, once per format in order `original,instructed` (36 x 5 x 2 = 360). Same QAD C3 base GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, same llama.cpp b10964 archive SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`, extracted server SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`, seed 13, temperature .1, c3_sampling off, 2048 context, 2 threads, max 48 output tokens, exact `hb1a_two_body_native_pilot.C3_SCHEMA` constrained JSON, no adapter, no system prompt in original arm.

The **only change** in instructed arm is an added system message, verbatim:

> Return only a JSON object with action A, B, NONE, or UNKNOWN. Use source facts only for the exact project ID in the current request. If the B1 option sheet or B2 archived policy is missing, foreign, or inconsistent, return UNKNOWN. When both matching sources exist, an option qualifies if its first value is at most the policy maximum first, its second value is at most the policy maximum second, and its flag is true when the policy requires it. Choose the qualifying option with the smallest first value, then smallest second value, then A before B. If neither qualifies, return NONE. Never invent source facts.

The original single user message is byte-identical across formats. Do not insert hidden oracle/answer keys, change grammar, inject a demonstration, add anti-echo sampling, or silently drop failed calls. The system message is task instruction, not an observed model-learning effect.

## Raw evidence, scoring, gates

Precompute a canonical SHA256 for every exact `messages` array and record it per call; include ID, source arm, format, model/runtime/binary hashes, explicit null adapter, seed, FINAL status, one native call, output, finite duration, and original process metrics. Require exactly 360 unique ordered triples and fail closed on mismatch, duplicates, foreign IDs, missing source, non-FINAL output, nonzero stage exits, runner leak, source changes or resource failure. Preserve RED attempts and original raw before retries. Require independent raw replay and CRC/SHA256SUMS plus exact source Git blobs; do not publish model weights, private data or personal records.

Oracle for `both_exact` is existing calibration `oracle_action` (12 A, 12 B, 12 NONE); for all four other source views expected UNKNOWN. Report per-format/per-arm exact, wrong committed, UNKNOWN, unparseable and output-label distribution; paired ID-level changes and A/B/NONE discrimination. **Descriptive, no acceptance threshold**, no STEP2 promotion, no training decision from 36 public synthetic calibration rows. Native execution is Linux x86_64 evidence, never Redmi. No new model calls until the preregistration commit and source-only tests are remotely verified.

Keep Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight 0; AG6 unapproved; Redmi unmeasured; V13 INCOMPLETE. The original P2X 72-ID validation result remains frozen and negative.

Next: implement default-off plan + strict raw scorer and adversarial tests, verify remote source-only CI, then check heavy native owner and run serial native only if available. If native is blocked, checkpoint and continue another independent Canon package. Remaining platform budget UNKNOWN.
