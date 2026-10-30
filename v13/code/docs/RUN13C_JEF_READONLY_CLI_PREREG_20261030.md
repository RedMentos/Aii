# Run13C — operator-only read-only JEF exact SourceRef CLI (2026-10-30)

Review-only child of Run13B #1289 software GREEN, exact parent `38e02285d4e27f9b4e27b5ad45ea1f7fa3b750f5`. Owner GPT-6. Files owned: new `v13/code/scripts/jef_budget_exact_readonly_run13c.py`, `v13/code/tests/test_jef_budget_exact_readonly_run13c.py`, this document, scoped BUILD_STATE and dedicated CI workflow. Existing `v13/store.py`, `runtime.py`, `budget_en_source_shadow.py`, `budget_answer_shadow_run13b.py`, native scorer, seed211 and Canon are frozen.

## Goal and verification

Run13B demonstrated a software-only human-readable exact budget answer on eight frozen source tasks, but no operator interface. Expose an explicitly invoked existing-home CLI that accepts **both exact Store SourceRef JSON objects**, verifies their source rows and byte-hashed blobs without creating a Runtime or taking its exclusive coordinator lock, and uses Run13B SHADOW renderer. This is a narrow offline/TTY operator aid, not active live answer delivery or C5 authority. Read-only SQLite URI, query-only PRAGMA, no persistent source inserts/updates, bounded no-symlink blob reads (plain or zlib-archived), fail closed on missing/revoked/cross-home refs.

Prospective controls: real Store created by existing Runtime; both refs produce the exact answer and no new source rows, with the original 8/8 seed211 answer-form signal unchanged. Test CLI subprocess invocation, revoked source, wrong home, foreign project, malformed refs, corrupt blob, symlink blob, and compressed archived blob. Source ref values are operator-provided, not fabricated from free-form text; no broad semantic claims. An exact original SQLite snapshot may still race with a concurrent revocation after the final read; do not claim durable dispatch authorization. No native/model downloads, no user data publication, no device changes.

Source-only GitHub Actions must run new tests plus Run13B and original Run13A prereg, py_compile, Canon pin, privacy/diff, original raw and SHA256SUMS even on RED. Private Library backup byte-verified when possible. All negative gates remain Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi UNMEASURED, whole-system incomplete. No fullsuite waivers.

Next after GREEN: independently review CLI against actual SQLite WAL/archived blob semantics and measure repeated read-only invocations with a running coordinator. Only then consider a separately preregistered, explicitly user-approved UI path with C5 egress revalidation. Never silently activate it.
