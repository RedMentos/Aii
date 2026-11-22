# QA & Android — same-turn B1/B2 fair-budget acceptance

**Date:** 2026-11-22  
**Base:** release-development `c03ff0aa9e18b5ffebd1109f3c078105f53c6afe`  
**Branch:** `qa/v14-fair-budget-acceptance-20261122`  
**Scope:** test-only; no runtime source, model, weight, permission, or device mutation.

## Why this exists

The earlier QA admission test in PR #2277 was source-reproduced on an older Core candidate but never executed. The current release already contains the pinned fair observer overlay. This successor runs the admission boundary and fair-slice checks against the exact staged Runtime on Python 3.13 and 3.14.

## Added acceptance cases

1. Both B1_DETAIL and B2_GIST reach the source/generation boundary under two recent C3 zero-token prefill failures, with distinct 6.75 s / 13.5 s role deadlines and the 16.5 s C3 reserve preserved.
2. A legitimate sub-one-second B1 slice is deferred as POSTCOMMIT_ELIGIBLE while B2 retains a valid 6.75 s same-turn slice. The test checks the per-role deferral/budget telemetry and bounded failure metadata query.
3. A 90 s turn with a 40.5 s observer window and 35 s per-body cap is tested in both A_THEN_B and B_THEN_A sequential orders. Each role receives 20.25 s when the first role consumes its complete fair slice.

The existing staged Runtime/SQLite suite remains responsible for the downstream source-bound OfferPacket → C4 selection → C3 consumption assertion.

## Evidence boundary

At branch creation, no local Aii checkout was available; the full local repository suite is therefore not claimed. GitHub Actions is configured to execute the stage and these tests on Python 3.13 and 3.14. All model generations are synthetic; this does not prove native model timing, actual useful offers on the Redmi, or 20-turn quality/TTFT/PSS acceptance. Redmi remains `REDMI_UNVERIFIED` for this change.

## Next step

Review exact-head staged/integrated CI. If green, ask Core/Boss to consume this independent QA evidence in the shared P0 acceptance ledger. Do not issue an updater request: the installed phone is already at the docs-only current SHA and the fair-budget code is not changed by this PR.
