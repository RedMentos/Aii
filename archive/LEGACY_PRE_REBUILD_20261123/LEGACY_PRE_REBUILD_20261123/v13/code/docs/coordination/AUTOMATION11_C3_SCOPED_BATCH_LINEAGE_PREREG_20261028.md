# Prereg: batch F1/F5 verification for bounded C3 exact-key conflict scan (2026-10-28)

Owner: independent ChatGPT review-only child of integrated #896 head `c6cc1bf4a4c6b72948494366dad9a3d7670b7ad4`. Before code edits, `recall_and_admit` calls `Memory._verified_rows([fresh])` once **per active scoped row** (up to 256), and `_verified_rows` scans all MemoryRecord/HumanDecision/feedback packets each time. This is an avoidable O(scoped_rows × packet_history) read amplification on the 6GB-class phone; it does not change safety authority.

## Locked change and tests
- Keep exact same bounded SQL, SourceRef checks, 256-row cap and fail-closed semantics. Read each active scoped candidate once; verify the whole set of candidates with **one** `Memory._verified_rows(scoped)` call. Require every candidate ID to be returned exactly once; if any unreadable, duplicate, missing or unverified, return `CLARIFY / UNVERIFIABLE_SCOPED_CORRECTION`. Never treat a missing candidate as permission to answer.
- Add a deterministic software test with two active same-project corrections and mocked `Memory.recall` returning only the first, instrumenting `_verified_rows` to prove one batch of length 2. Existing conflict, corruption, missing F1/F5, revocation, renderer seal, CLI postflight and no-native refusal tests must remain GREEN.
- Run source-pinned focused and full software suite, compile, privacy/diff, raw artifact SHA256 audit. No native run or performance speedup claim without measured timing. This package reduces redundant verification calls structurally, not measured Redmi latency.

## Gates
No change to frozen runtime, model catalog, seeds, learning/age/approval. No original Stage11/STEP2/B3/Body-JEPA/LP3/Redmi/full-V13 promotion. This remains a review-only scoped C3 source consumer; normal Runtime._turn not integrated.

Next after software GREEN: compare exact source and performance on a real phone when available; integrate only via reviewed lineage.