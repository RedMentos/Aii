# Run150 — persisted V13 source-bound AGE0d history audit

**Canonical interface:** Read-only diagnostic script `scripts/age0d_history_shadow_audit_run150.py --home <V13_HOME> --session <exact session-id> [--limit 100]`. The user must explicitly run it. No Runtime/Store/Canon edits; no new command in the live chat UI.

**Evidence path:** SQLite `data/db/brain.sqlite3` opened with `mode=ro` + `PRAGMA query_only=ON` and a read transaction (including live WAL visibility). One exact session only. For each candidate event require queue `DONE`, exactly one FINAL user and one FINAL assistant, same session, unchanged SourceRef in EventEnvelope and user metadata, original blob SHA-256, full source text and undeleted source. Refuse missing/deleted/tampered sources, cross-session messages, ambiguous finals, symlinked blobs, and unsafe DB symlinks. Only then run the isolated Run149 SHADOW arithmetic evaluator. Output aggregate counts, no raw prompts/answers/session identifiers.

**Tests:** 15 cases, including valid/incorrect arithmetic, cross-session isolation, pending/deadline exclusion, source tamper, blob symlink, duplicate finals, DB byte preservation, limits, DB symlink, parent directory symlink, WAL and **actual V13 Store integration**. Local scratch: 14 PASS, 1 SKIP because full Store package is not mounted; CI must run all 15 on the actual repository. No native model or Redmi run.

**Limitations:** FINAL assistant text might originate from tools, memory or C3; this diagnostic never attributes generation to C3 without independent provenance. No learning, delivery, age promotion, general language or STEP2/B3/JEPA proof. All original negative gates unchanged.

**Next:** Verify exact-head CI with actual Store and privacy scan. After a reviewed save, proceed to broader canonical end-to-end utility, not just arithmetic formatting.
