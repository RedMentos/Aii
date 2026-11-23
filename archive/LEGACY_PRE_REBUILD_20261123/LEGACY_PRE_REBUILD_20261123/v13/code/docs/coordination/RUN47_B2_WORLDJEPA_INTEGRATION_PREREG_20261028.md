# Run47 — independent Run45 + Run46 software integration prereg (2026-10-28)

**Parent:** Run46 review-only #954 exact head `29935afe83feb699c8b547ad6b24a275d7945410`, itself based on Run44 #952 `07f31a288cbade3779b791b22b2d4b10ffb8ba59`. Run46 exact-head CI was still in progress at branch creation; this integration is a candidate, not a preemptive GREEN claim. Run45 review-only #953 exact GREEN head `2c4b40e6ffc2cc051fcd3f1776af1a81c1e803df`, Actions `40746473146`, 32 focused/2553 full OK (1 skip), original ZIP SHA256 `1e7aba366f9394832ba1ac47e9382991a5030125799cecae2fbadd4d13cbf5de`, 15/15 hashes.

**Problem / goal:** Two disjoint independently reviewed packages remain sibling PRs: Run45 stopped-home B2 SHADOW blob-FD containment and Run46 World-JEPA zero-step confidence/checkpoint provenance. A branch-scoped combined source tree is needed to prove that neither candidate regresses the other's focused tests or the complete V13 Linux software suite before any integration discussion. This is not a runtime authority or native model proof.

**Candidate:** retain Run46 files exactly, copy Run45's four changed/added files byte-identically (run44 CLI, run45 test, prereg and workflow) from #953. No source logic edits, model/seed/fixture/cohort changes, Canon changes or production main merge. The Run45 workflow still triggers only on its original branch; add a separate Run47 source-only CI triggered on this integration branch. All original negative gates retained.

**Acceptance:** verify remote Git blob SHAs for both source families against independently verified parents; focused Run45 + Run46 + Run44/42/40 + WorldJEPA checkpoint/reader/atomic tests; full Linux software suite; frozen original eligibility/run42/run40 hashes; compile/privacy/diff; raw ZIP SHA256/CRC/inner SHA256SUMS and all exits 0. Require Run46's original exact-head raw proof independently GREEN too. No native/Redmi evidence, no new action authority. Preserve all failed attempts.

**Gates:** Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, Redmi UNMEASURED, V13 incomplete. Remaining platform budget UNKNOWN.
