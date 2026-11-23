# STEP2 native model pins — current catalog versus unregistered alternatives (2026-10-28)

**Correction:** the authoritative `v13/code/specs/models.json` has already evolved beyond the historical Redmi Age-0 two-same-weight setup. It currently specifies **B1 1.2B QAD, B2 Qwen3.5-0.8B, C3 LFM2.5-350M QAD**. The earlier 230M C3 and QAD/PTQ two-file combination are NOT the current catalog cohort. This file records primary-source/canonical metadata only; no model was downloaded, locally hashed, installed or executed in this run.

## Current V13 catalog identities (read from this branch's unchanged specs/models.json)

| Role | Exact upstream repository revision | Exact file | Catalog SHA256 |
| --- | --- | --- | --- |
| B1_DETAIL | `LiquidAI/LFM2.5-1.2B-Instruct-GGUF@6767265158422fb8a19c62ceb45f16f05363615b` | `LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf` | `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1` |
| B2_GIST | `ggml-org/Qwen3.5-0.8B-GGUF@8fea620810c4afa23dd6443f999a48574c1611a3` | `Qwen3.5-0.8B-Q4_0.gguf` | `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf` |
| C3_LANGUAGE | `LiquidAI/LFM2.5-350M-GGUF@657e078c94084481950a2d555a941481f715536b` | `LFM2.5-350M-QAD-Q4_0.gguf` | `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d` |

The catalog explicitly records the October 9 decision to use the distinct Qwen B2 and the 350M C3 after Linux cloud comparisons. **Do not replace these with older model variants**. The catalog is not evidence that a particular installed home actually has those files; a future native collector must independently SHA256 each resolved installed model and runner, verify its configuration and owner/cgroup, and preregister the exact run before inference.

Publisher file pages corresponding to the catalog:
- https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF/blob/6767265158422fb8a19c62ceb45f16f05363615b/LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf
- https://huggingface.co/ggml-org/Qwen3.5-0.8B-GGUF/blob/8fea620810c4afa23dd6443f999a48574c1611a3/Qwen3.5-0.8B-Q4_0.gguf
- https://huggingface.co/LiquidAI/LFM2.5-350M-GGUF/blob/657e078c94084481950a2d555a941481f715536b/LFM2.5-350M-QAD-Q4_0.gguf

## Unregistered historical/alternative artifacts — NOT the active cohort

The official Liquid AI 1.2B repository at `8ed288026e23958ad9dfa92d53ed773a8eee7125` distinguishes QAD `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1` from PTQ `2ea801949d760cdf1a2cc04a54262c22c3c0c54f0769d57760c9adeb0e59233f`. This proves different GGUF bytes, not semantic specialization; it is not a substitute for the current Qwen B2. The historical C3 230M QAD file has publisher SHA256 `e75f83268de11b2a1bcfab5f3b5c5c0c97569ddbbc0990aad88437e45b8ba292` at `LiquidAI/LFM2.5-230M-GGUF@03502067c64ce32ac4fe87b0cec0310a1a13d3e9`; the current catalog lists it under `language.previous` at older revision `cdf97bd8205908758f44aec508d68ac1aef98f5c`, not as current C3.

Primary sources for alternatives:
- https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF/blob/8ed288026e23958ad9dfa92d53ed773a8eee7125/LFM2.5-1.2B-Instruct-Q4_0.gguf
- https://huggingface.co/LiquidAI/LFM2.5-230M-GGUF/blob/03502067c64ce32ac4fe87b0cec0310a1a13d3e9/LFM2.5-230M-QAD-Q4_0.gguf

Licenses: the two Liquid AI models declare the custom LFM Open License 1.0; the catalog marks Qwen3.5-0.8B as Apache-2.0. Verify license texts at the exact revisions before distribution. No weights, private logs or mirrors are committed.

## Exact next action

Use the current catalog identities, not alternatives, for any new candidate native installation. Confirm exact installed bytes, B1/B2 distinction, C3 consumer compatibility, runner/library SHA, owner/cgroup and thermal budget; then separately persist a new source/model/runner/seed registration and conduct serial native runs. The existing collector/scorer tests are SOFTWARE/MOCK only; STEP2, B3, Body-JEPA, jepa_weight, Age0 and whole-system gates remain negative.
