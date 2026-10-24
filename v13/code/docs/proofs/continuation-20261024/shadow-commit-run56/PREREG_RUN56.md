# Run56 WP-S7 / shadow delta publication under source-revocation races

2026-10-24. Base: PR89 Run55 `4303ab074cb1ec2d2a8bffea7f1194e058f96dca`. Own ONLY `v13/code/docs/proofs/continuation-20261024/shadow-commit-run56/*`. No production runtime/Store schema modifications, no overlap with PR88 history ownership.

Goal: take a **precomputed shadow-only** local delta and publish an immutable receipt only when every original SourceRef remains active, its SHA256 is unchanged, the base model bytes still match, the active generation matches, and an explicit shadow mode and no-cancel condition hold. This is a prerequisite for §88 L3/L4 and Run48 source-rollback, not proof of native learning.

Predeclared tests: (1) valid shadow commit and independent readback; (2) duplicate request idempotent for identical bytes/refs, reject conflicting reuse; (3) source revoked before commit blocks receipt; (4) writer race serialized by same SQLite BEGIN IMMEDIATE; (5) crash after durable blob before DB receipt yields harmless orphan, not success; (6) crash after DB commit before caller return yields recoverable valid receipt; (7) revocation after commit invalidates readback; (8) tampered delta or base refuses; (9) wrong generation, non-shadow authority, cancellation, duplicate refs, malformed hashes fail closed; (10) Python -O and subprocess Linux tests. Predeclared outcome: 100% tests pass; all failures preserved. No native/Redmi/full-repo claim. Do not promote original gates.

Design: SQLite receipt table in a **synthetic Store-shaped DB** and an isolated content-addressed delta directory; source table and active_generation meta mimic current Store. Blob fsync+atomic publication BEFORE SQLite receipt commit. On crash, orphan is not a receipt; on DB commit, blob exists. Any later use must revalidate sources at consumption. No base writes, no promotion to production weights. Full Store migration/approval integration remains separately blocked pending review.

Canon §88, §89, §94, §95; primary source https://www.sqlite.org/lang_transaction.html (access 2026-10-24). Original gates: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; full V13 INCOMPLETE.
