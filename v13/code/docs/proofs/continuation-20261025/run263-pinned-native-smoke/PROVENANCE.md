# Run263 public model provenance check (2026-10-25)

Scope: research/source verification only; all download bytes remain pinned by the existing `v13/code/specs/models.json` and its Git blob. No model swap, quantization change, or license acceptance claim.

- B1 DETAIL: `LiquidAI/LFM2.5-1.2B-Instruct-GGUF` at registered revision `6767265158422fb8a19c62ceb45f16f05363615b`, `LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf`, expected 695755488 bytes, SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`. Official upstream model card: https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF ; official license text: https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF/blob/main/LICENSE . LFM Open License v1.0, not Apache-2.0; do not assert license accepted by the operator.
- B2 GIST: `ggml-org/Qwen3.5-0.8B-GGUF` at registered revision `8fea620810c4afa23dd6443f999a48574c1611a3`, `Qwen3.5-0.8B-Q4_0.gguf`, expected 563036064 bytes, SHA256 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`. Official file card: https://huggingface.co/ggml-org/Qwen3.5-0.8B-GGUF/blob/main/Qwen3.5-0.8B-Q4_0.gguf ; Apache-2.0.
- C3 LANGUAGE: `LiquidAI/LFM2.5-350M-GGUF`, registered revision `657e078c94084481950a2d555a941481f715536b`, QAD Q4_0 expected 219312832 bytes, SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`; LFM Open License v1.0.
- C2 CONTROL: `Cactus-Compute/needle3`, registered revision `b274efcb211a9eef48c9a88da4b43bd569696a39`, expected 35335380 bytes, SHA256 `c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38`; Apache-2.0.
- Native runner: `ggml-org/llama.cpp` tag `b10964`, Linux x86_64 archive expected 16825086 bytes, SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`.

No downloaded bytes are claimed until Run263 CI reports complete hash checks. Linux native inference (if achieved) is distinct from Redmi and training. All model/seed hashes and original negative gates remain unchanged.
