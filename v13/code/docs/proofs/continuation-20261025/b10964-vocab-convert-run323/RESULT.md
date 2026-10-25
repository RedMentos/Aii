# Run323 result — real pinned b10964 vocab-only GGUF conversion

UTC 2026-10-25. PR320, branch `assistant/b10964-vocab-convert-run323-20261025`, parent Run322 `339270685aa9be6bafe715f92ce5e18e4ff48718`. Preregistered before execution at `643681024d07ed9927b409823295986ac157349c`. Exact tested source `0e6e8c9aeb84feac834b7d1f9529bc54410eb8a2`.

**Real official converter execution: PASS_VOCAB_ONLY_NOT_MODEL_CONVERSION.** CI `40213050852`, job `121228219191`, all stages GREEN, 8/8 structural fixture tests PASS, privacy CLEAN. Raw artifact `12606775624`, ZIP SHA256 `b01e4afcc97846b3786593f9b39dcc09e5175de980ee42bc4b45e6e44c845d1b`; source and raw logs hash-closed. No GGUF or model weights uploaded.

- Original official `ggml-org/llama.cpp` b10964 source tar SHA256 `4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe`; unpatched converter SHA256 `e9a1da876330bbce9687541ab31736542a01b4ac43c6686126514a50f122fb7f`.
- Unmodified official `LiquidAI/LFM2.5-350M@9e6c6ccf47cd318696e137d381a7ded8fe4df09f`, 5 tokenizer/config files; `tokenizer_config.json` SHA256 `3701f370c70034d06e28947ff51c1063983393319f429e3ce58f06a45fae67cc`, license LFM Open v1.0.
- Isolated CPU `torch==2.8.0`, `numpy==2.3.5`, `transformers==5.3.0`, `jinja2==3.1.6`, plus pinned source dependencies; full `pip freeze` in raw evidence.
- Actual command: `convert_hf_to_gguf.py --vocab-only --outfile <temp>/run323-vocab.gguf <pinned HF tokenizer snapshot>`; official log `Model vocab successfully exported`.
- Actual ephemeral GGUF: **2,379,906 bytes**, SHA256 `187f7fff5aeeb828e59e1950edf31e60d1f518d95caf4021465aef32b77a846f`, GGUF version 3, **0 tensors**, 26 metadata entries. File intentionally not published.
- No model weights downloaded, no FP32 model tensor conversion, no native optimizer epoch, no deployed inference or Redmi evidence. This is stronger than a pure Python tokenizer test but not an end-to-end training proof.

Original negative evidence preserved: Run320 native `40211685395` RED due 4.57.1 `TokenizersBackend` error, Run322 two RED prerequisite/harness attempts and eventual tokenizer-only PASS. No original registered source/model/seed/hash changes.

**Next exact package:** isolated **full pinned FP32 HF→GGUF conversion** on the same official b10964 source and unchanged pinned HF weights with Transformers 5.3.0, compare exact downloaded file hashes and record GGUF header/tensor count and full master SHA. Retain failed attempts, never upload weights. Then execute the preregistered Run320 two-epoch optimizer/quantization/heldout cohort serially, respecting Run320 owner and original gates. Full conversion is not yet proved.

Gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Redmi MISSING, V13 INCOMPLETE. No production activation or private data.
