# Run107 — Fast episodic route SourceRef/lineage integrity (preregistered)

Date: 2026-10-25 UTC. Base: Run105 PR #137 `81f7d5f837530d38e8f2ee5c150905c9bcd8f03c`. Independent package. Owner exclusively `v13/code/v13/episodic_route.py`, new `tests/test_episodic_route_source_run107.py`, isolated workflow and `docs/proofs/continuation-20261025/episodic-route-run107/`. Run106 owns `episodes.py`; no shared code edits, no heavy native work, no production merge.

## Problem and expected test-first RED

WP-U10 `suggest` currently consumes mutable SQLite `memories.value` and `key_text` directly to select a route, even though route corrections are human SourceRef-backed and source bytes may be missing or changed. A valid-looking SQLite mutation can silently redirect the ACTIVE episodic route, bypassing C2; the source lineage in the response then points to the *old* decision.

Tests on actual persisted Runtime/SQLite:
1. Valid route value `detail -> gist` mutation must not become an ACTIVE route; shadow also must not present it as valid.
2. Changed key text `Aurora -> Borealis` must not redirect a suggestion to Borealis.
3. MemoryRecord packet key or value-source mismatch must fail closed.
4. Source blob corruption must fail closed even if the memory row still says active.
5. Valid route and explicitly global route survive restart and cross-session scope, with no new MEMORY_KEY sources created by a read-only suggestion.
6. A malformed newer candidate cannot mask an older independent valid candidate.

Expected RED: at least cases 1–4 fail against the immutable Run105 source. Preserve full raw CI log before implementation.

## Narrow fix

Read-only verification of the persisted route memory's immutable value SourceRef, matching MemoryRecord lineage and key, source bytes/hash, and originating authoritative event. Skip invalid rows and continue to another eligible source-valid candidate. Do not grant route authority from malformed packets or a missing source. Do not change the `off|shadow|active` mode, consolidation precedence, route vocabulary, threshold, or human approval.

## Proof limits

Model-free real SQLite + Linux GitHub Actions; no native inference, phone proof, learned semantic utility, or full-system gate promotion. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE. Run107 is a branch-scoped candidate; the binding Canon and all user decisions remain unchanged.
