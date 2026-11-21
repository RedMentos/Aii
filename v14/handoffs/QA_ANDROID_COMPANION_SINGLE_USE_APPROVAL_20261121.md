# QA handoff — Android companion single-use approval

**Updated:** 2026-11-21  
**Owner:** QA & Android  
**Core candidate:** [PR #2271](https://github.com/RedMentos/Aii/pull/2271)  
**QA follow-up:** [PR #2273](https://github.com/RedMentos/Aii/pull/2273)  
**QA branch:** `qa/v14-companion-single-use-approval-20261121`  
**Core base at latest sync:** `c5c9bddbfb7e47d16e4543fef71b19a02b13954d`  
**Status:** DRAFT / CI_PENDING / NOT_RELEASED / REDMI_UNVERIFIED

## Reproduced defect

Two separate `ConsentActivity` instances can load the same `PENDING_USER_APPROVAL` row and both show a dialog. The Core branch added an atomic `PENDING_USER_APPROVAL → EXECUTING` claim before `startActivity()`, which closes duplicate approvals. The denial path still finalized directly from `PENDING_USER_APPROVAL`, however, so a stale approve and a concurrent deny could race: whichever reached its database update first could win after the other activity had already started its side effect.

## QA correction

- Extend the existing Core execution claim with an SQL expiry predicate: `expires_at > nowMillis`.
- Add a separate one-shot `PENDING_USER_APPROVAL → DENYING` claim.
- Route both Deny and dialog cancellation through that claim before signing the denial receipt.
- Preserve Core's existing `finish(actionId, expectedStatus, ...)` API; execution receipts finalize only from `EXECUTING`, denial receipts only from `DENYING`.
- Keep Core's `CANCELLED` state terminal. A cancel that wins first prevents both execution and denial claims.
- Claimed actions remain non-retryable after process/database reopen; this is at-most-once behavior and deliberately avoids guessing whether Android received a launch intent before a crash.

## Tests and proof boundary

- Robolectric Android SQLite tests: concurrent approve-vs-deny across two helper instances, expiry, expected-state finalization, restart/no-retry, and cancel-vs-decision negative control. **Exact GitHub Android Gradle result pending.**
- LOCAL_LINUX SQLite algorithm simulation from the prior QA checkpoint: **PASS** — two independent SQLite connections raced for approve/deny; exactly one winner; terminal no-retry after reopen; expiry negative control.
- Local Android Gradle build: **NOT RUN** — JDK 17 exists, but this worker has no Gradle executable or Android SDK.
- No APK installed; no ContentProvider call, Android Keystore key, OS permission, Accessibility, MediaProjection or real app launch exercised.
- No Termux runtime, model, weights, Age, permissions or user data changed.

## Remaining independent review items

1. Verify the ContentProvider binds the exact calling package as well as the UID/certificate where Android exposes that identity; the current UID package-list check can authorize any package sharing that UID.
2. Replace `actionId.hashCode()` as the PendingIntent request code/notification ID with a collision-resistant persisted ID to avoid notification retargeting under `FLAG_UPDATE_CURRENT`.
3. Core has added a TTY-only `:android` orchestration path. It remains separate from the normal model turn, requires explicit `--confirm`, and has no actual Redmi execution proof or user-confirmed key pin receipt in this run.
4. The companion still implements only `launch_app`; UI observation, Accessibility, MediaProjection, tap/swipe/type/back and other Android control capabilities remain OFF/not implemented.

This QA patch does not add UI observation, shell/network access, arbitrary actions or model authority. **No Redmi success is claimed.**
