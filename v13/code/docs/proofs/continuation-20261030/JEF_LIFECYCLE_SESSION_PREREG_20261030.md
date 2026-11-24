# V13 N3/WP-U1 experience lifecycle current-chat boundary — preregistration 2026-10-30

## Authority and frozen base
Review-only child of PR #1174 source head `917c2c7d9d717426facd0bc6f98b126af3a4ece3`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. This package owns only `v13/code/v13/jefoutcome.py`, new `test_jefoutcome_session_20261030.py`, this prereg, a narrow workflow, and a build-state delta. Do not change registered models, source cohorts, existing failures, gates, Age-0 defaults or approval. Do not touch any other owner's branch.

## Problem / expected original RED
`:fastpolicy lifecycle <Event-ID>` calls `jefoutcome.lifecycle` with an arbitrary event ID, which currently checks only `events.id`. `:fastpolicy lifecycle` summary also selects all global `ExperienceRecord` packets, not the current chat. A second local chat can therefore inspect another chat's lifecycle stage, update IDs, and experience count. Other JEF/Context OS operator commands already enforce the current-session boundary.

## Before-source regression
1. Create two sessions in the same real SQLite Runtime/Store; create an `ExperienceRecord` packet for each with their actual EventEnvelope. In the first chat, both direct lifecycle and operator lifecycle must accept the own event.
2. Switch to the second chat. `:fastpolicy lifecycle <first-event>` and direct `lifecycle(r,first-event)` must reject `CURRENT_SESSION_EVENT_REQUIRED` and not reveal any stage/update IDs; own event still works.
3. `:fastpolicy lifecycle` summary must count **only** the current chat, with correct L0 stage counts; verify the first chat's count is unchanged after switching back.
4. After closing/reopening the SQLite Runtime, verify session-local summary and foreign-event rejection persist; no models, native runners, tools, or learning invoked.
5. Unknown IDs reject and empty new chat reports zero. Existing `test_jefoutcome`, JEF session and Context OS session tests remain compatible.

## Implementation constraint
Bind event lookup and summary packet scan to `r.session` using explicit SQL joins to `events.session_id`. No filtering in Python after a global `LIMIT` (would silently lose own records); limit applies after SQL scope. Keep read model read-only and historical non-operator helper semantics only if explicitly required by callers; do not add authority.

## Evidence and gates
Preregister before test/source. Focused isolated stdlib+minimal deps CI; preserve original RED and GREEN raw, exact head, Canon hash, source blobs, exit codes, privacy scan, diff check and SHA256SUMS. No full-suite, native, Redmi or whole-system promotion. PR #1174 unfiltered full-suite has historical frozen Run34/Run37 source-preflight errors and is **not** a blanket GREEN proof. Next: run targeted tests, independent review of SQL and cross-session counterexamples, then checkpoint and continue a distinct organ.
