# Core & Harness — B1/B2 → C4 → C3 recovery-window checkpoint

**Timestamp:** 2026-11-23T23:44:56.033Z  
**Owner:** Core & Harness  
**Candidate:** [PR #2458](https://github.com/RedMentos/Aii/pull/2458)  
**Branch:** `core/v14-fair-b1-b2-preanswer-budget-20261123-run1`  
**Code/test checkpoint:** `e27c035bd6ba4679919a36dff0dda04bc77cb09e`  
**Branch tip at first handoff readback:** `eec84757077d4fc23df5e6079692254cd7080d5f` (handoff/board/next-action commits only after the code/test checkpoint)  
**Base:** `gpt6/v13-private-remote-bridge-20261111` at `8d93236c753f0194224c19edc7411d8d7082b1d6`  
**Status:** DRAFT / NOT_RELEASED

## Root cause addressed

The previous recovery plan reserved most of a short turn for C3 and fairly sliced the remaining window between B1/B2, but it reused the same deadline for initial body work and C4/Focal. If the bodies consumed their full window, C4 could start after its deadline and fail to consume the offers. Focal re-entry was also indistinguishable from an initial pre-answer observer in the budget check.

## Connected implementation

- `native_turn_budget.plan()` now exposes two deadlines: the total pre-answer end and an earlier initial-body end. Recovery-only policy reserves the final 1.0 s of the pre-answer envelope for C4 selection/re-entry; ordinary turns retain their previous shared window.
- `Runtime._turn()` schedules initial B1/B2 passes only before the body end, but gives the FocalLoop the full pre-answer end. A 30 s recovery example therefore reserves 26 s for C3, 3 s for initial B1/B2, and 1 s for C4.
- `Runtime.ask()` marks initial observer calls explicitly. Focal re-entry is marked separately and can use the C4 reserve rather than being rejected by the initial-body cap.
- `Cognition.offer()` accepts the explicit pre-answer flag while retaining the previous default behavior for other callers.
- The focal-reserve metric is added to the Store telemetry allowlist and covered by a regression assertion.

This preserves both B1/B2 roles, C4, the C3 reserve, official Age, installed models, weights and permissions. It does not claim that a 1 s slice is enough for a real native body inference.

## Tests and evidence

- **LOCAL_SYNTHETIC — PASS:** Python prototype checked the 30 s recovery split (26 s C3 / 3 s initial bodies / 1 s C4), per-role deadline capping, expired-slice deferral and fair sequential allocation.
- **Repository pytest — NOT_RUN:** this execution environment has no Aii checkout and GitHub DNS/clone access failed. The project tests were added/updated but were not executed locally.
- **Exact-head GitHub Actions — BLOCKED / startup_failure, zero jobs:** Code/test-head PR run [45291011985](https://github.com/RedMentos/Aii/actions/runs/45291011985) and push run [45291005230](https://github.com/RedMentos/Aii/actions/runs/45291005230); the subsequent documentation-tip PR/push runs [45291476473](https://github.com/RedMentos/Aii/actions/runs/45291476473) and [45291479005](https://github.com/RedMentos/Aii/actions/runs/45291479005) also ended `startup_failure` with zero jobs. This is not a test PASS and does not establish a code regression either.
- **Redmi / Termux — REDMI_UNVERIFIED:** device was STOPPED_BY_USER. No relay query, APK install, update request, chat send, shell, model/weight change or permission change occurred.

## User-visible effect

When repeated real C3 zero-token prefill deadlines activate recovery, initial B1/B2 work no longer consumes the final C4 selection/re-entry second. If the bodies cannot fit their own minimum slice, the existing post-commit observer path remains available. This is a scheduling correction only; useful native B1/B2 offers, correct C3 output, latency improvement and Android behavior remain unverified.

## Next authorized work

1. Boss/Integrator: rebind the nested Runtime/JEPA and staged-consumer source pins against the exact #2458 head; do not merge the draft without that review.
2. QA: obtain executable exact-head Python 3.13/3.14 staged and integrated runs; inspect the C4 reserve and re-entry regressions.
3. After integration, use only authenticated device receipts and explicit user authorization for a new Redmi test. No manual Termux command or updater request is needed from the user now.
4. Next Core technical task: connect the existing `native_prefill_profile` admission logic to the actual per-role runtime using only matching device/model/thread/batch DEVICE_RECEIPT samples. Unknown or synthetic profiles must never be promoted to device evidence. Do not swap models without separate explicit approval.
