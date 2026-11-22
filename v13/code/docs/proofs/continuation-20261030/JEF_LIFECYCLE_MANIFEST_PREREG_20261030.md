# JEF WP-U1 lifecycle update provenance exact-source match — preregistration 2026-10-30

Parent review #1175 exact `e19cafa81b7ddc658e1da39d5591bfc9d0dc5df4` (verified remote). Own only `v13/code/v13/jefoutcome.py`, new `tests/test_jefoutcome_manifest_20261030.py`, focused workflow and evidence delta. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` immutable; no source/model/cohort/gate changes.

## Failure hypothesis
`jefoutcome.lifecycle` currently associates any `updates.manifest` with an experience when its **raw JSON text** contains one of that experience's feedback/source IDs as a substring. Unrelated free-text comments, longer fake IDs, string-typed `source_ids`, and malformed JSON containing an ID can falsely assert L4 proposal, L5 shadow learning, L7 validation, L11 reopen, or even L9 promotion. This is an evidence-integrity failure, not just formatting.

## Original RED-first controls
- Real SQLite Runtime with current-chat event and real feedback source ID. Insert a synthetic update row (no training/model) with `source_ids=[]` and an unrelated `note` containing the ID; L4/L5/L7/L11 must remain false.
- Repeat with `source_ids=[id+"-foreign"]` (substring trap), `source_ids=id` (wrong type), malformed JSON containing the ID; all must remain unlinked.
- Insert an exact `source_ids:[id]` manifest and verify L4/L5/L7 accurately reflect that update's status, without inferring L9 promotion.
- Confirm wrong-source update does not get attributed even if it has `status=APPROVED` or `ROLLED_BACK`; verify retained restart behavior and current-session boundary from #1175.
- No original failure or frozen preregistration rewritten.

## Repair and evidence
Use parsed JSON object with **typed list** `source_ids` containing exact source-ID strings. Fail closed for malformed/missing/non-list IDs. Never search serialized manifest bytes for provenance. Keep existing read-only API and status semantics. Narrow CI (JEF lifecycle manifest + session + existing JEF tests), original RED and GREEN raw, source/Canon blobs, complete SHA256SUMS, privacy/diff/compile. Historical Run34/Run37 full-suite RED and STEP2/B3/JEPA/Redmi/whole-system negative gates remain.
