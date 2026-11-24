# Seed79 isolated native C3 German typed-value read prereg — 2026-10-30

Owner `assistant/v13-c3-de-typed-read-native-seed79-20261030`, review-only child of PR #1219 at `30bcf62f22c70107f920276263df6a7e9f8872de`. Source-only work may proceed; native jobs are serialized.

## Fixed source and model prerequisites
Use existing `v13/agi/listarith.READ_SYSTEM` and `READ_SCHEMA` **unchanged**, exact current `v13/code/specs/models.json` blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, pinned C3 `LiquidAI/LFM2.5-350M-GGUF` revision `657e078c94084481950a2d555a941481f715536b`, GGUF `LFM2.5-350M-QAD-Q4_0.gguf` SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, size 219312832. License `LFM Open License 1.0`, upstream license recorded in model catalog. Existing llama-server native binary is fetched from pinned catalog and hash-checked. Do not modify model, license, source, quantization, scorer, seed67/71/73 or C3 production path.

Freeze **12 new German synthetic named-integer input texts**, each with expected named integer pairs and a supported simple total question, before harness implementation. Include distractor dates, an aggregate claim, duplicate values, signed values, and varied German listing formats. A schema-compliant C3 reader is measured as **source extraction only**, not arithmetic accuracy or end-to-end tool utility. The exact original JSON generation and runner resource metrics, model hash and process release must be retained per row. No use of Age/C5 overrides; call isolated `LlamaRunner.generate` with the existing read schema, never execute ToolStep or write user state.

## Preregistered outcomes
- `NATIVE_C3_DE_READ_SUPPORTED` iff at least **9/12 exact name+integer item sets**, zero invented nonaggregate numeric values, all 12 native runs complete with original model/binary hashes, no un-reaped runner process and no schema violations. Otherwise `NATIVE_C3_DE_READ_NOT_SUPPORTED` or `PILOT_PARTIAL_RED` for incomplete runs. Aggregates such as `Summe: ...` are not an input item; count any aggregate-read separately and never hide it.
- Report exact row-level raw output, parsed JSON, expected/actual, source-number guard result, aggregate contamination, native process PID, RSS/PSS, load/prefill/stream timing, and error types. Preserve failed attempts.
- A source-only test and fixture hash preflight is distinct from actual native inference. No software/synthetic/native result promotes STEP2, B3, Body-JEPA, jepa_weight, Redmi or whole-system completion.

Age0 RECORD_ONLY, jepa_weight=0, external actions off, no learned authority, no device measurement. Exact next: commit 12-row fixture and pin blob; implement isolated native capture and strict audit; run source-only preflight then one native Actions job if prerequisites available. Continue other canonical packages if native job blocked.
