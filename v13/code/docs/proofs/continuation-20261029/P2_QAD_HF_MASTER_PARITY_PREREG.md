# P2 / LP3 prerequisite: QAD GGUF ↔ HF master parity preregistration (2026-10-29)

Owner: GPT-6 isolated child of PR #1066 exact `a585b0185cfd2995ccb5a963bec66da9be3538d8`. Commit BEFORE implementing parity code, downloading a new HF master or training. This is a **source/weight correspondence test**, not a new learning result or permission to activate adapters. Original Canon and every model/cohort/seed hash unchanged.

## Motivation from verified negative STEP2 evidence

- P0X C3-only run `40840179920`: 50/150 exact, NONE 150/150, oracle headroom 100. P0X source-arm run `40841374171`: both-exact 52/150 (+2 vs baseline), B1-only 51, B2-only 50, foreign shuffled 50; preregistered +15 improvement threshold failed, no A output. Closed raw/score/receipt and private backup verified; STEP2 remains UTILITY_FAIL.
- Existing roadmap `v13/ROADMAP.md` blob `7e377bfa0e4bd06c8fbf13bab28e7a5b40f693eb` already records `LP1_NO_ATTRIBUTABLE_GAIN` and `LP2_ALIGNS_NO_GAIN`. LP3 requires answer to causally depend on predicted state, with shifted-target control; simple supervised C3 LoRA is only a separate baseline, not a substitute for JEPA LP3.
- Existing `v13/code/v13/lora_trainer.py` Git blob `49a752879ae5d19391963742a0f042e740edb2cc` has `LoraTrainer._load_gguf_weights`, `LlamaCppEvaluator`, `AdapterRegistry`, answer-only CE, KL anchors, and explicit AG6 approval. **Reuse**, do not redesign or create another live adapter path.

## Immutable pinned source and open prerequisite

- Deployed C3: LiquidAI `LFM2.5-350M-QAD-Q4_0.gguf`, revision `657e078c94084481950a2d555a941481f715536b`, SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`. Native llama-server b10964 SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`. License/provenance preserved from catalog.
- LiquidAI's official GGUF card https://huggingface.co/LiquidAI/LFM2.5-350M-GGUF distinguishes QAD Q4_0 from ordinary Q4_0 and identifies instruction `LiquidAI/LFM2.5-350M` as separate from pretrained `LFM2.5-350M-Base`. Transformers official LFM2 docs https://huggingface.co/docs/transformers/model_doc/lfm2 and PEFT https://huggingface.co/docs/transformers/peft show candidate training interfaces.
- **HF instruction master exact commit, config/tokenizer/safetensors SHA256 and license must be resolved and registered in a follow-up source-pin addendum BEFORE any download/training.** Do not infer that Base, instruction HF and QAD GGUF are weight-identical or adapter-compatible. No new paid provisioning or unpinned weights.

## Predeclared parity experiment, software first, then isolated native

1. Source-only inspect `_load_gguf_weights` tensor-name mapping and dequantization. Enumerate all HF master parameters and GGUF tensors, record matched/unmatched names, shapes, dtype/quant type, q/k RoPE layout and any tied embeddings. **Fail closed on unexplained missing or shape-mismatched trainable weights**; never accept `tensors_replaced>0` alone as complete mapping. Preserve all original negative attempts.
2. In fresh Linux x86_64 isolated home, pin and hash HF instruction master and QAD GGUF before/after. Construct (A) untouched HF instruction master, (B) HF architecture overwritten with dequantized QAD GGUF tensors using existing bridge, and (C) frozen native llama-server QAD. No adapters, no training, no weight activation. Use only the 30 P0X calibration rows or separate fixed public probes, **not** the 150 heldout answer keys. Preregister probe IDs, tokenizer template, decoding seed and comparison tolerances before any native inference.
3. Compare B vs C on identical prompts with greedy or strict fixed JSON schema, recording token IDs, top-1 agreement, logit/next-token distribution where native API permits, and output labels. Compare A vs B to quantify QAD distillation shift. Do not claim exact logit parity when llama-server cannot expose comparable logits; mark that subproof unavailable. Any discrepancy in tokenizer/template, tensor coverage or model identity is a RED prerequisite.
4. Only if mapping and parity are independently verified may a separate, default-off **P2 supervised C3 receiver baseline** be preregistered using new disjoint training data and existing `LoraTrainer`, `LlamaCppEvaluator`, `AdapterRegistry`. Keep `jepa_weight=0`, Age0 RECORD_ONLY, no AG6 approval bypass. Actual LP3 causal-state JEPA and B1/B2 learning remain separate required work.

## Gates and exact next work

Before implementation, fetch current heads/AGENTS/BUILD_STATE/ROADMAP and check other owners. Next: resolve and freeze exact HF instruction master provenance, then add source-only tensor-mapping audit tests on an isolated review branch; do not run a heavy native job concurrently with another owner. If source mapping fails, record RED and pursue independent Context OS/JEF/B1-B2 packages. No STEP2/B3/Body-JEPA/LP3/jepa_weight/Redmi/V13 promotion. Current status: **PREREG_ONLY_NO_NEW_MODEL_CALLS_NO_TRAINING**. Remaining platform budget UNKNOWN.
