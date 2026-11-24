# P2 independently observed ordinary HF vs exact QAD tokenizer difference (2026-10-29)

Independent source-byte artifacts (both ZIP SHA/CRC/individual files verified): ordinary HF instruction master `LiquidAI/LFM2.5-350M@120bf032c36dd1273de754669da040dba7ad4982`, Actions `40847869855`, tokenizer SHA `2221c71b5dce048a8abae62843b92bd7deec13cc153f95fa6e3327a47b79a7da`; exact QAD FP32 source `LiquidAI/LFM2.5-350M-GGUF@657e078c94084481950a2d555a941481f715536b/qad`, Actions `40848748542`, tokenizer SHA `df1d8d5ec5d091b460562ffd545e4a5e91d17d4a0db7ebe733be34ed374377bd`.

Decoded both original JSON files locally, compared parsed structures without any model call. Both have **509 `added_tokens` entries**, identical token IDs/contents in the six differing entries, but the **`special` boolean differs** (ordinary HF `true`, QAD `false`) for IDs:
- `10` `<|tool_call_start|>`, `11` `<|tool_call_end|>`
- `64011` `Mathias`, `64014` `python`
- `64400` `<think>`, `64401` `</think>`

Other top-level tokenizer JSON sections parsed equal; `tokenizer_config.json` also differs: ordinary HF has `is_local=true`, QAD `false`, and ordinary HF includes empty `extra_special_tokens` and `model_specific_special_tokens` entries that QAD omits. QAD has an independently pinned `chat_template.jinja` SHA256 `ba551d58630afa3190b1be3602e28301f3d2e9bbac978dfc49d6d825171648b6`.

**Implication**: token ID vocabulary identity alone is not enough for chat/template/skip-special-token parity. In particular tool-call and thinking-token treatment may differ. This is a *source-file metadata difference*, **not yet a demonstrated runtime token-ID or logit divergence**. Use the QAD source tokenizer/template for the QAD FP32 training candidate; do not silently substitute ordinary HF metadata. Next: preregister fixed non-heldout tokenizer/template probes across HF QAD and deployed GGUF native runtime; keep Age0, AG6 and all negative gates unchanged.
