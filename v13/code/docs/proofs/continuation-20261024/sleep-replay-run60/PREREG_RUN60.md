# Run60 — §94 Sleep/Wake replay queue and authority separation (synthetic)

2026-10-24. Base PR93 `c252704e2853932b1a01c22327cba60679f31a33`. Own only `v13/code/docs/proofs/continuation-20261024/sleep-replay-run60/*`; no production edits or active owner overlap.

Canon §94: replay item has experience_id, replay_type, priority, evidence_class, unresolved_errors, affected_paths, max_authority, ttl, source_refs. Sleep A real replay + old/new interleave + retention candidate, Sleep B counterfactual proposals with `fact_write_authority=0`, Sleep C trace decay/compaction, Wake high-priority replay only during idle without blocking user-response governor. Age0 rights never promoted by maturity.

Preregistered synthetic tests: (1) bounded SQLite durable enqueue, source hash/range/deleted validation, idempotency and conflicting request rejection; (2) expired/revoked sources never claimed; (3) old/new replay interleave, priority tie deterministic; (4) Sleep B counterfactual can produce hypothesis only, cannot write facts; (5) Sleep C compaction preserves immutable raw evidence and active queue; (6) user_pending/stop/resource-red prevents replay; (7) subprocess crash after claim leaves recoverable lease, no side-effect authority; (8) unauthorized type/age/permission refused; (9) Python -O and repeated concurrency tests. PASS = all, no native/Redmi/full-repo claim. Preserve failures.

No STEP2/B3/Body-JEPA/jepa_weight/full-system gate promotion. Source of truth remains full V13 canon and newer decisions. No automatic user-visible notifications or autonomous external actions.
