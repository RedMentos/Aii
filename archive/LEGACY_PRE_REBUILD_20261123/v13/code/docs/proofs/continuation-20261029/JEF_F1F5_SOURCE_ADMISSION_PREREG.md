# JEF F1/F5 human-memory source admission — prospective SHADOW prereg (2026-10-29)

Owner: GPT-6, isolated child of #1081 exact head `bf121ae56164a6a77a186dd8456e935e7bb389f9`. This file is committed before implementation or new tests. Previous #1081 proves Store SourceRef integrity and deterministic 36/36 complete-source software decisions, but **not human authorization**. This package closes that separate admission prerequisite without enabling live output.

## Exact authority and identity contract

Add a **default-off, read-only SHADOW** wrapper that accepts `Memory`, an explicit session, a current authoritative `event_id` and its exact full `source_ref`, plus exactly two distinct active `memory_id` values. The current event must exist in the named session with `EventEnvelope.authority=AUTHORITATIVE`, `kind=USER_TEXT`, and exact packet SourceRef equal to the supplied current_ref. Require current source text to match the bounded project/domain request grammar.

For each memory ID, require an existing materialized key SourceRef (do not create one during admission), `Memory.candidate(id, session)` active session-scoped fact, `Memory._verified_rows` F1 MemoryRecord **and** F5 HumanDecision **and** feedback lineage, full SourceRef/sha, exact expected topic key `Project <ID> archived <domain> policy` or `Project <ID> latest <domain> option sheet`, and `value` identical to the corresponding Store source. Reject global memory, cross-session memory, stale/superseded memory, missing F5, duplicate/conflicting active same-topic memories, deleted source, tampered packets/refs, partial current refs, wrong project/domain and any missing side. **Never trust caller-supplied keys, IDs or an unverified text snippet as authorization.**

After admission, call the previously tested `jef_typed_source_shadow.decide` on the verified exact refs. Return the typed SHADOW suggestion and only bounded provenance hashes/IDs; no source text in telemetry. The output always remains `SHADOW_NO_AUTHORITY`, `model_called=false`, `native_calls=0`, `jepa_weight=0`, `user_approved=false` for live execution; **even F1/F5 source authorization does not authorize model/tool/runtime activation**. No mutation of Store or weights during admission. The key-ref materialization prerequisite may occur during explicit record creation, not in the decision call.

## Tests and limits

Use real fresh Runtime/Store and explicit `Memory.feedback(..., kind='fact', permission='record', scope='session')` from authoritative user events, then materialize key provenance once as part of setup. On only the 36 P2X calibration rows, test 36/36 correct full-source and 144/144 UNKNOWN negatives with F1/F5 lineage, source count unchanged during admission, persisted restart, actual forget/revocation, supersession, global/cross-session veto, missing F5 packet/feedback, stale event, wrong current SourceRef and model runner never called. Do not use 72 P2X validation IDs or P0X holdout for tuning. Preserve RED attempts, hashes, source CI and private backup.

This is a software human-source-admission candidate, **not live C3/JEF output authority, not learned JEPA, not Redmi native utility**. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; AG6 unapproved; Redmi unmeasured; V13 INCOMPLETE. Remaining platform budget UNKNOWN.
