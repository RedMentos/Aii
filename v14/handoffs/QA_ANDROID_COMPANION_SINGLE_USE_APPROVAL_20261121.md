# QA handoff — Android companion single-use approval

**Updated:** 2026-11-21  
**Owner:** QA & Android  
**Core candidate:** [PR #2271](https://github.com/RedMentos/Aii/pull/2271)  
**QA follow-up:** [PR #2273](https://github.com/RedMentos/Aii/pull/2273)  
**QA branch:** `qa/v14-companion-single-use-approval-20261121`  
**Core base observed at latest sync:** `05415809a5383cce9e26d64247433bb1d73f2776`  
**QA branch commit before this final sync:** `711d95ad0e9156b07d67fe0e62f9d56e0a0fee64`  
**Status:** DRAFT / CI_PENDING / NOT_RELEASED / REDMI_UNVERIFIED

## Reproduced defect

Two separate `ConsentActivity` instances can load the same `PENDING_USER_APPROVAL` row and both show a dialog. The old flow called `startActivity()` before `CompanionDb.finish()`; the DB compare-and-set happened only after the external Android side effect. A stale second dialog could therefore launch the same package again even though its later DB finalizer failed. Approve-vs-deny had the same ordering problem because denial was persisted only after signing.

## QA correction

- A single SQLite `UPDATE ... WHERE status='PENDING_USER_APPROVAL' AND expires_at>?` claims the action before a decision.
- Approval claims `DISPATCHING`; denial/cancel claims `DENYING`.
- Only the winning approval path can invoke `startActivity()`.
- Finalizers accept only their matching claimed state, so a stale deny cannot overwrite a dispatch and a stale approve cannot execute after denial.
- A claimed row remains non-retryable after process/database reopen. This deliberately favors at-most-once behavior over guessing whether a side effect happened before a crash.

## Tests and proof boundary

- Robolectric Android SQLite regression suite: concurrent approve-vs-deny across two helper instances, expired action, finalizer state mismatch, and restart/no-retry. **Exact GitHub Android Gradle result pending.**
- LOCAL_LINUX SQLite algorithm simulation: **PASS** — two independent SQLite connections raced for approve/deny; exactly one winner; terminal no-retry after reopen; expiry negative control.
- Local Android Gradle build: **NOT RUN** — JDK 17 exists, but this worker has no Gradle executable or Android SDK.
- No APK installed; no ContentProvider call, Android Keystore key, OS permission, Accessibility, MediaProjection or real app launch exercised.
- No Termux runtime, model, weights, Age, permissions or user data changed.

## Remaining independent review items

1. Verify the ContentProvider binds the exact calling package as well as the UID/certificate where Android exposes that identity; the current UID package-list check can authorize any package sharing that UID.
2. Replace `actionId.hashCode()` as the PendingIntent request code/notification ID with a collision-resistant persisted ID to avoid notification retargeting under `FLAG_UPDATE_CURRENT`.
3. Runtime operator/CLI orchestration is now present in Core's `android_companion_runtime.py` and TTY-only operator path at Core head `05415809`; it still has no real device execution evidence or user-confirmed key pairing receipt.
4. The companion still implements only `launch_app`; UI observation, Accessibility, MediaProjection, tap/swipe/type/back and other Android control capabilities remain OFF/not implemented.

The companion remains one API-first capability with default STOPPED and per-action UI approval. This QA patch does not add UI observation, shell/network access, arbitrary actions or model authority. **No Redmi success is claimed.**
