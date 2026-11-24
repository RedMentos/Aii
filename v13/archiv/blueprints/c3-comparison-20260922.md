# C3 comparison preparation — 2026-09-22

Canon requires a real SmolLM2-135M-Instruct vs LFM2.5-230M comparison; neither a model card nor one alpha chat is a selection proof.

Fresh source check on 2026-09-22:
- Upstream SmolLM2-135M-Instruct is Apache-2.0 and primarily English; its published limitations warn that factual/logical output can be unreliable.
- Public GGUF conversions exist and llama.cpp can run them, but the GGUF artifacts located in this check are community conversions rather than an official HuggingFaceTB GGUF release. Therefore this continuation does **not** silently pin or download one into the production model manifest.
- A diagnostic paired benchmark harness was added at `scripts/benchmark_c3.py`. It uses the same pinned local llama-server/config for the installed C3 baseline and an operator-supplied candidate GGUF, never mutates `config/models.json`, and records per-fixture native timings/RSS plus deliberately narrow lexical smoke checks.

Sources checked:
- https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct (upstream model/card; Apache-2.0, English-primary limitations)
- https://huggingface.co/QuantFactory/SmolLM2-135M-Instruct-GGUF (community llama.cpp conversion; Apache-2.0 metadata)
- https://huggingface.co/tensorblock/SmolLM2-135M-Instruct-GGUF (community GGUF quant matrix)

Claim limit: no C3 winner is selected in this continuation. A paired real-weight run, preferably repeated on the Redmi, plus validated/human quality scoring is still required.
