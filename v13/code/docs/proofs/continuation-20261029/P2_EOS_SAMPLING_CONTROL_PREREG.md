# P2 native GGUF EOS-sampling confound control — preregistration 2026-10-29

**Prospective follow-up** to the independently verified first-token native result in PR #1070 at exact parent `9be1c524d1ab813be97b80873b0ba223372f7fd0`. Commit this registration **before** implementing or running any new model calls. This is a diagnostic of the previously observed native generated-token vs top-logprob discrepancy, not a parity gate or new P0X cohort.

## Frozen evidence and causal hypothesis

Original first-token native [run 40851408574](https://github.com/RedMentos/Aii/actions/runs/40851408574), exact execution head `d101aec5000e2e45fbe1b7da25475d1244c8cece`, artifact `12887870364`, original ZIP SHA256 `2cb67b8dc3a861d821e75b0dfab4a56cd2f1a046a9e36ce0929197648c1d1633`, original `RESULT.json` SHA256 **`1df95bff7c78635ae3f5bce13e58d30182610e8a7978ab6afaabfa327e750a23`**. Eight pinned non-heldout prompts; eight HF FP32 forwards and GGUF one-token generations, 8/8 source token IDs identical. HF argmax vs GGUF generated 3/8; HF argmax vs GGUF top-logprob first ID 7/8; 5/8 GGUF generated != its own top-logprob first ID (in all five top-logprob first ID=7). Original `ignore_eos:true` may suppress the preferred token; this is a **hypothesis**, not a proven token identity or source of all mismatch.

## Exact one-factor control

- Fetch **original ZIP** from GitHub Actions with read-only scoped token; require exact ZIP and `RESULT.json` SHA256 before any new call. Never modify or overwrite original raw. No private user data or paid provisioning.
- Download only pinned deployed QAD GGUF `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d` and pinned llama.cpp b10964 Linux archive `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`; verify bytes first.
- Use **exact same eight integer input-ID arrays**, order, endpoint `127.0.0.1:8080/completion`, `n_predict=1`, `temperature=0`, `n_probs=5`, `stream=false`, `cache_prompt=false`, `repeat_penalty=1.0`, `top_k=0`, `top_p=1.0`, `min_p=0.0`; change **only** `ignore_eos:false`. No new HF forwards, no adapter, no training, no P0X holdout.
- Record each original HF argmax, original GGUF generated and top-logprob first, control GGUF generated and top-logprob first, and recomputed counts. No posthoc agreement threshold: **0–8** control matches are descriptive. A source/hash/runtime/row/exit error is RED and retained. Require 8 bounded native calls, raw logs, source receipts, process teardown, ZIP CRC and SHA256SUMS before describing the result.
- Keep independent review branch-scoped; no Canon/runtime default modification, no Age authority, no AG6 activation. If original `ignore_eos:true` caused sampling confound, generated-vs-toplogprob disagreements should decrease, but this is a **testable expectation**, not a gate or a guaranteed result. Even perfect equality does not establish full logits, RoPE/cache, adapter transfer or utility.

## All binding negative gates unchanged

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi unmeasured; V13 INCOMPLETE; no production merge. Continue disjoint P2X receiver training/Context OS/JEF/World/Dream work after this narrow control.
