# Run631 — native chat-template C3 LoRA utility: verified NO_GAIN

**Date:** 2026-10-27 UTC. Review PR #626, child of Run630 PR #625. Prereg `730825bbdeb2e8359f4a123a87ec8cad6d7c244d` before source/tests/CI. Actual native checkout `9ee3201237d1ce5dc0a7cc8a73b56262751f02b0`, GitHub Actions **40425890810 SUCCESS** job 121931424674. No source/model/seed/cohort/weights changed from Run629/630.

## Exact closed evidence

All eight CI stages exited 0: source controls **14/14 PASS** (new Run631 6 plus Run630 8), adapter ZIP and GGUF hash, b10964 source and Linux binary hash, isolated pinned dependencies, official SmolLM2 master hash, actual F16 GGUF conversion, native llama-server base/scale0/scale1, and public-repo privacy scan CLEAN. Raw artifact 12699089381 ZIP SHA256 `a3b7f6c7738aabab90df369ee524ac853146ccb637b076b169060485b3418834`, **26/26 internal SHA256 PASS**. Private backup `/V13-Checkpoints/2026-10-27/Run631/Run631-chat-native-40425890810.zip`, byte-identical Library roundtrip PASS.

Exact HF SmolLM2-135M-Instruct revision `12fd25f77366fa6b3b4b768ec3050bf629380bac`, master SHA256 `5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c`, original Run629 LoRA GGUF SHA256 `e2f84ae657b0b90891d7c5c042a897b9bd30021f8a16e399a27fa2704b793f4b`, original b10964 server SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`. Exact tokenizer `apply_chat_template` used; **6/6 HF/native token-ID parity PASS**, 35–43 tokens per prompt; **6/6 base-vs-LoRA-scale0 first-token top64 and full generated-text parity PASS**. Scale1 changed first-token logprobs by max |Δ logp| `0.20013, 0.20490, 0.17065, 0.09440, 0.18938, 0.21870` across six prompts. Native adapter genuinely affects the distribution.

## Negative semantic result, no retuning

Fixed preregistered synthetic **train 0/2 base → 0/2 candidate**: no `amber` or `47` learned in the answer. **Heldout 1/2 → 1/2**: greeting passed, arithmetic 2+2 did not contain expected `4` in either. **Near-miss leaks 0/2 → 0/2** for Cedar protocol. `bounded_synthetic_utility=false`, status `NO_ANSWER_UTILITY`. Some wording changed, but the answer keys did not improve. This is not evidence of general learning, and no additional hyperparameter/label tuning is authorized on this frozen cohort.

This closes the earlier Run630 raw-prompt EOS/newline limitation with actual 32-token chat outputs and tokenizer parity. It remains a **Linux-native SmolLM2 F16 reference**, not the currently deployed `LiquidAI/LFM2.5-350M-GGUF` QAD Q4_0 C3, nor B1/B2, JEPA or Redmi. Run629's original 2-step master recall 0.0 remains consistent.

All negative gates unchanged: STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, Redmi `UNMEASURED`, V13 `INCOMPLETE`, production weight authority 0. No autonomous learning, phone performance, semantic utility or AGI claim. Original Run628/630 RED and GREEN artifacts remain retained.

**Next exact package:** independently preregister actual current C3 `LiquidAI/LFM2.5-350M` licensed master pinned to immutable revision and verified safetensors hash, match it to deployed GGUF identity before authority, run bounded native CPU LoRA gradient/export with frozen synthetic train/heldout and honest zero-gain outcomes; then Q4 LoRA compatibility/retention, B1/B2 sparse training and Body-JEPA. Do not replace or activate current C3 from this experiment.
