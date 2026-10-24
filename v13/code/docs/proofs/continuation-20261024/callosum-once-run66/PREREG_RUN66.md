# Run66 prereg — idempotent B3 Callosum outcome utility updates

2026-10-24. Base Run65 PR98 0d48e8354f442c8badc86cca6074e46d8d166e51. Own minimal `v13/code/v13/callosum.py` outcome callsite, new `v13/code/v13/callosum_outcome_once.py`, `v13/code/tests/test_callosum_outcome_once.py` and `v13/code/docs/proofs/continuation-20261024/callosum-once-run66/*`. Do not edit history, Sleep, World-Model, native LP3 or model cohorts.

Source observation: `Callosum.outcome` records `m['scored']=True` after a successful utility update, but the next call reads and scores all pending messages again without checking that marker. Repeated finalization, crash/retry or concurrent callbacks can multiply learned channel counts and utilities, violating B3-H9 measured baseline integrity.

Proposed fix: a small pure helper applies scored utility records to the current persisted pending list only if each packet id is unscored, marks exactly updated messages and deduplicates packet IDs. Call it inside the existing optimistic Store state mutation, return actual applied count, not speculative precomputed count. Do not change channel policy, latent gates, feedback rights, B3 L1 status or user permissions. Human rating updates remain separately governed.

Predeclared tests: same-event replay idempotence, duplicate packet IDs, only matching scored packets marked, missing pending no-op, stale precomputed score list after concurrent state update no-op, existing utility values unaffected on replay, Python -O. Original repeated-scoring RED and source hashes retained. Actual Callosum/Store integration test requires complete checkout; distinguish tests. Gates STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE.
