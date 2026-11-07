# Mobile weight-learning research — 2026-11-07

This note supplements the full v10.16.1 Canon and later user decisions; it does
not replace B1/B2, C3, JEF, JEPA, the existing gates, or the current model pins.
No model, implementation, native runner, training job or device was changed
for this research.

## Existing evidence

`NATIVE_LFM2_TRAIN.md` describes actual Linux-native updates to selected C3
LFM2.5-350M `ffn_down` tensors and reports learned synthetic facts, but its
tested configurations did not pass the existing AG6 retention/leakage gate.
It is not evidence that B1/B2 learn, that JEPA improved a body, or that
training runs within the Redmi's actual memory, thermal and energy limits.

## Current primary sources

- [First-Order LoRA Training with Phone NPUs, v2](https://arxiv.org/abs/2610.24816v2)
  (preprint, 2026-10-26, accessed 2026-11-07): on newer Snapdragon devices the
  authors study splitting frozen-weight products onto an NPU while keeping
  adapters and optimizer on CPU. Their *four-example simulated precision study*
  for Qwen3.5-4B reports Q4 gradient error 98% versus FP32 and examines a
  mixed-precision policy. This does not establish the same result for V13's
  Qwen3.5-0.8B, LFM2, or Redmi. It motivates checking per-tensor gradients
  against FP32 and keeping a training master distinct from Q4 inference.
- [MobileFineTuner](https://github.com/Edge-Intelligence-Lab/MobileFineTuner/tree/086b1a027fe708d5eaca89b1ec2bf1a876fb80de)
  (source revision `086b1a027fe708d5eaca89b1ec2bf1a876fb80de`, accessed
  2026-11-07) declares Apache-2.0 and offers C++ LoRA plus synthetic Android
  entrypoints. Its documented architectures include Qwen2.5-0.5B, not verified
  support for V13's LFM2 or Qwen3.5 bodies. Its model files and tokenizer are
  separate assets. Treat it as an independent possible baseline; training,
  resource use, adapter exchange and Redmi compatibility remain unverified.
- [MobileRLHF](https://github.com/Edge-Intelligence-Lab/MobileRLHF)
  (accessed 2026-11-07) documents Android DPO/KTO paths using Hugging
  Face/SafeTensors assets. Its adapter output is not established as directly
  consumable by V13's GGUF/llama.cpp path. Any experiment needs a verified
  conversion and post-reload inference parity before considering a consumer.
- [MobileSpec / forward-only specialists](https://arxiv.org/abs/2611.04797)
  (preprint, 2026-11-03, accessed 2026-11-07) proposes trainable specialist
  parameters optimized using forward evaluations and verifiable outcomes.
  It is an optional comparative research arm, not evidence for V13 Body-JEPA,
  LFM2/Qwen3.5 support, a Redmi result, or full base-weight training. Check
  code availability, license and a real runner hook before implementation.

## Suggested bounded next experiment — not yet registered or run

Compare the existing native C3 baseline with one eligible `ffn_down` tensor
versus the previously tested broader tensor scope on *new disjoint* synthetic
training/held-out questions and fixed seeds. Register source, model, data,
optimizer, compute and gate before execution; keep prior failed runs intact.
Measure weight delta, exact and paraphrased learning, near-miss leakage,
retention, loss/gradient finiteness, restart and rollback, and Linux RSS/time.
If that shows a useful signal, separately measure the same supported path on
the Redmi, including peak RSS, temperature, latency and energy where available.
Do not retune the locked AG6 gate or use the result as proof of B1/B2 learning.
