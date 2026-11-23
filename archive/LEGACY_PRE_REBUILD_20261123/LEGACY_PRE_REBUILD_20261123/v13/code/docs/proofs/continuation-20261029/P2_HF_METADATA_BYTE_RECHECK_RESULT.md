# P2 independent pinned HF metadata bytes — exact-source verification (2026-10-29)

Original three-file hash receipt: [Actions 40847683959](https://github.com/RedMentos/Aii/actions/runs/40847683959), ZIP SHA256 `f9e4491afb82c637a8b85b561e0e019cb9468ff9e4b7be46a4e3a011d67bbbd3`. Independent recheck prereg committed **before** execution `da81b28844d00ae4d97ac0cf1db2d322869e0da7`, exact frozen expected SHA256 listed in `P2_HF_METADATA_BYTE_RECHECK_PREREG.md`.

Independent workflow commit `f516deb02508c0533359efee43fd94c61b848e05`; [Actions run 40847869855](https://github.com/RedMentos/Aii/actions/runs/40847869855) **GREEN**. Original public metadata-byte artifact ID `12885423278`; ZIP SHA256 `90220d9bff41ff0e6024c618756c7eb4a2b38cdc25b1779460a5309a8ec08468`, independently downloaded and rehashed equal to GitHub artifact digest; ZIP CRC CLEAN. Five members: `SHA256SUMS`, `SOURCE_PIN.txt`, and exactly `config.json`, `tokenizer.json`, `tokenizer_config.json`. Independently rehashed all three extracted **original public bytes**:

- `config.json`: 1281 bytes, SHA256 `720b43d6ddc2ed25be23eed355aefcf342434a176dedad23dbe0a5e3ac24bbb8` — PASS.
- `tokenizer.json`: 4,733,383 bytes, SHA256 `2221c71b5dce048a8abae62843b92bd7deec13cc153f95fa6e3327a47b79a7da` — PASS.
- `tokenizer_config.json`: 595 bytes, SHA256 `3701f370c70034d06e28947ff51c1063983393319f429e3ce58f06a45fae67cc` — PASS.

Exact HF source: `LiquidAI/LFM2.5-350M` at `120bf032c36dd1273de754669da040dba7ad4982`; pre-existing full master `model.safetensors` SHA256 `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`. Independent config parse: `model_type=lfm2`, `num_hidden_layers=16`, `hidden_size=1024`, `vocab_size=65536`, `architectures=[Lfm2ForCausalLM]`; 16 conv/full_attention layers. These are source metadata, **not** verified deployed GGUF architecture equivalence. `tokenizer_config.json` has no `chat_template` key; do not assume matching template.

Next: isolated structural audit with pinned master/GGUF and matching GGUF source; do not infer QAD value/logit parity from matching shapes. Preserve all negative gates and AG6 approval; no model call/training, Redmi test or production merge in this source-byte recheck.
