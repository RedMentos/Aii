# Prospective follow-up: bind fixed eligibility final authority to exact visible bytes

2026-10-26. First source-only attribution package passed Actions 40376233219 on exact head `afdc11e1af20cb4d15f3471cd144d6c1e2cc71e4`, raw artifact 12673959051 SHA256 `aff1680fcee20b03ab0fa725613c5b3364fa62ab93cde073884bb588196a97f4`; original Run574 causal scope remains source-only.

New adversarial hypothesis: a corrupted/modified final visible answer with `meta.output_authority=ELIGIBILITY_TOOL_FINAL`, `tool_answer_first=FINAL`, and a typed UNKNOWN/NONE tool result can still be classified as fixed-tool authority without comparing the output bytes against `eligibility.final_text(args,result)`. This permits inaccurate provenance in the broker even though conflict checking may later produce a correction.

Implement a strict exact-text guard in the broker's candidate selection (including safe rejection of malformed tool-result shapes); test exact positive UNKNOWN/NONE, tampered answer, missing keys and forged metadata. Preserve existing broker precedence, egress, correction and C3 A/B LEAD behavior. Source-only; no native, Redmi, new learning authority, model downloads or gate promotion. Retain original failed CI attempts and raw. Review branch only.
