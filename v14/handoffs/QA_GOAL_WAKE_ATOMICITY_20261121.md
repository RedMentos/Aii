# QA handoff — Goal wake publication atomicity

**Updated:** 2026-11-21 21:41 CET  
**Owner:** QA & Android  
**Branch:** `qa/v14-goal-wake-atomicity-20261121-run11`  
**Base:** `gpt6/v13-private-remote-bridge-20261111` at `bdcad466ffea75a2b41f7d23be168f53c7197d20`  
**Status:** implementation pushed for exact-head CI; NOT_RELEASED / REDMI_UNVERIFIED.

## Reproduced defect

On the current shared source, `GoalStore.add(..., wake_at=...)` committed the goal and incremented its sequence before `schedule()` converted `wake_at` to float. A value such as `"not-a-time"` therefore raised `ValueError` after a durable goal row existed. The same flow could leave a goal row without a valid scheduler backlink when the scheduler refused or the backlink write failed.

This is a real persistence/lifecycle defect in the long-horizon goal subsystem, not an Age/compute-budget change.

## Change

- Validate `wake_at` as a finite numeric timestamp before any goal-state write; reject booleans, strings, NaN, infinities and values that overflow float conversion.
- Serialize goal creation and wake publication under the existing Store RLock so a scheduler worker cannot dispatch between the goal row and its backlink.
- Roll back the goal row and sequence if the scheduler refuses or publication fails.
- Add a narrow scheduler compensation method that cancels only a still-pending/held event after a failed goal backlink write. A post that committed and then raised is located by the exact `goal:<id>` dedup key and compensated.
- Add actual SQLite/Store/EventScheduler regressions for invalid input, successful matching receipts, queue refusal, pre-commit exception, post-commit exception and backlink-write failure.

No model, weight, Age right, learning mode, device permission, installed runtime, user chat or phone data is changed.

## Evidence boundary

- Full local Aii checkout: BLOCKED; no repository checkout is mounted and `git ls-remote` failed because `github.com` DNS could not resolve.
- The focused test is added to the existing Lab-Age/rights CI workflow, rather than creating a new standalone workflow.
- GitHub Actions exact-head results must be read back before claiming test success.
- No Android/Termux device is connected. Private owner-read requests Aiiii #431 (PIPELINE_STATUS) and #432 (DIAGNOSTICS) remain open with zero authenticated comments; installed SHA and updater consent remain UNKNOWN. REDMI_UNVERIFIED.
- No UPDATE_REQUEST, LOG_PAGE, CHAT_SEND, shell action, Termux command, model/weight/permission change or device mutation was performed.

## Next step

After exact-head CI, ask Core/Boss to compose this isolated QA fix with the separate Age-rights and current Runtime branches, retain the new persistence tests, and run restart/recovery plus the complete current staged/integrated suite. No user action is required.
