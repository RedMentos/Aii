# Run322 result — pinned tokenizer-only compatibility (not native conversion)

UTC 2026-10-25. PR319, branch `assistant/lfm2-tokenizer-compat-run322-20261025`, base Run321 `3531d79d736de0f99d606976ec6ac4f064ba3139`. Preregistered at `822655ef527040c19e1350df50894ee61c77e1b0` before code. **Exact passing source:** `d954e2ed14210cf90caf3e025d288d583cb04f2f`.

## Frozen two-arm result

- Exact HF `LiquidAI/LFM2.5-350M` revision `9e6c6ccf47cd318696e137d381a7ded8fe4df09f`, **5 unchanged tokenizer/config files**, no weights. Original `tokenizer_config.json` SHA256 `3701f370c70034d06e28947ff51c1063983393319f429e3ce58f06a45fae67cc`; class `TokenizersBackend`. License LFM Open v1.0.
- Isolated `transformers==4.57.1`: **expected FAIL**, `ValueError: Tokenizer class TokenizersBackend does not exist or is not currently imported`. This reproduces the Run320 converter prerequisite blocker without model weights.
- Isolated `transformers==5.3.0` + `jinja2==3.1.6`: **PASS**, five fixed chat prompts, two independent tokenizer loads, identical token-id sequences. Token counts **11,17,16,16,16**; sequence SHA256s: `f7daa5f77d5e958c5834787b85122626288156b12f25fbc3dec8787ee68d8fe9`, `8f6ec3532c0e85bc934c459e5c70ee066c56deafb66d1208fe0278fa1956d70b`, `eece4ad6eed010ac3c3d502f9377e5d26aa6ec0cbd6b78ab85fce0b34aed5855`, `4fcb9d133532b2ab704366f8b6215665484409d0fa7d1a1a7ba3e795590b6c1d`, `f3403eda6d65a147024b986915b4440f511ee4eb9ada83cf8a29ed2f054517c0`.
- Preregistered assessment `COMPAT_DIAGNOSTIC_SUPPORTED`, **not** native converter proof, not an optimizer epoch, no GGUF. Source-only fixture tests **7/7 PASS**; official privacy `CLEAN`.

## Raw attempts and durable evidence

1. CI `40212484153` RED: 4.57.1 expected fail; 5.3.0 loaded tokenizer but chat-template call failed because isolated environment lacked `jinja2`. Raw artifact `12605864111` ZIP SHA256 `0ed9d90aaada794f5346fc2a01a2ab3280763cc21c70f757ecfc7a81914ba2f8`.
2. CI `40212587785` RED: Jinja2 installed, 5.3.0 tokenizer returned a non-plain-dict mapping not handled by probe. Raw artifact `12605864308` ZIP SHA256 `5daf0ffbe3bf3dccddc7dca3ee5381984369d85495c8e5f9e4dc3235b3170de5`.
3. Intermediate `40212700980` cancelled by newer exact-head commit, not counted as evidence.
4. **GREEN** CI `40212714416`, job `121227398762`: both preregistered arms, 7/7 fixture tests, exact HF source hashes, privacy CLEAN. Raw artifact `12606850007` ZIP SHA256 `2af6899d06c9d8c3344d8f9de6f38235b82d5d5fbede8e7ebfb74594d1ca9728`. Original RED attempts retained; no deletion or retrospective cohort change.

## Scope and next command

Independent **next step:** test **exact pinned official llama.cpp b10964** `convert_hf_to_gguf.py --vocab-only` against the same unmodified HF tokenizer snapshot with isolated 5.3.0 dependencies, then separately attempt real FP32 conversion and native two-epoch training with original source/model/seed hashes. Do not modify Run320 owner files or rerun native training until the prerequisite passes. Original Run320 RED `40211685395` remains negative native evidence (0 optimizer epochs).

Primary sources: https://huggingface.co/LiquidAI/LFM2.5-350M/blob/9e6c6ccf47cd318696e137d381a7ded8fe4df09f/tokenizer_config.json ; https://github.com/huggingface/transformers/blob/main/src/transformers/tokenization_utils_tokenizers.py ; https://github.com/ggml-org/llama.cpp/blob/b10964/convert_hf_to_gguf.py .

Gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi MISSING, V13 INCOMPLETE. No model/seed/Canon/runtime changes or model weights published.
