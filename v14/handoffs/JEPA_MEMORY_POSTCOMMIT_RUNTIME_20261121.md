# JEPA & Memory — current-base postcommit runtime candidate (2026-11-21)

## Base and ownership
- Base branch: `gpt6/v13-private-remote-bridge-20261111`
- Base SHA: `569680bc10eabeb94ea5a1695d4bf77b8584e0a0`
- Lane: JEPA & Memory; changes touch the shared SleepRuntime and numeric WorldJEPA update path, so Boss/QA review is required before merge.
- Supersedes the stale-base implementation attempt in PR #2168 only after this candidate's exact CI is green. No force-push and no release/deployment claim.

## Concrete changes
1. SleepRuntime now schedules the latest observed ActionOutcome only; a newer CANCELLED/ABORTED/OUTCOME_UNKNOWN row cannot starve an older observed T8 backlog.
2. Sleep cursor records learning and planner completion separately. A planner-only SHADOW readout while optimizer gates are OFF cannot suppress a later explicit learning opt-in for the same event.
3. WorldJEPA.fit/partial_fit, Store consumer and runtime facade accept a cooperative cancel check. SleepRuntime checks user cancellation every optimizer step and resource state periodically; cancellation before checkpoint/Store commit discards the temporary update. The scheduler requeues the cancelled idle job.
4. The numeric learner remains dual-gated, source/digest-disjoint, replay/retention checked, persistent and rollback-capable. Native GGUF B1/B2 weights are not changed; B1/B2/SELF readouts remain SHADOW with no decision authority.

## Tests added
- Censored newest outcome does not starve older observed T8.
- User preemption cancels a fit without checkpoint/Store cursor commit and requeues the scheduler job.
- Planner-only readout does not consume later learning permission.
- Existing source-bound learner, parameter/EMA diff, holdout, shuffled/zero-action negative controls, replay, restart and rollback tests remain included.

## Evidence boundary
- Local exact Aii checkout: BLOCKED by GitHub DNS resolution; no local repository PASS.
- Exact candidate CI: pending readback.
- Redmi: REDMI_UNVERIFIED; no authenticated owner receipt, installed SHA or updater consent.
- No phone action, model download/swap, permission change or user-data mutation.

## Research consequence
JEPA-TTT (arXiv:2610.00722; https://jepa-ttt.github.io/) reports a matched persistence control where retaining predictor, optimizer and replay state improves planning over resetting each episode. The current V14 learner persists numeric model/replay state but not Adam moments. Persist optimizer moments atomically next, then compare reset vs persistent optimizer under equal update and replay budgets. ER-JEPA (arXiv:2609.36952) motivates later content/hard replay comparisons; no code/weights/license were imported.

## Next action
Boss/QA review the shared SleepRuntime/WorldJEPA changes and exact CI. After integration, persist optimizer moments and measure the reset-vs-persistent ablation. No user action required.
