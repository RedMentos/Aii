# Run98 prereg — interactive human SOURCE_EXACT answer after F1/F5 source record (2026-10-29)

Owner GPT-6 scheduled continuation. Preregister FIRST on independently raw-verified Run92 #999 exact `58eb54a05532a5b9d25bd9713faf3bec1d55baff`. Conditional import only after Run96 #1004 and Run97 #1003 original corrected artifacts are independently GREEN; do not promote from open PRs. No main merge.

## User-visible function

Add an explicit **human TTY-only** interactive command `:source answer What is the budget for Project Elyra?` to the existing `:source budget Elyra 615 --confirm` lane. If a real F1/F5 correction is active, return JSON `status=FINAL`, `answer="Project Elyra budget: 615 Euro."`, `mode=SOURCE_EXACT`, `native_calls=0`, `model_called=false`. This is a deterministic exact rendering of a human-authorized source, **not** C3-generated text. It must not require an earlier assistant answer or installed native model. The existing `:verified` remains model-free READY/CLARIFY only, unchanged.

## Exact imports and modifications

- Import Run96 exact GREEN `v13/__main__.py`, `v13/operator.py`, `v13/source_record.py`, Run94/95/96 tests/docs/provenance, and Run97 exact GREEN `scripts/source_exact.py` + tests/docs/prereg. Preserve all other canonical files byte-for-byte, especially Runtime, Memory, Store, SourceConsumer, C3 model catalog, Age and SSOT.
- Extend `source_record.operator_command` only for `args[0]=='answer'`: join the remaining user question, bound it by `cfg['input_bytes']`, reject empty/oversize, call existing `scripts.source_exact.query_exact(r,question)`. No new parser/model, no auto-answer in ordinary chat, no changes to `--confirm` source recording or `source_exact` authorization.
- Add HELP text to `Operator` for the explicit answer command. Existing TTY origin check remains authoritative. Require idle/Stage0 RECORD_ONLY and unchanged source-bound revalidation as enforced by Run97.
- Real Runtime test: no source CLARIFY; preview no-write; confirm real F1/F5; `:source answer` FINAL exact, no model; wrong project/out-of-scope CLARIFY/NOT_APPLICABLE; restart preserves; `:forget <ID> --confirm` revokes and answer refuses; malformed/oversize/non-TTY/nonidle blocked. Full suite, source hashes, privacy/diff, closed original raw SHA256SUMS.

## Negative gates

No native C3 semantic quality, JEPA, STEP2 complementarity, B3 receiver, Body-JEPA, LP3, Redmi, Age promotion or whole-system completion. This is narrow project-budget source grammar and explicit user interaction only.