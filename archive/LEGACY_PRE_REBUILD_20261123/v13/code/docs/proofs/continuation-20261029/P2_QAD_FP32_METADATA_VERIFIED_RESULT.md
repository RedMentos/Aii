# P2 official QAD FP32 metadata: independently verified public source bytes (2026-10-29)

Source-only prereg `P2_QAD_FP32_SOURCE_METADATA_PREREG.md` committed `138c0d7a9e5b10dc3a15d9ca77cee405f4c90f8f` **before** workflow `05ed3263b3986913b04212eb1cca1abd9e4335db`. [Actions run 40848748542](https://github.com/RedMentos/Aii/actions/runs/40848748542) **GREEN**. Artifact `12885912131`, original ZIP SHA256 `216abc4c90fb7ded57581d9c4064e28914a4cc43851ed91c43677b161bef07df`, independently downloaded, ZIP CRC CLEAN, 8/8 original public metadata file SHA256SUMS independently rehashed, plus source pin receipt `LiquidAI/LFM2.5-350M-GGUF@657e078c94084481950a2d555a941481f715536b/qad`.

Exact source metadata SHA256:
- `README.md` 3098 bytes: `d007385cd630a1102185bc14f32a91cd0c8e3fac94740d49eb43627400e83402`
- `LICENSE` 10596: `5188f2b355da20647257a3156db5834c794e5fb5e6d8dc4d4cdbb3180e75b85b`
- `provenance.json` 936: `c3184c381730efd5a1e68b64dd1c3061e2fae7bec6da94e33874ecb762c85907`
- `config.json` 1308: `884c7b2b936f296dd448bfca18a14fd9bc903be7d3bff1303ac62bbb43f641d6`
- `tokenizer.json` 4733389: `df1d8d5ec5d091b460562ffd545e4a5e91d17d4a0db7ebe733be34ed374377bd`
- `tokenizer_config.json` 490: `b99856c5bdc9f88cc30a7ffff78bfc7768427e0b1216d0c196b27e5d55043455`
- `chat_template.jinja` 5487: `ba551d58630afa3190b1be3602e28301f3d2e9bbac978dfc49d6d825171648b6`
- `generation_config.json` 134: `0ec7d228c4de7e3453e98bf6910c7eb7841e87fede63ea11c0f75a5c64e1c3c3`

Verified original `provenance.json` names **FP32 QAD master** `qad/model.safetensors` SHA256 `1d90518482c4ec204bebb4820bbaee4f8a38c5a6df72256f86bcd21fe52ad079`, 1,417,952,352 bytes per official immutable commit; deployed QAD GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`; pinned upstream converter `74ade52741203e5c8f81eaf06a96cb1cfe15f2a3`, release QAD GGUF parent `9969000761ce34de907bf20017cbfc3d52d6eaf9`. Official source claims byte-identical quantized tensors and whole-file reconstruction with release metadata; **not yet independently reproduced by V13**.

Important: QAD `tokenizer.json` SHA `df1d8d5...` differs from ordinary HF instruction-master `2221c71...`, and QAD `config.json` SHA `884c7b...` differs from ordinary master `720b43...`. **Never silently reuse the ordinary HF tokenizer/config for QAD training.** QAD source has `dtype=float32`, 16 LFM2 layers, hidden 1024 and vocab 65536. Next: download/hash QAD FP32 weights under isolated resource guard, run no-inference structural/value correspondence against pinned deployed QAD GGUF, preserve raw. Only after evidence and separate AG6-gated preregistration consider a QAD-master LoRA baseline. No production merge or negative-gate promotion.
