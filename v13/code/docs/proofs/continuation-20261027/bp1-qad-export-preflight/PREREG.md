# BP1 QAD native LoRA GGUF export compatibility — pinned source prereg (2026-10-27)

Owner: GPT-6 independent, review-only branch `codex/gpt6-bp1-gguf-b10964-export-preflight-20261027`, parent `f6d6812a493cc7d2235e97bf16e0324242d1ecd6` (BP1 QAD LoRA V2). Do not change frozen runtime, active cohorts, models, training data, seed or gates.

**Observed genuine native RED:** Actions `40476209086`, source `18130b4b663705aed167fcf7b052a6eb6e38831e`, performed real QAD 25-row FP32 optimizer path but failed during `LoraTrainer._export` with `Unavailable: Unbekannte GGUF-Architektur: lfm2`; isolated `gguf==0.16.3` lacks LFM2 mapping. No adapter export, no accepted train proof. Preserve original RED.

**Prospective source choice:** Existing verified inference runner is llama.cpp **b10964**. Its Git tag `b10964` resolves to full immutable source commit `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4` (GitHub REST GET tag and commit, 2026-10-27). Official pinned `gguf-py/gguf/constants.py` includes `MODEL_ARCH.LFM2` -> `lfm2`, and tensor map includes `model.layers.{bid}.self_attn.v_proj` and `model.layers.{bid}.self_attn.out_proj`. License/source is the upstream ggml-org/llama.cpp repository. This is source inspection, not executed compatibility.

**Registered preflight:** In isolated Ubuntu Python venv install `numpy==2.2.6` and the `gguf-py` package from an exact checkout of `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`. Verify checkout SHA and installed module path. Without model weights, instantiate LFM2 GGUFWriter, map two official HF LoRA module names, emit synthetic A/B tensors and a GGUF v3 adapter, read it back and verify 4 tensor names/shapes and LoRA metadata. Negative tests: reject old/unknown architecture, wrong checkout, missing mappings, mismatched A/B shapes and non-adapter metadata. Record source, dependency, exit codes and raw bytes. **Synthetic GGUF is not a trained adapter or native inference proof.**

If software GREEN, next separate package changes only the isolated native train dependency to the verified pinned `gguf-py` source, then reruns serial genuine 25-row train with original model/train/seed hashes and audits export + original raw. Do not modify `v13/code/v13/lora_trainer.py` in frozen SourceHandoff. Do not run a second heavy owner concurrently. Do not upload adapter weights to public artifacts.

STEP2 UTILITY_FAIL, B3 L1_FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Redmi unmeasured, full V13 incomplete.
