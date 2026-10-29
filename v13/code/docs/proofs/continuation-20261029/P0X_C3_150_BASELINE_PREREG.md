# P0X C3-only 150-row Linux-native baseline — prospective preregistration (2026-10-29)

Owner: GPT-6 isolated child of PR #1058 exact `cd2d1d76c08a8b4f09f83b99d33e8effab140d26`. Commit this BEFORE baseline code/native inference. This is a model-native **headroom check**, not a STEP2/JEPA/Redmi proof.

## Immutable source/model inputs

- P0X original prospective cohort prereg Git blob `312f8cb0acd591fe9c17a3e87a299f21d92465fd`, generator blob `7ec4e877ad5ea3eed1c60102dac3baa15391dd2b`, seed `2026102907`, external fixture SHA256 `ab03aba600e8085b02247657cc5fb718195e89a83641ef69ad006a27c776647e`, external registration blob `e85b0d636c75d6c6cf0cdd7f45a18609c2c4b04b`. Original source-only CI run `40839417533`, exact head `9cd2a432193232d9ee807f26604bda1efd323d45`, artifact `12881818398`, ZIP SHA256 `4a6d00bb7a5adc849a5cf9d795805b1f4ca210745585ed932769f13b793a56dc`.
- Use **only 150 P0X `holdout` rows** and `c3_only` view from `p0x.model_inputs(rows)`, original generator order. Never include calibration rows, B1/B2 sources, oracle/action key, family/sheet/rule indices or serialized fixture in model-facing input. Verify external fixture SHA and exact source blobs before any model call.
- Frozen C3_LANGUAGE LiquidAI/LFM2.5-350M-GGUF revision `657e078c94084481950a2d555a941481f715536b`, GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, LFM Open License 1.0. llama-server b10964 SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`. No other model download.

## Fixed 150-call protocol

- Each model-facing message is `[{"role":"system","content":hb1a.C3_SYSTEM},{"role":"user","content":P0X_current_only_view}]`; same C3_SYSTEM and strict JSON action schema from frozen HB1a source blob `033ea9c8c3e6f9ff631b84136afa1f74dd7e627c`. JSON schema action enum `A|B|NONE|UNKNOWN`. Strict parse: exact one-field JSON action object, no fallback prose extraction. No oracle in prompt.
- Serial 150 C3 calls, seed 13, temperature 0.1, top_k 50, repeat_penalty 1.05, threads 2, context 2048, max 48 tokens, `c3_sampling="off"` (schema arms do not use anti-echo), per-call 90s, overall 28min. Linux x86_64 CPU, fresh isolated home, >=2.5GB MemAvailable and >=3GB disk, no active adapters/tools/latents, Age0 RECORD_ONLY, jepa_weight=0, no training. Process teardown and model/binary SHA before/after required.
- Original closed raw after **every** call and on any RED; independently recompute strict score, source identity, output hash and receipt. Save exact-head workflow/parent evidence/inputs/outputs/timings/RSS/SHA256SUMS, no weights or user-private data. Preserve all failed attempts.
- Predeclared score: `exact`, `wrong_committed`, `unknown`, `unparseable`, output label distribution, and `oracle_headroom=150-exact` (oracle software control has 150/150 by construction). Require `oracle_headroom>=15` to justify proceeding to a separate native source-complementarity experiment. If headroom smaller, record `P0X_NO_HEADROOM`; do not silently alter cohort, seed or schema.

## Limits and next

A C3-only baseline cannot prove B1/B2 complementarity. Public synthetic heldout is not blind external data. No promotion of STEP2, B3, Body-JEPA, LP3, jepa_weight or V13 completion; Redmi remains unmeasured. Next after verified baseline: independently preregister both-exact and B1/B2-generated-source native arms plus foreign/shuffled controls, then P2 default-off C3 receiver training only after true heldout separation and headroom checks. No production merge.
