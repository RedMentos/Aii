# P2 QAD FP32 ↔ GGUF first-token native independent result — 2026-10-29

Owner: GPT-6 isolated review, PR #1070. Original prospective first-token model-forward prereg in parent #1069, separate independent raw-audit prereg commit `ab223d25443224ab85e4920ecc9f4cd81d689147` before reading model results. **No training, no production merge, no gate promotion.**

## Exact native evidence

- Native Actions [40851408574](https://github.com/RedMentos/Aii/actions/runs/40851408574) at exact source `d101aec5000e2e45fbe1b7da25475d1244c8cece`: workflow GREEN. Original artifact ID `12887870364`, original ZIP SHA256 **`2cb67b8dc3a861d821e75b0dfab4a56cd2f1a046a9e36ce0929197648c1d1633`**.
- Independently downloaded and checked ZIP CRC CLEAN, **30/30** SHA256SUMS, no duplicate entries, **13/13** stage exits zero, privacy CLEAN, 6/6 model/config/tokenizer/template/GGUF hash receipts, 1/1 pinned llama.cpp runtime hash receipt, loopback server log and teardown. Original artifact is byte-identical after permitted private Library upload/re-materialization at `/V13/RawEvidence/2026-10-29/P2-firsttoken/GREEN_40851408574_sha2CB67B8D.zip`.
- All eight fixed non-heldout prompt input token-ID arrays exactly match the separately verified tokenizer-only run [40850029535](https://github.com/RedMentos/Aii/actions/runs/40850029535) original ZIP SHA `fff6a6477090166176b71674ef593d1954966b5cbb685723054cd1b230c8e342`; 8/8 HF FP32 forward calls and 8/8 GGUF one-token calls. No P0X holdout used. No adapter or optimizer.
- Independently recomputed from original `RESULT.json`: **3/8** HF argmax vs *generated* GGUF token IDs equal; **7/8** HF argmax vs **first GGUF top-logprob ID** equal; total top-5 intersection **28/40**. Both counts are descriptive only; not a preregistered parity threshold. Original result `top1_equal_count=3` is generated-token equality, **not** the raw top-logprob argmax comparison.
- **Critical sampling confound:** In five of eight rows, GGUF *generated* token differs from its own top-logprob first ID. All five GGUF top-logprob first IDs are token `7`; the registered request explicitly set `ignore_eos:true`. This is consistent with an EOS-suppression/sampling intervention, but the identity and exact sampler behavior must be verified rather than inferred. Consequently **3/8 generated agreement cannot be attributed to weight/quantization mismatch**. The 7/8 raw-top-logprob observation also does not establish full logit/greedy parity or RoPE/cache parity.
- Original dependency-only REDs retained unchanged: run `40850998235` ZIP `bc900460...` (tokenizers resolver), run `40851169183` ZIP `56f16af2...` (safetensors resolver), both zero model forwards. Both original RED ZIPs and tokenizer ZIP are byte-identically backed up in the same private Library folder.

## Registered next causal control

Before a new model call, preregister a separate **GGUF-only** eight-prompt `ignore_eos:false` control on the exact same pinned GGUF/runtime, integer input IDs, one-token greedy parameters, with original FP32 first-token raw frozen as comparison. No P0X use, no HF repeat, no model/seed/cohort swap. Compare GGUF generated ID, GGUF top-logprob first ID, original HF argmax, and original GGUF ignore-eos:true generated ID; keep original artifacts. This is a narrow diagnostic, not a utility gate. If no clean source/memory/runtime prerequisites, record blocker and continue independent JEF/Context OS/World/JEPA/Dream work.

## Unchanged binding gates

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi unmeasured; V13 INCOMPLETE. Native Linux evidence is not Redmi acceptance. Remaining platform budget UNKNOWN.
