# QA handoff — Android companion single-use approval

**Updated:** 2026-11-22 (current checkpoint below)  
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


## Current QA checkpoint — 2026-11-22 06:20 CET

**Exact branch head:** `c9d78d6537c635f0875539c81abf7535a2e06d94`  
**PR:** #2286 — DRAFT / NOT_RELEASED / REDMI_UNVERIFIED.  
**Base:** #2273 at `aa9f5091469ea751ce351cd0e1714c79e483c05f`; the companion stack is not yet rebased onto current Boss head `1105ab56dae6604d927fc4ea868121000010fb93`.

### Resolved in current QA head

1. **Ambiguous submit/cancel:** timeout after possible remote commit no longer finalizes the local action. A failed or unconfirmed remote cancellation leaves `SUBMIT_UNCERTAIN`, which remains pollable; local stop preserves it. Tests cover late signed receipt, cancel timeout and stop.
2. **Expired pending rows:** `CompanionDb.pending(nowMillis)` expires stale rows before returning only live approvals. Robolectric test covers stale/live rows.
3. **PendingIntent identity:** `approvalIntent()` already places the full 32-hex action ID in its data URI. The Robolectric hash-collision test confirms distinct Intent identities even when Java `hashCode()` collides. The notification integer ID still uses the 32-bit hash, so a collision could replace a notification, but cannot retarget the PendingIntent; pending rows remain visible through the companion list.
4. **Exact caller package:** current code now uses Android `ContentProvider.getCallingPackage()`, compares it with the paired package and UID package set, then verifies the paired signing-certificate digest. The helper regression rejects null, mismatched, shared-UID and unrelated-package cases. Android documents that `getCallingPackage()` returns a package verified to belong to the calling UID (API 19+): https://developer.android.com/reference/android/content/ContentProvider#getCallingPackage().

### Exact-head CI evidence

- **V14 Android companion** — run `44989226973`: PASS; Gradle build and Robolectric tests completed (`BUILD SUCCESSFUL`).
- **V13 Android control broker isolated tests** — run `44989226981`: PASS.
- **V13 Android outcome contract** — run `44989227020`: PASS.
- **V13 Android local sandbox replay integration** — run `44989227003`: PASS.
- **V14 Core companion outcome adapter** — run `44989226974`: PASS.
- **V13 staged context/integrated regression** — run `44989227088`: staged-runtime job FAIL, integrated-regression still running at this checkpoint. The staged-runtime log reports **2 failed, 238 passed, 10 skipped, 47 subtests passed**; both failures are old-phone two-checkout migration assertions (`last_result=PARTIAL`, runtime `ERROR`, dashboard `UPDATED`, `last_error=UPDATE`). The same migration failure already existed on parent #2273 head `aa9f509` (run `44959905505`), so it is inherited, not introduced by the exact-caller change. Do not mark this stack release-ready. The likely old-worker/new-builder compatibility mismatch needs a current-base investigation; the current log does not expose the tracked `deploy_errors` payload, so the precise exception remains unconfirmed.
- LOCAL_LINUX repository tests: BLOCKED — no Aii checkout is mounted in this run. Android Gradle ran on GitHub Actions, not on a local device.

### Latest private Redmi evidence (sanitized technical aggregates only)

Owner-read DIAGNOSTICS receipt #466 reports the phone's AI runtime and dashboard running, auto-update enabled, and both source checkouts reporting UP_TO_DATE at installed commit `89333289b8cd50da92cbf7074c9ef689a2972dbf` (last successful update timestamp is 2026-11-18, not this QA head). The latest measured turn was 84.37 s total / 77.51 s TTFT, with 657 prompt tokens and 11 generated tokens; B1 and B2 probes ended in TIME_BUDGET, and only B2 had a mapped native process (699.6 MiB PSS). Native probe is SMOKE_PARTIAL. Official Age remains 0; lab selector is X10/active, but physical feature execution is not verified. These figures are private diagnostic aggregates; no transcript, prompt, device path, key, model bytes or database contents are copied here.

### Remaining acceptance boundary

- The companion code is **not installed** on Redmi; no APK install, provider IPC, Keystore operation or real app launch was tested on the phone.
- `launch_app` is the only implemented native capability. UI observation, Accessibility, MediaProjection, tap/swipe/type/back and background app operation remain OFF/not implemented.
- The current Boss branch has separate green synthetic Age-rights, migration and staged/integrated checks, but that does not certify this older companion stack or the Redmi.
- No UPDATE_REQUEST, remote shell, log-page request, permission change, model change, weight change or device mutation was made.

