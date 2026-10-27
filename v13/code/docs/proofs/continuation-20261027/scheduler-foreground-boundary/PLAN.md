# G13 foreground-kind action boundary: preregistered independent review

Date 2026-10-27 UTC. Owner GPT-6 continuation. Parent review PR #738 exact `a76badb3b19ed9ae332174acd2089fdd5e153c26`; active scheduler is review-only, not production main.

## Hypothesis / expected RED

`_allowed` immediately returns true for `FOREGROUND = {USER_INPUT, TOOL_EVENT, RESOURCE_CHANGE}`, bypassing idle, CRITICAL resource, quiet-hours and burn-out budget. But `_post` accepts arbitrary `action` for every `kind`, so a SYSTEM `TOOL_EVENT` carrying `sleep_full` can be dispatched under CRITICAL while idle=false; a SYSTEM `USER_INPUT` with a growth action can masquerade as foreground. This violates the documented scheduler distinction between signals and background work, independently of the prior capacity fix.

## Contract / proposed GREEN

Foreground-kind events are notifications/control signals, never executable background jobs: accept only `action=None` or `action='notice'` for `USER_INPUT`, `TOOL_EVENT`, `RESOURCE_CHANGE`. `USER_INPUT` must have `origin='USER'`; the user's actual durable turn queue is separate. Preserve existing SYSTEM `RESOURCE_CHANGE` without action and priority/preemption semantics. Do not alter USER-origin TIMER sleep commands, Age rights, allowed action registry or current growth/learning dispatch. Fail closed at post time with ValueError and no queue mutation. No claims about future tool events; any future executable tool action requires its own explicit policy path and approval.

## RED/GREEN verification

Add actual `post/next` regression for SYSTEM TOOL_EVENT carrying `sleep_full` under CRITICAL/idle=false; reject SYSTEM USER_INPUT with growth action; reject RESOURCE_CHANGE with growth action; retain legitimate RESOURCE_CHANGE and TOOL_EVENT notice dispatch. Focused scheduler suite, compile, exact-parent privacy/diff and raw artifacts. Full suite on exact source before integration. No native/model/Redmi proof, no Age promotion. LP1/LP2/BJ1/STEP2/B3 remain negative, jepa_weight=0, V13 incomplete. Preserve all failed evidence; do not merge to main.
