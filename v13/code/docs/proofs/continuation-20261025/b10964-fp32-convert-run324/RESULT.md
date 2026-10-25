# Run324 result — real pinned FP32 model tensor conversion, no optimizer

UTC 2026-10-25. PR321, branch `assistant/b10964-fp32-convert-run324-20261025`, parent Run323 `fd8c12ae56a1add448dbe9001e4e57db3cc98029`. Preregistered at `4cc9aa00351a973e229d47410ddfd5e1e41e5a4b` before the real model download/conversion. Exact tested source `e205152e9e0bf657c6189b99672b122244b44fd1`.

**Real full model conversion PASS_REAL_FP32_CONVERSION_NO_TRAINING.** GitHub Actions CI `40213340677`, job `121229084221`, all stages GREEN; **10/10** synthetic negative/source-bound tests PASS; official privacy scan CLEAN. Raw artifact `12606995474`, ZIP SHA256 `2d2443917539ca4826f13341c6bbfebd3823ea11b857edcc43efa8d50cb62e71`, 30-day retention. Source/manifest/pip freeze/converter stdout/stderr/verification report hash-closed. Neither HF weights nor GGUF uploaded.

- Official pinned `LiquidAI/LFM2.5-350M@9e6c6ccf47cd318696e137d381a7ded8fe4df09f`, LFM Open License v1.0. Original **`model.safetensors` 708,984,464 bytes** SHA256 `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`. Six unchanged original HF files; tokenizer config SHA256 `3701f370c70034d06e28947ff51c1063983393319f429e3ce58f06a45fae67cc`.
- Official **unmodified** llama.cpp b10964 source tar SHA256 `4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe`, converter SHA256 `e9a1da876330bbce9687541ab31736542a01b4ac43c6686126514a50f122fb7f`.
- Isolated CPU `torch==2.8.0`, `numpy==2.3.5`, `transformers==5.3.0`, `jinja2==3.1.6`, pinned conversion dependencies, recorded `pip freeze`. Official command `convert_hf_to_gguf.py <pinned HF snapshot> --outfile <ephemeral>/run324-f32.gguf --outtype f32` completed.
- Ephemeral **FP32 GGUF** SHA256 `5d200c19f13483e66b39d9feb3353032581882f3eb10cc8752f027d4688d6e6f`, **1,420,324,800 bytes**, GGUF v3, `lfm2` architecture, `general.file_type=ALL_F32`, **148 tensors, all F32**, 354,483,968 tensor elements, 27 metadata fields. Exact source and master SHA measured, no model publication.

This resolves the original Run320 HF→GGUF conversion prerequisite using an isolated compatible tokenizer version, **without** changing registered HF/model/source hashes. It does **not** prove native optimizer epochs, Q4 heldout utility, learning retention, phone thermal/RSS, Body-JEPA, or V13 completion.

**Next:** use the same immutable HF revision/source/master recipe in a separately owned review workflow to run original Run320 preregistered **two native CPU optimizer epochs**, epoch checkpoint hashes, Q4_0 heldout cohort and independent Run321 postflight audit. Do not modify Run320 original owner files or original 8/6/5/12 cohort, thresholds, seeds or negative gates. Serialize native/model jobs and preserve failures. Original Run320 native `40211685395` remains RED at 4.57.1 (0 epochs), retained as negative evidence.

Gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Redmi MISSING, V13 INCOMPLETE. No production activation.