### Next QA action

Coordinate with Boss/Core to recompose #2271 → #2273 → #2286 on current Boss head `1105ab56dae6604d927fc4ea868121000010fb93`, preserve the exact caller/consent and receipt-lifecycle tests, and repair the inherited old-worker migration path before merge. Only after exact current-head CI and a fresh authorized owner-read may Boss consider the normal update request. **User action: none.**


## AudioRecord acceptance matrix — 2026-11-22

**QA scope only:** no microphone provider is present in this companion stack. No RECORD_AUDIO permission is declared or requested, no permission was granted, and no AudioRecord object or capture service was started. The registry now advertises audio_capture explicitly as OFF_NOT_IMPLEMENTED, provider NONE, OS permission required, no result/learning authority. The provider allowlist still accepts only launch_app.

| Required acceptance | Current evidence | Status |
|---|---|---|
| OS permission denied/revoked | Robolectric manifest guard proves RECORD_AUDIO and FOREGROUND_SERVICE_MICROPHONE are not requested; no capture provider exists | **DEFAULT_OFF_PASS / runtime denial path BLOCKED** |
| Visible Activity stop/background | No capture Activity or AudioRecord lifecycle exists; future provider must stop/release on onStop and never continue in background | **BLOCKED_NO_PROVIDER** |
| Cancel/timeout | Boss Runtime two-phase audio-lease tests cancel C3 and revoke before completion with fake provider/runners | **SYNTHETIC_RUNTIME_PASS; Android capture BLOCKED** |
| Short/failed AudioRecord read | No AudioRecord read loop exists; future provider must reject empty/odd/truncated frames and release the recorder | **BLOCKED_NO_PROVIDER** |
| Duplicate/expired request | Companion launch approval DB has atomic one-shot decision and expiry tests; this is not an audio lease | **PARTIAL / AUDIO BLOCKED** |
| One-shot consume | No audio capture nonce/lease is issued or consumed by Android companion | **BLOCKED_NO_PROVIDER** |
| Stop switch/process death | Companion stop switch protects the existing launch capability; no capture process/service exists to restart | **PARTIAL / AUDIO BLOCKED** |
| PCM zeroization/no persistent raw bytes | Companion DB schema test forbids PCM/audio blob columns; Python audio Runtime stores derived acoustic context, not raw PCM. Python ingress currently accepts immutable bytes, so explicit in-process zeroization is **not proven** | **NO-PERSISTENCE GUARD PASS / ZEROIZATION OPEN** |
| Signature/digest/source/finality | Launch receipts use ECDSA; Python audio ingress validates PCM16 bounds, source/consent and PROVISIONAL/FINAL. No Android audio-capture receipt or signed capture digest exists | **PARTIAL / AUDIO RECEIPT BLOCKED** |
| Store revocation before C3 | Exact Boss head 1105ab56dae6604d927fc4ea868121000010fb93, audio+arithmetic workflow 44988042151: Python 3.13 and 3.14 each PASS, 52 tests + 26 subtests; fake PCM/provider/runners only | **SYNTHETIC_PASS** |
| Real Redmi AudioRecord | No provider/APK install/permission receipt/physical capture evidence | **REDMI_UNVERIFIED** |

### Required provider contract before any microphone implementation

1. Capture is OFF by default. A visible, foreground Activity must show an explicit one-shot action; no background service or implicit model-triggered capture.
2. Check the OS RECORD_AUDIO grant and a separate live, source-bound user-consent lease before constructing AudioRecord. Denial, revocation, disabled stop switch, expired lease or non-visible Activity must not construct/start the recorder.
3. Consume a unique lease/nonce atomically before capture. Duplicate, replayed, expired or already-consumed requests must fail closed.
4. Runtime ingress accepts 8–48 kHz, but signed-consumer PR #2310 currently requires mono PCM16 at exactly 16 kHz, at most one second. Android AudioRecord documents 44.1 kHz as the only rate guaranteed across devices; 16 kHz may work only on some. The provider must check getState()/getSampleRate() and fail closed on mismatch, or use an explicit tested resampler whose source/target rates are receipt-bound. Never silently relabel or resample.
5. On cancel, timeout, onStop, permission revocation, exception or process death: stop/release the recorder, wipe the mutable capture buffer in finally, and never auto-resume after restart.
6. Pass only source ID, consent receipt, sample rate, start time, PCM16 and PROVISIONAL/FINAL through the in-memory bridge. No raw PCM file, SQLite blob, log, backup or crash-report payload. The Runtime must not claim Python immutable-byte zeroization until a mutable-buffer lifecycle is implemented and measured.
7. Bind a signed receipt to lease nonce, source ID, PCM digest, sample rate, frame count, timestamps and finality. Revalidate the live source/consent lease before Store admission and again before C3 dispatch; revocation must cancel C3 and tombstone derived context.
8. Keep action authority and learning authority false. Microphone permission is not permission for ASR, transcription, persistent recording, model training or external action.

