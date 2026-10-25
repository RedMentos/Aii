# Run324 preregistration — real pinned FP32 LFM2 HF→GGUF conversion (no training)

UTC 2026-10-25. Independent owner: new `scripts/probe_native_fp32_convert_run324.py`, `tests/test_native_fp32_convert_run324.py`, dedicated native conversion CI and this proof directory. Parent Run323 verified checkpoint `fd8c12ae56a1add448dbe9001e4e57db3cc98029` / PR320. No edits to Run320-owned evaluator/workflow, original native training C++, Canon, seeds, runtime or weights.

## Frozen prerequisite and exact one-arm experiment

Original Run320 native `40211685395` RED at `transformers==4.57.1` `TokenizersBackend` before any optimizer. Run322 proved exact tokenizer in 5.3.0; Run323 exact official b10964 `--vocab-only` **actually PASS** (2,379,906-byte GGUF, zero tensors, 26 metadata entries). **Neither proves full model tensor conversion.**

One preregistered full conversion: exact official `ggml-org/llama.cpp` tag **b10964**, source tar SHA256 `4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe`, unmodified converter SHA256 `e9a1da876330bbce9687541ab31736542a01b4ac43c6686126514a50f122fb7f`. Exact HF `LiquidAI/LFM2.5-350M` revision `9e6c6ccf47cd318696e137d381a7ded8fe4df09f`, LFM Open License v1.0. Download **all actual pinned safetensors + tokenizer/config** to ephemeral CI, record SHA256 of each unchanged original file. No Q4 weights substituted for FP32 master. Isolated `torch==2.8.0` CPU, `numpy==2.3.5`, `transformers==5.3.0`, `jinja2==3.1.6`, `safetensors==0.6.2`, `sentencepiece==0.2.1`, `protobuf==6.33.0` and resolver-compatible hub; record `pip freeze`.

Run official `convert_hf_to_gguf.py <exact HF snapshot> --outfile <temp>/lfm350-f32.gguf --outtype f32` (bounded timeout 12 min). On success, validate immutable source tar/converter/model file hashes; GGUF magic/version, positive tensor and metadata counts, plausible FP32 master bytes 1–3 GB, `general.file_type=ALL_F32`, `general.architecture=lfm2`, every tensor quantization type F32, plausible parameter count 250–500M. Record actual GGUF SHA256, bytes, tensor counts, source hashes, CPU dependencies. Do not upload GGUF or HF weights, do not activate or train. On any failure, retain raw error and hash-bound original source; no post-hoc substitutions.

Eight+ software negative tests: fake/missing/truncated GGUF, non-F32 file type, quantized tensor, wrong architecture, wrong source tar/converter, absent safetensors. Native success is **FP32_CONVERSION_ONLY**, not native optimizer, retention, inference, Redmi or AGI.

**Next after proof:** hand off exact converted-master recipe/hash to Run320 owner for preregistered 2-epoch native optimizer, same 8/6/5/12 fixed synthetic cohort and original thresholds; no unapproved training or promotion. Serialize heavy native/model jobs; preserve original RED Run320 artifact `12606256943`. All gates unchanged STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi MISSING, V13 INCOMPLETE.
