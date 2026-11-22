# Run95 prereg — human-recorded source budget from real Age0 operator without model answer (2026-10-29)

Owner GPT-6 scheduled continuation. Review-only child of independently raw-audited Run92 #999 exact `58eb54a05532a5b9d25bd9713faf3bec1d55baff`. Preregister before code/tests. Independent of Run93 native cohort and Run94 CLI. No main merge or frozen source/model changes.

## Problem

`:remember` currently requires a prior model answer; the verified F1/F5 source-backed C3 budget path is therefore awkward for a human to seed from a fresh session. Add an **explicit human-only Age0 command** `:source budget Elyra 615 [--confirm]` to create a durable real `Store.event` and `Memory.feedback(kind='fact', permission='record', scope='session')` with key `Project Elyra budget` and value `615 Euro`. No native model call or assistant answer required. This is not arbitrary external web fact ingestion.

## Fixed safety and functionality

- New isolated module `v13/source_record.py`, minimal `Operator.run` dispatch and HELP addition, new tests/docs/workflow. Frozen `v13/operator.py` base blob `7bf3a992af1db87f6ee2432c2486dbbced0f2bd4`, `v13/memory.py` `53dc948d0d360f94743ad996eb83ea0e85c2dd0b`, `v13/source_consumer.py` `4b73842be25e784f70ade4f6c4ced3fe2dcb9eab`, `v13/runtime.py` `68e7ed1352800174972558f1e0b0683a42c8689a`, canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7`; do not edit any frozen source except the specified Operator dispatch.
- `:source budget NAME AMOUNT` without `--confirm` returns exact human preview and **writes nothing**. Only `:source budget NAME AMOUNT --confirm` commits; origin must be OPERATOR_TTY (existing Operator origin gate), Runtime idle, Stage0, RECORD_ONLY, latents disabled and jepa_weight=0. Never use a model for parsing or authority.
- Strict `NAME=[A-Za-z][A-Za-z0-9_-]{0,39}`, `AMOUNT=(0|[1-9][0-9]{0,8})`, no signs/decimals/grouping/newlines/extra flags, source value exactly `N Euro`. No global scope; session only. Wrong/ambiguous command rejected before any event/Memory writes. Human command source recorded as the event input.
- Real `Memory.feedback` provides HumanDecision/F1/F5 SourceRef; after restart the existing `:verified What is the budget for Project Elyra?` must return READY, zero native calls. Wrong project CLARIFY. Explicit new value supersedes same-key active memory under existing Memory semantics. `:forget <ID> --confirm` revokes source and `:verified` returns CLARIFY. No model called in all software tests.
- Test preview/no-write, confirm, restart, same-key update, wrong project, malformed/injection, non-TTY origin, nonidle and non-Age0 refusal, forget; run focused and full suite, privacy/diff, closed raw hashes.

## Claim limits

This is narrow user-authored F1/F5 source **ingestion** only, not learned factual accuracy, native C3 generation, semantic memory, JEPA, STEP2, B3, Body-JEPA, LP3, Redmi or full V13. Age0 RECORD_ONLY and all original negative gates unchanged.