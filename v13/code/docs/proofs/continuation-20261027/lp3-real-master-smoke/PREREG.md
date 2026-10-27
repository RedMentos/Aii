# WP-LP3 first real C3 master compatibility smoke — preregistered 2026-10-27

**Independent NEW diagnostic cohort, not LP1/LP2/STEP2/BP2b and not a utility trial.** Parent LP3 prompt-only review exact `158e2546e9de93a117ca43a50b94d3adf670c07b`; review-only branch `codex/automation11-lp3-real-master-smoke-20261027`. Preregistered before the native Actions execution. No changes to any earlier seed, model, source hash, negative result or active Age rights.

## Exact source and reason

Official public `LiquidAI/LFM2.5-350M` at HF Git revision **`120bf032c36dd1273de754669da040dba7ad4982`**, `model.safetensors` expected SHA256 **`1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`** (matches archived LP2 source hash). License **LFM Open License 1.0**. Download only pinned public revision and metadata in isolated CPU Actions; verify full weight hash before loading. Do not silently substitute a new model or tokenizer revision. This is the HF FP32 source, not the Redmi Q4 C3 runtime.

## Frozen diagnostic procedure

- Deterministic seed 73, Torch CPU four threads, Transformers 5.20.2, Torch 2.14.1 CPU. Frozen base eval, trainable prompt-state predictor and 2-token soft prefix; all base weights remain `requires_grad=False`.
- Two **synthetic** distinct prompt/answer pairs: `What is the name of my cat?` → `Brombeer`; `Which city did I move to last year?` → `Tromso`. Chat-template prompt only; answer tokens never enter `prompt_features`. These examples are *not* LP2 heldout or new utility claims.
- Pre-optimizer: compare own vs shifted vs zero soft-prefix answer logits and target-free next-token logits; check finite values and shape; backpropagate teacher-forced answer CE through predictor and prefix projector with strictly positive finite gradient norms; base frozen.
- One AdamW step on trainable prefix parameters, learning rate 1e-3. Recheck base byte equality via SHA256 of a sampled frozen tensor (and frozen flags); no LoRA, JEPA or Body training. Bound output to diagnostic numeric receipts; no model/optimizer bytes uploaded.
- Run source verification, preflight, and a single native compatibility job serially. Preserve failure logs and exit codes; timeout is **FAIL**, not success. No unregistered second attempt after a failure without a new diagnostic note.

## Success / failure, fixed before execution

`LP3_REAL_MASTER_COMPAT_PASS` only if source SHA matches, HF model loads, prompt-only features work, both control deltas are finite and >1e-8, answer CE is finite, both trainable gradient norms are >0, frozen-base tensor unchanged, and target-free greedy returns 2 bounded tokens. Otherwise `LP3_REAL_MASTER_COMPAT_FAIL` with raw failure and no gate promotion. Passing does **not** establish LP3 utility, generalization, wrong-assignment benefit, JEPA, STEP2, B3, Age promotion or Redmi feasibility. Next separate study must preregister matched CE/own/shift and 5 known LP2 failures + new harder paraphrases, with retention/drift/near-miss and proper source hashes.
