# Core handoff — fair same-turn B1/B2 pre-answer budget (2026-11-22)

## Ownership and current base

- Owner: Core & Harness
- Branch: `core/v14-fair-b1-b2-preanswer-budget-20261122`
- Current release-development base: `c4eb82deec915f65894c20d6ebbaf0ebf58fa335`
- Rebased by a non-force merge commit; the intervening base commit changed only the JEPA Runtime-port test, not these Core files.
- Scope: keep sequential B1_DETAIL and B2_GIST both eligible inside the existing C3-reserved whole-turn budget, then run a missing peer post-commit when only one body produced an offer. This is a software/runtime candidate; no Redmi effect is claimed.

## Defect and hypothesis

The current `native_turn_budget.plan()` can reserve the minimum C3 window after repeated real zero-token C3 prefill deadlines, but `Cognition.offer()` then blanket-defers every pre-answer B1/B2 pass. The scheduler also gives the first sequential body the whole remaining observer deadline, and the post-commit observer path runs only when `offers` is completely empty. Consequently, one successful body can prevent its missing peer from receiving a later observation.

The fix keeps the existing C3 reserve formula and Age/permission policy. It does not relax the C3 reserve, switch to parallel native loading, remove either body, or alter official Age.

## Runtime changes

1. `native_turn_budget.plan()` accepts an optional per-role observer deadline, caps the role's available slice against the existing C3 reserve, requires strict integer token evidence for failures/successes, and exposes the minimum role slice.
2. Runtime caps the short-turn pre-answer observer window at the measured C3 reserve boundary.
3. Sequential `observer_schedule.run()` allocates the remaining window fairly among remaining roles. Runtime passes each role's individual deadline into `Cognition.offer()`.
4. `Cognition.offer()` defers only if that role's slice is below 1.0 s; otherwise it logs `PREANSWER_BUDGETED` and attempts the source-bound offer.
5. After a FINAL answer, the background path schedules only body roles that did not produce an offer. A missing peer is not suppressed merely because the other body succeeded.
6. Store telemetry allows the bounded budget measurements and statuses without recording user text.

## Tests added/changed

- Native-turn budget: per-role deadline cap, minimum-slice/post-commit boundary, strict positive-token success evidence, boolean-token negative, and a real `Cognition.offer` source-read seam proving a fair slice is attempted while the post-commit path remains available.
- Observer scheduler: deterministic equal-slice allocation and early-finish reallocation.
- Runtime integration: short 30 s C3-recovery window preserves both sequential pre-answer role deadlines inside the existing C3 reserve; when B2 fails pre-answer but B1 succeeds, B2 still receives a post-commit observation.
- Existing schedule order, peer communication, cancellation, parallel-residency and resource-mode tests remain unchanged.

## Verification status

- LOCAL_FULL_REPOSITORY: BLOCKED — no Aii checkout is present; container GitHub DNS resolution fails. No local full-suite result is claimed.
- CI: PENDING exact current-base PR head.
- Runtime tests use a real Runtime/Store with a fake C3 generator and bounded offer seams; they do not execute native GGUF inference.
- Redmi: REDMI_UNVERIFIED for this change. Latest private read-only DIAGNOSTICS reports installed commit `9c7a0ec2d58538be8b7fde9476db299f2a5dd7b8`, not current release HEAD `c4eb82deec915f65894c20d6ebbaf0ebf58fa335`. It records B1/B2 `TIME_BUDGET` 53.2/54.2 s and a prior 63.22 s turn / 42.48 s TTFT / 34.96 s prefill / 2 tokens. That is historical telemetry, not a new post-update user turn or proof of useful offers.
- No model, weights, permissions, Age, user data or updater setting was changed. No phone command or device action was sent.

## Coordination

- PR #1920 is an older, stale first-body half-slice candidate with an incompatible historical base; this current-head package is the replacement review candidate, not an automatic merge.
- JEPA PR #2311 touches different Runtime hunks (worker preemption); this branch only changes pre-answer scheduling and post-commit missing-peer regions. Re-run exact combined integration after any JEPA rebase.
- Boss/Integrator owns shared board, workplan and `V14_USER_NEXT_ACTION.md`; this is the Core-owned evidence path for that update.

## Next action

Run exact branch CI, fix any failures, review the combined Runtime diff against current JEPA changes, then hand Boss a merge-ready PR. After release integration and an authenticated installation receipt, obtain a fresh device turn receipt; no user action is required now.
