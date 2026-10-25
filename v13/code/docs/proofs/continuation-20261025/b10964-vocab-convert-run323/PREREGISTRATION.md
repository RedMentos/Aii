# Run323 preregistration — exact pinned b10964 vocab-only converter (no model weights)

UTC 2026-10-25. Independent owner: new `scripts/probe_native_vocab_convert_run323.py`, `tests/test_native_vocab_convert_run323.py`, new CPU-only workflow and this proof directory. Parent Run322 verified tokenizer-only checkpoint `339270685aa9be6bafe715f92ce5e18e4ff48718` / PR319. No edits to active Run320 original native workflow, frozen learning code, Canon, seed or model.

## Frozen prerequisite and hypothesis

Run320 original native CI `40211685395` RED at `transformers==4.57.1` tokenizer class, before optimizer. Run322 `40212714416` proved exact HF `LiquidAI/LFM2.5-350M@9e6c6ccf47cd318696e137d381a7ded8fe4df09f` tokenizer works under isolated `transformers==5.3.0` + `jinja2==3.1.6` (5 deterministic prompts) without model weights. **This does not prove official converter compatibility.**

Pre-register one candidate only: official `ggml-org/llama.cpp` tag **b10964** source tarball SHA256 `4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe`, unpatched converter. Download only the exact five HF tokenizer/config files from the same pinned revision, hash original bytes, preserve LFM Open v1.0 provenance. Isolated CPU dependencies: torch==2.8.0 (CPU index), numpy==2.3.5, transformers==5.3.0, jinja2==3.1.6, sentencepiece==0.2.1, protobuf==6.33.0, safetensors==0.6.2, compatible resolver-chosen hub; capture pip freeze. No paid services.

Run `python3 <b10964>/convert_hf_to_gguf.py --vocab-only --outfile <temp>/lfm-vocab.gguf <exact-snapshot>`. On success, require GGUF magic, version in supported range, **zero tensors** (vocab-only), positive bounded metadata count, minimum nontrivial byte length, file SHA256 and exact source manifest binding. Do not publish GGUF or model weights; raw logs/manifest/hash only. On failure, preserve complete converter stderr and nonzero status, **do not** rewrite the HF tokenizer or patch b10964. Synthetic source-only tests for invalid GGUF, missing file, nonzero tensor count, truncated header, wrong source revision/hash and correct header.

A vocab-only success would establish only the official b10964 tokenizer/metadata path under the new isolated Python version, not a complete FP32 tensor conversion, optimizer epoch, deployed inference or Redmi. The next independent package must test full pinned FP32 conversion and native training with same registered hashes and original negative gates. Serial heavy native jobs, no competing optimizer.

Source/license links: https://github.com/ggml-org/llama.cpp/blob/b10964/convert_hf_to_gguf.py ; https://huggingface.co/LiquidAI/LFM2.5-350M/blob/9e6c6ccf47cd318696e137d381a7ded8fe4df09f/tokenizer_config.json .

STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi MISSING, V13 INCOMPLETE. No model/seed/Canon changes.
