# Run11 independent Store SHADOW use-boundary proof plan — 2026-10-28

Parent: Run31 PR #937 exact commit `096d7a9d7d1fcdcc74e21d3bb690544b197e09b5`. New files only; do not edit active Run31, Run29, Run24, Runtime, Store, original cohort, model, seed, or canonical gates. Separate ownership: `scripts/run11_store_shadow_use_boundary.py`, `tests/test_run11_store_shadow_use_boundary.py`, one new workflow, and this handoff.

Problem: Run31 validates persisted source identity while computing a deterministic German typed SHADOW result, but the returned candidate is not tied to a subsequent read-only consumer. An event/message can be revoked, changed or reordered after return. A self-hash does not confer authority.

Hypothesis: an explicitly untrusted, in-memory snapshot plus a second live Store read immediately before SHADOW-only inspection can refuse stale/revoked original user messages, source/sequence changes and candidate mutation. It must NOT promise atomicity after inspection, F5 authority, model utility or side-effect safety.

RED-first tests: clean candidate and restart read; then mutate source tombstone, original user message status/text/metadata, event rowid without source hash change, candidate action/hash, wrong Store/session/project and malformed ticket. Test no model or external action. Expected RED before module exists. GREEN needs same focused suite, Run24/28/29 regression tests, compile, full suite, privacy scan, exact parent/donor source pins, closed raw CI artifact, independently audited stage exits. No hidden private data in repository.

Implementation contract: `seal_candidate` captures live per-role event sequence and source hashes before and after existing Run31 `bridge.evaluate`; `inspect_shadow` revalidates original sources, recomputes deterministic candidate, compares against sealed snapshot, and revalidates once more before returning an untrusted SHADOW-only diagnostic. Reject every mismatch. It must never authorize Runtime, tools, training or output; post-return concurrent revocation remains unsolved.

Gates remain Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi unmeasured; canonical architecture and full scope incomplete. Remaining platform budget UNKNOWN.
