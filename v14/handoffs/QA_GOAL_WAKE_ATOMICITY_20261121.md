# QA handoff — Goal wake publication atomicity

**Updated:** 2026-11-21 21:54 CET  
**Owner:** QA & Android  
**Branch:** `qa/v14-goal-wake-atomicity-20261121-run11`  
**Base:** `gpt6/v13-private-remote-bridge-20261111` at `bdcad466ffea75a2b41f7d23be168f53c7197d20`  
**Status:** implementation and exact source-pin chain pushed; PR #2257 DRAFT / NOT_RELEASED / REDMI_UNVERIFIED. Current PR head: `a37b2dec808e3de6294b0cae4ff492d66e96cda3` (workflow follow-up); code/pin head: `62a540ff3fbc6350168b38a7e78785de3ec5ca84`.

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
- LOCAL_LINUX isolated helper check: PASS (4 valid timestamps and 7 invalid controls); this is not a repository integration test.
- CI Python 3.11: PASS — Lab-Age workflow compiled `goals.py`, `scheduler.py` and the tests; 15 combined Age/goal-wake tests passed, plus the existing Lab-Age controls, WebView and mobile dashboard suites.
- CI Python 3.14: PASS — all 7 goal-wake tests passed on CPython 3.14.10; exact immutable staged runtime startup and SQLite source-ref selftest also passed.
- CI integration support: PASS — source-pinned integrated-stage test passed; offline runtime-deploy integrity passed; two-checkout old-phone migration passed; owner-read synthetic security checks passed.
- CI staged-runtime and integrated-regression jobs are still running at the time of this update. The additive-only policy gate is FAIL BY POLICY (`not a strictly additive PR`) because this is a reviewed production-code fix touching existing modules/builders; it is not a test assertion failure and has not been bypassed.
- Exact builder chain was read back and verified: scheduler `1e6f55d5348e83411c98d3f5d197aa2853e4fd3093b2c2164d6caa69acd6f783` → idle overlay `6713ae5e27205cccd2eecfe542db7818a98261cc59f54804e4047fa188f34fa5` → recovery builder `0e555f185ca5d48c4d9299325f0588feefb4b4da9adbf693944a31d0d0815fc8` → integrated stager `71b63e23add542f45f32952f1ff8657a2d11f08507c01db6ca450673a3a670c8` → `runtime_deploy.STAGER_SHA256` matches.
- No Android/Termux device is connected. Latest private Aiiii owner-read issues #435 and #436 (PIPELINE_STATUS) remain open with zero authenticated comments; #431/#432 are also unanswered/expired. Installed SHA and updater consent remain UNKNOWN. REDMI_UNVERIFIED.
- No UPDATE_REQUEST, LOG_PAGE, CHAT_SEND, shell action, Termux command, model/weight/permission change or device mutation was performed.

## Next step

After exact-head CI, ask Core/Boss to compose this isolated QA fix with the separate Age-rights and current Runtime branches, retain the new persistence tests, and run restart/recovery plus the complete current staged/integrated suite. No user action is required.
