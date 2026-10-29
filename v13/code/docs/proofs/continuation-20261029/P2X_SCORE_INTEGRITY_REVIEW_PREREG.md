# P2X native validation scorer independent paired-integrity review prereg — 2026-10-29

Owner: GPT-6 isolated reviewer, branch `assistant/v13-p2x-score-integrity-review-20261029`, exact parent PR #1074 source head `c0ee5b389fafb9adc11929f8b942bea6a0679b5a`, scorer Git blob `e9b2f7604a0b11eb333b844b53153c2cb8f8b8bc`, tests Git blob `5fb30944a38c050414cae5927691ee3408241a9b`. Commit this prereg before changing source/tests or inspecting any future native model output. No model calls, adapter activation, P0X holdout or production merge.

## Observed source-only integrity gap
`score()` validates each of 360 raw calls, computes per-arm totals and details. But `compare(base,candidate)` accepts score dictionaries with pinned schema/model/runtime/fixture/adapter metadata and 360 count **without checking** that their `per_arm` aggregates agree with `details`, that there are exactly 72 distinct paired ID hashes in fixed five-arm order, or that the candidate's oracle/ID order matches base. A tampered summary could report a fabricated positive `both_exact_delta` while retaining otherwise valid metadata. This is a report-integrity issue, **not evidence that the existing real model output was tampered with**.

## Prospective independent repair
- On this isolated child branch, harden `compare` to recompute the per-arm exact/wrong_committed/unknown/unparseable counters from all 360 detail rows; validate strict action/kind/expected consistency, exactly 72 unique 64-hex ID hashes × five frozen arms in order, no duplicate/missing/reordered pairs, same ID hashes/oracles across base and candidate, pinned negative-gate flags and identity metadata. Keep original scoring semantics, frozen source/seed/model/runtime hashes, and no new acceptance threshold.
- Add adversarial source-only tests proving a forged aggregate, wrong oracle, duplicate or reordered IDs, cross-candidate mismatch, forged negative gate, malformed kind/parsed fields all fail; original legitimate base-vs-adapter score must still compare.
- Run exact-remote focused tests with privacy/diff and raw evidence; preserve original RED attempts. This is a strict descriptive report integrity guard, **not a cryptographic signature** and cannot prove raw native execution without separately bound original raw evidence.
- Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, AG6 unapproved, Redmi unmeasured, V13 INCOMPLETE. No production merge.

Next command: patch scorer and tests on review branch; run source-only CI and verify original raw artifact. Remaining platform budget UNKNOWN.
