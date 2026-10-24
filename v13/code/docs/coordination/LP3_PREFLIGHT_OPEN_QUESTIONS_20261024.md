# LP3 preflight — unresolved items, 2026-10-24

## USER_DECISION_REQUIRED
None. No new user authorization is needed for the isolated software review.

## HARD_BLOCKER
- Exact seven-file pinned LFM2.5-350M snapshot is absent in the current 4-GiB container. Revalidate native host model bytes and exclusive job ownership before any native run.
- Full repository checkout is not mounted here; full regression and public-repo privacy scanner remain unexecuted.
- Redmi-specific sustained thermal/RSS/KV/energy proof needs a real Redmi session; Linux software tests cannot substitute.

## RESEARCH_NEEDED
- Independently authenticate tokenizer/config/chat-template hashes against the pinned upstream revision (current run manifest binds local bytes, not their upstream identity).
- Seal per-seed native raw outputs with externally persisted Git blob or SHA receipt; the original aggregate-only LP3 audit does not detect coordinated rewrites.
- If memory-key cohort supports utility, design a new, matched-budget generated-answer consumer experiment before changing any JEPA gate.

## CAN_DECIDE_AUTONOMOUSLY
- Review this candidate against the complete repository, run the full test suite and privacy scanner, and verify SHA bindings.
- Recheck the native host prerequisites; execute the already registered LP3 four-seed cohort only when they are present and no other owner is running a heavy job.

## UNCHANGED
STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; no runtime authority; canonical_architecture_complete=false; user_full_scope_complete=false.
