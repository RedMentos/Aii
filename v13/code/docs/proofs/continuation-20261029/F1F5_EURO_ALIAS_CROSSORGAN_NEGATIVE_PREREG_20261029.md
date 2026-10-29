# F1/F5 Euro alias independent source lifecycle negative controls — 2026-10-29

Parent checkpoint: `cc2fcdaf007d74a4cbfdc2c8a01e6fa476284132` / PR #1157,
focused prior workflow `40963256311` GREEN. Review-only test extension.

## Frozen hypotheses before CI
1. Two valid same-value aliases permit `:verified exact` source output.
2. If the second independently active correction's F1/F5 blob is tampered,
   the **real recall_and_admit → exact_source** path refuses with CLARIFY and
   never calls C3, despite the first valid matching correction. A direct
   supplied candidate list is not authoritative for this lifecycle.
3. If the second alias is explicitly revoked, the first remains independently
   verifiable and the exact source output is delivered without native C3.
4. All original contradictory-amount, foreign project/currency, native answer,
   privacy, Canon and Age0 negative checks remain unchanged.

Execute focused software CI using the pinned existing workflow and preserve
original raw test output with SHA256SUMS. This does not constitute Linux-native
or Redmi evidence and promotes no STEP2, B3, Body-JEPA, LP3 or whole-system gate.
