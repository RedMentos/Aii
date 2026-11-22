# QA & Android — same-turn B1/B2 fair-budget acceptance

**Date:** 2026-11-22  
**Base:** release-development `c2e7ae7ebe47af6ea96995c7df112872bb404d38`  
**QA branch:** `qa/v14-fair-budget-acceptance-20261122`  
**Current PR head before this handoff refresh:** `70f96ee6f416bc05a4e0b3fe4590cc009209ffd2`  
**Scope:** test-only; no production Runtime, model, weight, permission, updater or device mutation.

## Why this exists

The earlier admission-only QA draft #2277 was never executed. This successor runs the admission boundary and fair-slice checks against the exact final staged Runtime, on top of the current release head. It complements the existing source-bound B1/B2 → C4 → C3 staged Runtime/SQLite regression; it does not replace or simplify either body.

## Added acceptance cases

1. Both B1_DETAIL and B2_GIST reach the source/generation boundary under two recent C3 zero-token prefill failures, with cumulative role deadlines of 6.75 s / 13.5 s and the 16.5 s C3 reserve preserved.
2. A legitimate sub-one-second B1 slice is deferred as POSTCOMMIT_ELIGIBLE while B2 retains a same-turn eligible slice. The test checks per-role deferral/budget telemetry and the bounded failure-metadata query.
3. A 90 s turn with a 40.5 s observer window and 35 s per-body cap is tested in both A_THEN_B and B_THEN_A sequential orders. Each role receives 20.25 s when the first role consumes its complete fair slice.

The existing staged Runtime/SQLite regression still asserts source-bound OfferPacket → C4 selection → C3 consumption and B1-timeout→B2 same-turn fallback.

## Exact-head CI

Final tested code head: `70f96ee6f416bc05a4e0b3fe4590cc009209ffd2`, rebased onto c2e7 with no force-push; compare 6 commits ahead / 0 behind, four QA-owned files changed.

- **6 SUCCESS / 0 FAILURE / 0 pending / 1 expected SKIPPED**
- PASS: focused consumer Python 3.13 and 3.14; staged-runtime; integrated-regression; same-repo integration; offline-bridge security.
- Expected skip: strict additive-only validator, because this PR deliberately extends existing workflow/test files. No gate was bypassed.

The release-development base c2e7 itself has 39/39 exact-head check-runs SUCCESS. Neither result is local full-suite or Android evidence.

## Environment and proof boundary

- No full Aii checkout was available in the local workspace; no LOCAL_LINUX full-repository suite is claimed.
- GitHub CI executed the staged Runtime/SQLite and synthetic clock/Store/model-boundary tests on Python 3.13 and 3.14.
- No native GGUF generation, useful native B1/B2 offer, semantic latent alignment, Android execution or Redmi performance is proven by these tests.

## Latest authenticated phone evidence

Private owner-authenticated receipts #504/#505 (2026-11-22 08:28Z) reported:
- installed SHA `c03ff0aa9e18b5ffebd1109f3c078105f53c6afe`; auto-update/runtime/dashboard UP_TO_DATE;
- B1_DETAIL and B2_GIST native probes still TIME_BUDGET;
- latest recorded turn 63.22 s total / 42.48 s TTFT / 34.96 s prefill, 709 prompt tokens and 2 generated tokens; the redacted input does not permit a correctness inference.

The later release-development head c2e7 has no authenticated installation receipt. No UPDATE_REQUEST, CHAT_SEND, LOG_PAGE, shell, model/weight change, permission change or device mutation was made. This test-only PR does not require an update.

## Next step

Boss/Core independent review and integration decision. The P0 Redmi gate remains open: a separate consented 20-turn run must measure correct final answers, native B1/B2 source-bound offers consumed by C4/C3, TTFT/prefill, PSS/residency, restart and rollback. Do not count post-commit offers as same-turn contribution.