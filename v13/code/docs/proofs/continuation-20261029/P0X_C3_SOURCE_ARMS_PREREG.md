# P0X 150-row C3 exact-source/ablation native follow-up — preregistration (2026-10-29)

Owner: GPT-6 isolated child of PR #1060 exact `577366b0059d8367f5c5446afc62b0d524d35768`. This registration is committed **before observing the P0X C3-only native baseline result** (run `40840179920` still in progress at registration). No model calls for this follow-up before source-only tests, frozen source pins and a verified baseline with oracle headroom >=15/150.

## Fixed source and provenance

- Original prospective P0X source prereg Git blob `312f8cb0acd591fe9c17a3e87a299f21d92465fd`, generator Git blob `7ec4e877ad5ea3eed1c60102dac3baa15391dd2b`, seed `2026102907`, external fixture SHA256 `ab03aba600e8085b02247657cc5fb718195e89a83641ef69ad006a27c776647e`, registration blob `e85b0d636c75d6c6cf0cdd7f45a18609c2c4b04b`. Exactly 150 heldout tasks, no calibration rows or new seed.
- C3-only baseline prereg blob `0a3ab620497299f9580357e858a04db5b20d1b5f`, model C3 LiquidAI/LFM2.5-350M GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, llama-server SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`. No replacement model, adapter or training.
- Model-facing source texts are taken **unchanged** from `p0x.model_inputs(rows)` for the same task IDs, with `hb1a.C3_SYSTEM` and strict JSON action schema `A|B|NONE|UNKNOWN` identical to the C3-only baseline. Never include oracle/answer key or family/sheet/rule fields. Foreign B1 retains its original project identity.

## Registered 600-call design

For each of the 150 heldout tasks in original generator order, four C3 arms:
1. `b1_only`: current + exact B1 option sheet, no B2 policy.
2. `b2_only`: current + exact B2 policy, no B1 sheet.
3. `both_exact`: current + exact B2 policy and exact B1 option sheet.
4. `shuffled`: current + exact B2 policy and a foreign B1 sheet with original foreign project header.

Total **600 new C3 calls**, serial; compare against 150 previously measured C3-only calls (do not rerun/rewrite baseline). Seed 13, temperature 0.1, top_k 50, repeat_penalty 1.05, threads 2, context 2048, max 48 output tokens, `c3_sampling="off"`, strict JSON action parser, 90s per-call deadline, 45min overall cap. Linux x86_64 CPU, fresh isolated home, >=2.5GB available memory and >=3GB disk, Age0 RECORD_ONLY, no adapters/tools/latents, jepa_weight=0. Preserve per-call original raw, partial RED attempts, input/model/runner SHA before/after, independent verifier and process teardown.

## Registered outcomes and interpretation

- Per arm: exact, wrong_committed, unknown, unparseable; output action distribution and per-task paired differences. Compare `both_exact` exact to the **frozen C3-only baseline** exact on identical task IDs; preregister descriptive improvement threshold >=15/150 correct, and require both-exact to outperform each single-source arm. Track shuffled wrong commitments explicitly; a high shuffled false-commit rate is a failure even if exact improves.
- **Do not start** the 600-call native run if the independent C3-only baseline is RED, hash-inconsistent, missing, or its oracle headroom is <15. No baseline posthoc reweighting or prompt tuning.
- A positive result is only a source-dependence diagnostic on public synthetic data, not a blind independent real-world test, not proof of B1/B2 **generated** offer utility, JEPA learning, B3 latents, Redmi readiness or STEP2 promotion. A negative result motivates P2 default-off C3 receiver learning with new train/holdout separation, not changing the original score.

All gates remain Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, V13 INCOMPLETE; Redmi unmeasured. No production merge or private user data in public evidence.
