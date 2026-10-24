# Run47 preregistration — Sleep TTT consumer-time lineage revalidation

Parent Run46 `b1951ad8c97e508aa1a9314f2089855f5dec2fe9`. Ownership exclusively `v13/code/docs/proofs/continuation-20261024/ttt-consumer-revalidate-run47/`; no production, Run42–46, Body/JEF or original gates modified.

Problem: even a source-valid Sleep TTT export becomes stale when an input, transitive context source or fixed-answer rule is revoked after export but before the training consumer reads it. The Run42 export is only CANDIDATE_NOT_TRAINED; no authorization to train is implied.

Implement an isolated fail-closed loader that recomputes the exact Run42 stage_ttt candidate set with current `native_history` at **consumption time** (exact upstream history blob `05455f297205b40fe8e0f818c4657f1fedcd9fa3`, Run42 staging blob `8dcd4b36cbe58f06ea330a510f1735b37f0ad600`). Accept a selected export row only when it matches the current freshly verified row byte-for-byte in all material fields; reject duplicates, unknown IDs, tampering, non-candidate statuses, revoked target/context/transitive source, removed fixed-answer rule, and malformed JSON. On any invalid row, reject the **entire batch** (no partial training). No weights or Age rights; actual trainer must still pass WP-I retention, human approval and native runner proof.

Predeclared tests with exact native_history function and a deterministic fake Store: valid export passes, repeated deterministic pass, target/context/transitive revocation fails, fixed-rule removal fails, edited target/context/status fails, duplicate row fails, stale/unknown session fails, malformed JSON fails, empty export is empty/no-op. Preserve negative attempts. No native model or real Runtime/Store proof.

Original gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE.
