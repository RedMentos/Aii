# HB1b C3 output-format/source-use diagnostic — preregistration BEFORE implementation (2026-10-29)

Owner: GPT-6 isolated review child of PR #1054 exact `cb36ffec3b56b1cb6a13bfcfb38b93fa6c90fc1b`. This is a **POSTHOC-MOTIVATED, PROSPECTIVELY PREREGISTERED FOLLOW-UP** to HB1a native result, not an independent confirmatory holdout. Original HB1a RAW/SCORE, cohort, seeds and model/source hashes remain immutable.

## Motivation, observed before this registration

HB1a [run 40836705747](https://github.com/RedMentos/Aii/actions/runs/40836705747) verified 54 Linux-native calls: six public synthetic tasks, C3-only 2/6 exact, both-exact 0/6, both-native 2/6. All 24 generated-offer-arm C3 outputs were `NONE`. It is unknown whether this reflects C3's actual source-use limitations, the restrictive JSON output format, or both. No general complementarity or foreign-source conclusion is justified.

## Fixed inputs and provenance

- Source fixture generator Git blob `329153aaa73df009fdc433523994e372e0fd2c95`, fixture SHA256 `73c9f4096a928ece659cfa5aff0c483001346834f6117765ed1c53c9c2b7939b`. Select exactly the six `family=5` rows as in HB1a. No new cohort, no claim of blindness.
- Original HB1a prereg Git blob `9d6652e99ac9aa0de7898f15eeb8a54d598c49e6`, source plan Git blob `033ea9c8c3e6f9ff631b84136afa1f74dd7e627c`, original closed raw SHA256 `abbcacec1217e51dfc592d2e981db9597162b475ca01886151fa99c39a1df7e1`, score SHA256 `b7ba7c038d420cba7bb78dc62cba0b66ed7d41b50c8f5e7b4f9f85e3697c3c44`. Parent artifact ID `12881321580`, run `40836705747`, ZIP SHA256 `7d180436ab64165f867a80902add7b23f8dae19cbbfd72b8b266ac48c47b4552`.
- Reconstruct model-facing exact/native source text from `hb1a.receiver_plan(rows, fixture_sha, parent_raw.body_rows)` after verifying parent raw source/identity/model hashes. Never use answer keys or raw fixture dictionaries in model prompts. `both_exact` and `both_native` source text must be identical across the format pair.
- C3 pinned public LiquidAI/LFM2.5-350M-GGUF revision `657e078c94084481950a2d555a941481f715536b`, GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, LFM Open License 1.0. Native llama-server b10964 SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`. No replacement model, adapter or training.

## Registered 24-call design

For each six-row task, exactly four C3 arms, fixed order:
1. `exact_schema`: HB1a both-exact messages and its strict JSON schema `{"action":"A|B|NONE|UNKNOWN"}` (replication).
2. `exact_plain`: **identical user source text**, system instruction changes only the final output-format sentence to require one plain token `A`, `B`, `NONE` or `UNKNOWN`, with **no JSON schema**.
3. `native_schema`: HB1a both-native messages and strict JSON schema (replication).
4. `native_plain`: identical both-native user source text, plain-token instruction, no JSON schema.

No oracle in prompts, no source label rewrite, no posthoc output repair. Parse schema arms only as a strict JSON object with one `action` enum field; plain arms only if `output.strip()` is **exactly** one of four uppercase tokens. Otherwise `UNPARSEABLE`. Never search explanatory prose for a convenient action.

Seed 13, temperature .1, threads 2, context 2048, max C3 output 48 tokens, per-call deadline 90s, overall cap 30min. Linux x86_64 CPU, fresh isolated home, Age0 RECORD_ONLY, latents OFF, jepa_weight=0, no adapters, tools or weight updates. One native runner, teardown, model/binary hash before/after, resource admission >=2.5GB available memory and >=3GB disk. Parent artifact must be independently SHA-verified before any call. Save original raw after every successful call and on RED, include inputs, outputs, timings/RSS, SHA256SUMS, failed attempts, exact-head CI.

## Questions, controls and claim limits

Primary descriptive outcomes: per-arm exact/wrong/unknown/unparseable counts; distribution of action labels, and paired differences plain-vs-schema for each source type. Secondary: native vs exact source effect under the same output format. The deterministic source parser is a non-model oracle/control and **not** counted as C3 competence. The 6 tasks are public and reused; no statistical significance or generalization claim, and the original HB1a score must not be modified. A positive result only motivates a separate independent held-out P0/P2 study.

All negative gates remain Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, V13 INCOMPLETE; Redmi unmeasured. No production merge. No user-private data in public evidence.
