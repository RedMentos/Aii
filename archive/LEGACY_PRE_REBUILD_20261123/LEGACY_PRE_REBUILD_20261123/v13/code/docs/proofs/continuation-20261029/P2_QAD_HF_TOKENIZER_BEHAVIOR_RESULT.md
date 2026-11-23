# P2 eight pinned QAD vs ordinary HF tokenizer probes — source-only result (2026-10-29)

Pre-registered eight synthetic public strings and two immutable tokenizer SHA pins in `P2_QAD_HF_TOKENIZER_BEHAVIOR_PREREG.md` commit `1103f82549eea287a6b0e127c23aa18dcaaa652d` before workflow commit `22340db8021497e59e5c00a8e631d6e9a449965a`. [Actions 40849657373](https://github.com/RedMentos/Aii/actions/runs/40849657373) **GREEN**, pinned `tokenizers==0.22.1`, both original source JSON SHA PASS, no model weights/inference/training. Artifact ID `12885804161`, original ZIP SHA256 `a51d34497becb61527a636a37d22f19b2c804f8e900a4d74899f38bae2a05f5e`; independently downloaded/rehashed, ZIP CRC CLEAN, original source hash log and full 8-probe JSON retained.

Report `v13.p2.qad_hf_tokenizer_behavior_source_only.v1`, `TOKENIZER_SOURCE_BEHAVIOR_MEASURED_GGUF_UNPROVEN`: **8/8 input token-ID sequences identical** under `encode(add_special_tokens=False)`; **only 4/8 decoded outputs identical** under `decode(skip_special_tokens=True)`. Exact differences:
- `<|tool_call_start|>python<|tool_call_end|>`: ordinary HF decodes `''` (empty), QAD preserves the entire string; both IDs `[10,64014,11]`.
- `<think>reasoning</think>`: ordinary HF decodes `'reasoning'`, QAD preserves `'<think>reasoning</think>'`.
- `Mathias uses python.`: ordinary HF decodes `' uses .'`, QAD preserves full `'Mathias uses python.'`.
- `{"tool":"python"}`: ordinary HF decodes `'{"tool":""}'`, QAD preserves `'{"tool":"python"}'`.
The other four prompts (`Hello.`, `2 + 2 = ?`, `Äpfel, Öl und Straße.`, and a two-line string) decode identically. The six `added_tokens.special` boolean differences previously identified explain these observations. No posthoc prompt selection or threshold.

**Implication**: The ordinary HF and QAD source tokenizers agree on these eight input ID sequences but can produce **materially different decoded text when skipping special tokens**. This matters for tool-call/thinking handling and any training or evaluation pipeline that decodes outputs. Use the exact QAD source tokenizer/template for the QAD FP32 training candidate; do not silently substitute ordinary HF. This remains **source-only**, not deployed GGUF runtime tokenization or model logit parity. All negative gates unchanged.
