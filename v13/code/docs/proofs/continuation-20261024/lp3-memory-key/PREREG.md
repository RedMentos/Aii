# WP-LP3 memory-key candidate — preregistration (2026-10-24)

**Status:** REGISTERED SOFTWARE CANDIDATE, **not run on native master**. Isolated package owner: Codex/GPT. No runtime edits, no active cohort mutation, no authority, no model/organ substitutions. Parent: `codex/continuation-20261024` at `6c0ae186e0b612dc4118ef9fc60be90882bfe569` (Claude PR #38 base `cb959052433e01c29afc007e02b93aef373deb7f`). Separate from PR #42 organ/phone/train-runner repairs and all parallel Claude owners.

## Question and rationale

LP2 demonstrated alignment without response utility (`LP2_ALIGNS_NO_GAIN`): its predictor was not on the response path. LP3 tests a **separate explicit latent-key consumer**: a learned query vector selects a stored answer text from a frozen answer-state bank. This is not C3 language generation, not LoRA, not a Body-JEPA implementation, not proof of general semantic learning. A successful experiment only warrants a follow-up coupled-path trial; STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, and `jepa_weight=0` remain.

## Fixed protocol before any master execution

- Source: frozen local HF fp32 `LiquidAI/LFM2.5-350M` (same family as LP2), local-only, full SHA256 of `model.safetensors` supplied at CLI; no downloads, no GGUF substitution. Prompt states use the *same user chat template* as the existing `LoraTrainer._encode`; target states use the mean of the base hidden states of target answer tokens. Model and target bank are frozen. No EMA is claimed for a frozen bank.
- Facts: the **same 16 fictional facts** in LP2; 16 prompt states trained against the 16 frozen answer states. Held-out tasks: LP2's 32 previously fixed paraphrases (including the five historical misses) plus 16 newly written harder paraphrases in `HARDER` (48 per seed). These tasks are never used for optimization. Negative near-miss set is LP2's fixed `NEAR_MISS`.
- Predictor: residual `h + MLP(LayerNorm(h))`, hidden 256, GELU, last linear zero-initialized. Fixed InfoNCE temperature 0.1, AdamW lr 0.001, exactly 30 full-batch steps, seeds 31, 37, 41, 43. No LoRA/CE; **not equal-budget comparable to LP2**. `NCE_OK` maps k→k, `NCE_SHUF` trains k→(k+1) mod 16.
- Consumer: cosine top-1 over fixed bank; output is the **stored answer text** bound to selected memory ID. Abstain if cosine < 0.35 or top1−top2 ≤ 0.03 or zero query. The five arms use identical bank/texts: `raw` (no predictor), `predicted` (correct predictor), `wrong_trained` (shift-trained predictor), `value_shift` (correct predictor but cyclically shifted *value binding only*), and `zero_intervention` (predicted state zeroed, must abstain). Shuffling bank *and* value pairs would be a false control and is forbidden.
- Measures: per-question exact stored-answer selection, abstentions, near-miss nonabstentions (all are unsafe false retrievals), NCE losses, full predictions. Preserve each seed as immutable, fsynced JSON and a source/model-bound run manifest. Interrupted completed seeds remain; do not silently resume or overwrite a registered attempt. Recompute aggregate counts from raw predictions.

## Decision rule

`LP3_MEMORY_KEY_CANDIDATE_SUPPORTED_ONLY` iff at least 3/4 seeds show ≥4 additional correct answers out of 48 vs `raw`, and at least 3/4 seeds show ≥8 more correct vs **both** `wrong_trained` and `value_shift`, and in every seed near-miss nonabstentions increase by at most 2 vs raw. Otherwise `LP3_MEMORY_KEY_NOT_SUPPORTED`. An incomplete or unverifiable run is `LP3_INCOMPLETE` or invalid, never PASS. No automatic gate promotion or runtime switch under any result.

## Required evidence / limitations

Before native run, independently confirm exact local HF master/tokenizer, available RAM, current native jobs, and source hash. If absent, report `HARD_BLOCKER` and do not fabricate results. Report is Linux fp32 **memory lookup only**. The next coupled trial must compare actual generated answers at matched inference/learning budgets, negative transfers, restart/persistence, near-miss abstention and Redmi constraints. Do not use these synthetic toy tests as native evidence.
