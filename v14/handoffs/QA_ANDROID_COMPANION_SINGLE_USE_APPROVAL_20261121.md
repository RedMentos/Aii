# QA handoff — Android companion single-use approval

**Updated:** 2026-11-21  
**Owner:** QA & Android  
**Core candidate:** [PR #2271](https://github.com/RedMentos/Aii/pull/2271)  
**QA follow-up:** [PR #2273](https://github.com/RedMentos/Aii/pull/2273)  
**QA branch:** `qa/v14-companion-single-use-approval-20261121`  
**Core base at latest sync:** `a4d4a5ea304ff2de35f331b9a65455c812a64879`  
**Status:** DRAFT / CI_PENDING / NOT_RELEASED / REDMI_UNVERIFIED

## Reproduced defect

Two separate `ConsentActivity` instances can load the same `PENDING_USER_APPROVAL` row and both show a dialog. Core added an atomic `PENDING_USER_APPROVAL → EXECUTING` claim before `startActivity()`, which closes duplicate approvals. The denial path still finalized directly from `PENDING_USER_APPROVAL`, however, so an approve and a concurrent deny could race: whichever reached its database update first could win after the other activity had already started its side effect.

## QA correction

- Extend Core's execution claim with an SQL expiry predicate: `expires_at > nowMillis`.
- Add a separate one-shot `PENDING_USER_APPROVAL → DENYING` claim.
- Route both Deny and dialog cancellation through that claim before signing the denial receipt.
- Preserve Core's existing `finish(actionId, expectedStatus, ...)` API; execution receipts finalize only from `EXECUTING`, denial receipts only from `DENYING`.
- Keep Core's `CANCELLED` state terminal. A cancel that wins first prevents both execution and denial claims.
- Claimed actions remain non-retryable after process/database reopen; this is at-most-once behavior and avoids guessing whether Android received a launch intent before a crash.

## Tests and proof boundary

- Robolectric Android SQLite tests: concurrent approve-vs-deny across two helper instances, expiry, expected-state finalization, restart/no-retry, and cancel-vs-decision negative control. **Exact GitHub Android Gradle result pending.**
- Python transport/runtime regression: submit acknowledgements must echo the exact action ID; missing/mismatched IDs fail closed and cancel both local and remote pending state. **Exact Python CI result pending.**
- LOCAL_LINUX SQLite algorithm simulation from the prior QA checkpoint: **PASS** — two independent SQLite connections raced for approve/deny; exactly one winner; terminal no-retry after reopen; expiry negative control.
- Local Android Gradle build: **NOT RUN** — JDK 17 exists, but this worker has no Gradle executable or Android SDK.
- CI setup correction: an initial Android setup attempt failed before Gradle because the SDK package list was passed as one semicolon-delimited string. The workflow now supplies three package entries on separate lines (`platform-tools`, `platforms;android-35`, `build-tools;35.0.0`) at commit `c57426d085360d259c06bb7fcbc715e28b8e6321`; exact rerun is pending.
- No APK installed; no ContentProvider call, Android Keystore key, OS permission, Accessibility, MediaProjection or real app launch exercised.
- No Termux runtime, model, weights, Age, permissions or user data changed.

## Remaining independent review items

1. Verify the ContentProvider binds the exact calling package as well as the UID/certificate where Android exposes that identity; the current UID package-list check can authorize any package sharing that UID.
2. Replace `actionId.hashCode()` as the PendingIntent request code/notification ID with a collision-resistant persisted ID to avoid notification retargeting under `FLAG_UPDATE_CURRENT`.
3. Core has added a TTY-only `:android` orchestration path. It remains separate from the normal model turn, requires explicit `--confirm`, and has no actual Redmi execution proof or user-confirmed key pin receipt in this run.
4. The companion still implements only `launch_app`; UI observation, Accessibility, MediaProjection, tap/swipe/type/back and other Android control capabilities remain OFF/not implemented.

This QA patch does not add UI observation, shell/network access, arbitrary actions or model authority. **No Redmi success is claimed.**


## Follow-up — signed receipt must remain retryable until Store commit (2026-11-22)

**QA follow-up PR:** #2286, branch `qa/v14-companion-os-permission-contract-20261122`.  
**Current code checkpoint:** `7c684da6b5ac720ede0cc652d5cffacac93b3eca` (exact CI rerun in progress).

### Reproduced failure window

Before this correction, `accept_companion_receipt()` finalized the broker as `RECEIPT_VERIFIED` immediately after signature verification. `accept_and_persist_companion_receipt()` then attempted the SQLite Store transaction. If the Store write failed, the signed receipt remained available in the companion, but `poll()` saw a terminal broker state and returned `ALREADY_FINAL`; no source-bound ActionOutcome/nonce was persisted and no retry was possible.

### QA correction

- `accept_companion_receipt(..., finalize_broker=True)` preserves the standalone API's existing behavior.
- The combined `accept_and_persist_companion_receipt()` path verifies with `finalize_broker=False`, persists the source-bound ActionOutcome and nonce transaction, then marks the broker `RECEIPT_VERIFIED`.
- Transient Store failures leave the broker in `RECEIPT_CONSUMED`, which `consume_dispatched()` already restores/reuses on retry.
- The Store persistence is idempotent by action ID, source event, receipt nonce and digest, so a retry after Store commit but before broker finalization returns the existing packet rather than duplicating it.
- Permanent `InvalidOutcome` provenance/replay failures transition to `RECEIPT_REJECTED`; they are not left retryable.
- Regression: `test_store_failure_keeps_signed_receipt_retryable_until_durable_commit`.

### Current proof boundary

- The new regression and companion outcome tests are being rerun on Python 3.13/3.14 at exact head 7c684.
- Android Gradle/Robolectric and staged repository integration are also in progress; no local Android SDK/device is available.
- No APK installation, Android permission, actual package launch, Termux mutation, model/weight change or Redmi test occurred. **REDMI_UNVERIFIED**.

### Remaining open QA findings

1. Ambiguous `content call` submit timeout can still leave a remote pending approval if cancellation fails while the local broker is marked cancelled. Preserve an explicit uncertain state until remote cancellation or signed outcome is reconciled (reported on #2273 comment 7073252422).
2. Expired `PENDING_USER_APPROVAL` rows are still returned by `CompanionDb.pending()` and are not transitioned to EXPIRED when the activity exits; add atomic expiry cleanup (reported on #2273 comment 7073252422).
3. `PendingIntent` identity still uses `actionId.hashCode()`; use a collision-resistant identity/URI so `FLAG_UPDATE_CURRENT` cannot retarget another action's notification.
4. The provider still checks the paired package within `getPackagesForUid()`; where Android exposes it, bind the exact calling package as well as UID and certificate to avoid authorizing a different shared-UID package.

The companion remains limited to one consent-gated `launch_app` capability. Screen observation, Accessibility, MediaProjection, tap/swipe/type/back, shell/network access and model authority remain OFF/not implemented.
