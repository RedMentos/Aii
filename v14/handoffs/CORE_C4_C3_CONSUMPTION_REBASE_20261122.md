# Core handoff — same-turn C4 → C3 consumption on current Boss base

Date: 2026-11-22

## Ownership and exact base

- Lane: Core & Harness.
- Branch: `core/v14-c4-c3-consumption-rebase-20261122`.
- Base: Boss integration PR #2288 branch `boss/v14-recall-store-pin-rebind-20261122`, starting SHA `f0d3c848dfb1d65e282f065233adbe3c9205e439`.
- The branch is stacked on #2288 and is not a release branch.
- Shared V14 board, active master, historical Canon and Perception-owned raw Cognition/audio sources remain untouched.

## Runtime change

- New Core-owned staged overlay: `v13/code/scripts/integrated_c4_c3_receipt_candidate_20261122.py`.
- The existing pinned recovery wrapper applies it **after** the reviewed base, observer-fairness and A5 audio compositions.
- It emits `c4_offer_context_ready` only after source-validated selected OfferPackets have been assembled into the C3 context.
- Receipt fields are limited to `role=C3_LANGUAGE`, selected OfferPacket IDs, count and PASS. No prompt, source bytes, quotes, summaries or user text.
- This means context-ready at the C4→C3 boundary, not proof that a native model semantically used the context.
- The original `cognition.py` and A5 audio candidate bytes were restored to their exact base blobs; this avoids invalidating the observer overlay's pinned source contract.
- Downstream pins were read back: receipt overlay SHA-256 `0f3aab12b64454eaa3b49ce4adf22e8a29aeae081c5f82e8376e54a22028dff3`; wrapper SHA-256 `00fe663fb7c2828788af5799b26c374bd9604ecaf480bb00c3c85fd1d8f20c3b`; stage SHA-256 `d4f4b28d6342b7fb60005f7cd0949292fd9947c1ea870e273eece820dfcdbd0e`; deployer pin matches stage.

## Regression and discovered test-target issue

- The first exact-base CI attempt ran the test against raw source. Python 3.13 failed because raw `native_turn_budget.py` uses the pre-overlay recovery policy, which deliberately defers pre-answer B passes after two recent C3 zero-token failures.
- The actual pinned candidate applies the reviewed observer-fairness overlay at staging time. Its /2 policy preserves the bounded 45% pre-answer window and divides it into sequential B1/B2 slices while reserving the remaining 55% for C3.
- Therefore the regression must run against the **composed candidate**, not raw source. The raw-source test target was invalid; it did not establish a product regression.
- New runner `v13/code/scripts/run_c4_c3_current_candidate_test_20261122.py` calls the exact pinned base+observer+A5+Core wrapper with `include_postcommit=False`, copies the composed modules into an isolated temp Runtime, then runs the same Runtime/SQLite/Focal/Cognition test and its tampered-OfferPacket negative control.
- Only the known postcommit overlay is skipped because Boss #2288 currently tracks a separate postcommit pin-order failure. This focused test does not claim the full production stage passes.

## Test and deployment boundary

- Earlier raw-source attempt: CI Python 3.13 FAIL (invalid test target; no C4 receipt because the staged fair-budget overlay was not applied).
- Corrected composed-runtime workflow: new exact-head Python 3.13/3.14 runs pending after this commit.
- Full `stage_integrated_candidate.py` / integrated deployment remains blocked by the separate upstream #2288 postcommit pin-order failure; report it separately from this Core test.
- LOCAL_LINUX full-repository tests: BLOCKED. The execution container has no Aii checkout and `git ls-remote https://github.com/RedMentos/Aii.git HEAD` failed because github.com DNS did not resolve.
- TERMUX/REDMI: REDMI_UNVERIFIED. Latest private PIPELINE_STATUS request #453 had no authenticated reply; installed SHA and updater consent remain UNKNOWN.
- Release: NOT_RELEASED. No deployment, model/weight, Age, permission, updater or user-data change occurred.

## Next action

1. Read the corrected exact-head Python 3.13/3.14 runs and fix any real regression.
2. Keep the full stage/postcommit pin-order failure assigned to Boss/Integrator; do not mask it in the Core test.
3. If Boss advances #2288, create a new current-base rebase branch rather than force-pushing.
4. Boss/Integrator should integrate this Core slice into #2288 and refresh the shared board/workplan/user-next-action.
5. Then continue the separate Core V14-003 native input-embedding receiver experiment; production B3 remains OFF until native receiver utility and negative controls are proven.
