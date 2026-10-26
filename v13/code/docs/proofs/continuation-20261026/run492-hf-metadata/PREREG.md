# Run492 — pinned public Hugging Face model metadata preflight (before network check)

**Date:** 2026-10-26. **Base:** Run491 checkpoint `534bfe43d0412b913ddc412a12f17f18d066bb03`. **Scope:** primary-source metadata only; no GGUF download, inference, native execution, license acceptance, paid provisioning or gate promotion.

Exact frozen inputs from original Run479 `models.json` and installed native receipt:

| Role | Model repository | Exact revision | File | Size bytes | File SHA256 | Declared license |
|---|---|---|---|---:|---|---|
| B1_DETAIL | LiquidAI/LFM2.5-1.2B-Instruct-GGUF | 6767265158422fb8a19c62ceb45f16f05363615b | LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf | 695755488 | bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1 | lfm1.0 |
| B2_GIST | ggml-org/Qwen3.5-0.8B-GGUF | 8fea620810c4afa23dd6443f999a48574c1611a3 | Qwen3.5-0.8B-Q4_0.gguf | 563036064 | 57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf | apache-2.0 |
| C3_LANGUAGE | LiquidAI/LFM2.5-350M-GGUF | 657e078c94084481950a2d555a941481f715536b | LFM2.5-350M-QAD-Q4_0.gguf | 219312832 | 3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d | lfm1.0 |

Source: Hugging Face official API `/api/models/<repo>/revision/<40-char-revision>?blobs=true`; require exact repo/revision, public and ungated, exact sibling path, LFS SHA256, size and license metadata. Missing metadata, drift or changed license must fail closed. No guessing, no accepting a similar file, no fallback to HEAD content-length as proof of SHA256. Capture the exact response SHA256 and a sanitized validation receipt; do not persist credentials or model bytes.

The runner binary `llama-server` b10964 SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39` and native libraries still require **separate byte-level** preflight. LFM Open License 1.0 terms must be preserved; this check does not imply the user accepted a license. If a model is gated or unavailable, record the blocker and continue independent blueprint work.

Run491 frozen fixture SHA256 `c434a5765ed85b7c51022c5aaea0ba4c3150ef0f1490f466b4a8833e41b44c63` and seeds 31/32/33 remain unchanged. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight 0, Redmi unmeasured, Age0 unchanged.
