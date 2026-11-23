# P2 HF instruction-master metadata SHA pins — source-only result (2026-10-29)

**Prerequisite registered before download**: `P2_HF_METADATA_SOURCE_PIN_PREREG.md`, commit `63ea7db99b0b7cd164e82e6967e14bc435e770d1`. Execution workflow `.github/workflows/v13-p2-hf-metadata-source-pin-20261029.yml`, commit `67503d81bff291bcf190d1e4f1d8dc5754a7da60`, [Actions run 40847683959](https://github.com/RedMentos/Aii/actions/runs/40847683959) **GREEN**; job `123359090505`, fetch and artifact upload steps PASS. This is a public HF metadata download, **not** a model inference/training or weight-parity result.

Exact immutable source: `LiquidAI/LFM2.5-350M`, HF instruction revision `120bf032c36dd1273de754669da040dba7ad4982`, model.safetensors existing verified SHA256 `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`, license LFM Open License 1.0. The run downloaded **only** three public files using the pinned `/resolve/<revision>/` path with curl --fail:

| File | SHA256 from pinned-source run | Bytes |
|---|---|---:|
| `config.json` | `720b43d6ddc2ed25be23eed355aefcf342434a176dedad23dbe0a5e3ac24bbb8` | 1281 |
| `tokenizer.json` | `2221c71b5dce048a8abae62843b92bd7deec13cc153f95fa6e3327a47b79a7da` | 4733383 |
| `tokenizer_config.json` | `3701f370c70034d06e28947ff51c1063983393319f429e3ce58f06a45fae67cc` | 595 |

Original Actions artifact ID `12885272820` (`v13-p2-hf-metadata-source-pin`), original ZIP SHA256 `f9e4491afb82c637a8b85b561e0e019cb9468ff9e4b7be46a4e3a011d67bbbd3`. Downloaded the original artifact, independently computed exact same ZIP SHA256, ZIP CRC CLEAN, one member `SHA256_RECEIPT.txt`. Its complete hash/size/revision lines agree with decoded original job logs. **This independently verifies the receipt, not the three downloaded source file bytes** (those were not in this receipt-only artifact). A separate byte-bearing source-only recheck is required before claiming independent source-byte verification.

Next: independently retrieve these three exact public source files on a new source-only CI job, check against these frozen hashes, upload the original public metadata bytes and independently rehash the ZIP contents. Then run the structural tensor audit against pinned HF master and deployed QAD GGUF in an isolated environment, inspect mapping/shape and RoPE/template differences. No new native parity experiment or adapter training until source/mapping prereg gates. No STEP2, B3, Body-JEPA, LP3, jepa_weight, Redmi or V13 promotion; Age0 RECORD_ONLY.