### Current test additions

- CapabilityRegistryTest: explicit audio_capture OFF state and provider allowlist rejection.
- AudioCaptureDefaultOffTest: manifest does not request microphone or microphone foreground-service permission.
- CompanionDbApprovalTest: no raw PCM/audio blob table or column in companion SQLite schema.
- These are Android/Robolectric default-off guards, **not** microphone-capture tests. The full runtime matrix remains blocked until Core supplies a real one-shot AudioRecord adapter and the user separately authorizes an actual permission/device test.


## Latest follow-up — 2026-11-22 06:19 CET

**Current QA code head:** 34176854f001927874c7e6c9d4c46ba3dc65483d.  
**Acceptance matrix:** v14/handoffs/QA_ANDROID_AUDIORECORD_ACCEPTANCE_20261122.md.

- Added an explicit audio_capture capability row: OFF_NOT_IMPLEMENTED, provider NONE, OS permission required, no result/learning authority. The provider allowlist still accepts only launch_app.
- Added Robolectric guards for absent RECORD_AUDIO / microphone foreground-service permission and for the companion SQLite schema having no PCM/audio blob storage.
- Added tests for the audio_capture OFF state and provider allowlist rejection. These tests are awaiting GitHub Actions execution.
- The Android and companion Python workflows for head 34176854 are queued (8 runs at last poll). GitHub currently has a large Actions backlog; no test result is claimed for these new tests yet.
- Earlier code head c9d78d6 had Android Gradle/Robolectric PASS and the broker/outcome/sandbox/Core adapter workflows PASS. That does not validate the new AudioRecord default-off tests.
- LOCAL_LINUX Android build is BLOCKED: this run has no Aii checkout, Gradle or Android SDK (Java alone is present). No local Gradle test was run.
- Exact compare from base aa9f509 to head 34176854 shows 20 changed files, 0 deletions; the full tree is present (7,205 paths versus 7,203 in the base). A temporary sparse-tree construction commit was corrected by a forward-only restore commit; no force-push was used and the final repository tree is intact. Prefer squash merge if this stack is ever accepted so the transient tree-repair history is not carried into the release branch.
- The inherited two-checkout old-phone migration failure remains; this stack is not merge-ready. No Redmi install or AudioRecord permission/capture test occurred.

**Status:** DEFAULT_OFF_GUARDS_ADDED / CI_PENDING_QUEUE / MIGRATION_BLOCKED / REDMI_UNVERIFIED. User action: none.


## Cross-lane signed-consumer readback — 2026-11-22

Perception PR #2310 head 923c4b32bb3f63d6224251b00b6b1f9941db5079 is stacked on #2304 at 8a8970c64b66b77bb1bb6a5460d0e4be38a6490c. Its signed-audio-consumer workflow 44988548283 FAILS on both Python 3.13 and 3.14 during test collection with ModuleNotFoundError: v13.android_companion_ecdsa. The staged/integrated workflow 44988548352 passes, but no signed-consumer assertions ran. The base lacks the companion verifier/nonce DB dependency carried by the #2271/#2273/#2286 stack. This is a cross-lane composition failure, not a Redmi or AudioRecord result. Perception was notified to rebase/compose the consumer with the exact verifier dependency.

The consumer PR currently expects 16 kHz mono PCM16 for at most one second. Android's official AudioRecord reference says 44.1 kHz is the only sample rate guaranteed on all devices; 16 kHz may work on some. It also requires checking AudioRecord.getState() after construction and exposes getSampleRate() for the actual configured rate: https://developer.android.com/reference/android/media/AudioRecord. Therefore a future provider must not assume 16 kHz works on Redmi. It must measure the configured rate and fail closed if the signed consumer cannot accept it, or use a tested resampler with both rates bound into the signed receipt. No silent rate substitution.

