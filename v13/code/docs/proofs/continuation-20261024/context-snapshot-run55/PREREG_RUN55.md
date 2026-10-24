# Run55 / Context OS atomic native_history snapshot — preregistration

Date: 2026-10-24. Base: PR88 `a90acdc3ab3ab3fa7646a2d1634750f527d02853` (draft, unmerged). Owned paths: `v13/code/docs/proofs/continuation-20261024/context-snapshot-run55/*` only. No other owner's production edits.

Problem: PR88 native_history verifies current fixed-rule/source lineage using separate Store calls. It holds Store.mutex only for the initial rules read, so another thread or external SQLite connection can revoke source lineage between reads, producing a non-atomic history view. Run53/54 tests did not prove concurrent revocation. This is a scoped read-consistency candidate, NOT a permanent source lease or training authority.

Exploratory software prototype and 12/12 synthetic SQLite tests were executed **before** this prereg; they are disclosed as exploratory, not preregistered evidence. No threshold or gate is promoted from them.

Predeclared new tests: (A) source-shaped unprotected history read permits writer to revoke between two read phases; (B) guarded read holds BEGIN IMMEDIATE and blocks an external SQLite writer until commit, without deadlock; (C) Python `-O` preserves guards; (D) separate-process SQLite writer is blocked during the snapshot; (E) malformed Store contracts and busy writer fail closed. Success = all new and exploratory tests pass on Linux SQLite; failure logs retained. Native Store/Runtime/Redmi, full repo suite and official privacy scan are separate pending proofs.

Design: opt-in wrapper around **unchanged** `v13.history.native_history`, using `Store.tx()` (existing RLock and `BEGIN IMMEDIATE`) to pin all SQLite source/rule/event checks into one transaction; final SourceRef re-read inside the transaction. This blocks SQLite writers during a bounded history read, not after return. Consumer-time revalidation remains required for Sleep/TTT and any training/answer commit.

Original gates unchanged: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; V13 INCOMPLETE. No Age authority, no real weights, no automatic activation. Research: https://www.sqlite.org/lang_transaction.html and https://www.sqlite.org/isolation.html (access 2026-10-24). 
