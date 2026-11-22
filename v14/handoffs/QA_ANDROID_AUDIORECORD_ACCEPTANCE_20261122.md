## QA run 11 — current companion, migration and phone evidence (2026-11-22 08:02Z)

- QA PR #2286 exact head: `106d181fff812c188cfe186e689cc5e78c2f121c`. Exact-head CI is **7/7 SUCCESS**: Android companion Gradle/Robolectric (run 45000497679, BUILD SUCCESSFUL); staged + integrated regression (45000497664: staged 240 passed / 10 skipped / 47 subtests; integrated 415 passed / 3 skipped / 58 subtests); old-phone migration (45000497607: 2 passed); Android outcome (45000497653); local sandbox (45000497669); control broker (45000497697); Core outcome adapter (45000497733).
- The Android companion's first exact-head attempt hit Maven Central HTTP 429. The failed job was retried; the retry on the same SHA passed. No code was changed to work around the rate limit.
- Migration diagnosis: the legacy worker's `Pinned plain UI recovery builder changed` error is the expected fail-closed result when that old worker encounters a new pinned builder. The test now requires that it publish no active-runtime receipt, then requires the freshly reloaded worker to recover the exact target. This is a synthetic two-checkout CI proof, not a Redmi migration receipt.
- QA code/test changes: fixed the missing MainActivity.refresh() SharedPreferences declaration; serialized pending-row expiry and exact notification cleanup with submit publication in both provider and MainActivity; added a latch-controlled expiry/notification regression; added Robolectric runner + paired-Termux fixture to the process-start stop-switch snapshot test. Stop/enable persistence uses checked synchronous commit and fails closed.
- PR #2286 remains **DRAFT / NOT_RELEASED / REDMI_UNVERIFIED**. It is 193 commits ahead / 716 behind current release c03ff0, merge base d3ac638; it still depends on the #2271 → #2273 parent stack. Do not rebase this leaf alone. Perception #2312 must be reconciled after the full companion stack.
- Latest private owner-authenticated PIPELINE_STATUS #498 (07:52Z): auto-update enabled, dashboard UPDATED, runtime CI_WAIT, last_result PARTIAL, last_error NONE, target/update commit c03ff0. Earlier #496 was UP_TO_DATE at f210999. No UPDATE_REQUEST was sent. Do not claim the c03ff0 runtime is installed; its push CI was still 34 SUCCESS / 0 FAILURE / 4 IN_PROGRESS in the latest Boss read. c03ff0 is documentation-only.
- No local full Aii checkout or local Android SDK was available. No APK install, Android permission request, AudioRecord instance, microphone capture, screen/UI executor or Redmi action occurred. Audio remains caller-supplied PCM only; `audio_capture=OFF_NOT_IMPLEMENTED`, provider `NONE`, and zeroization of immutable Python PCM remains OPEN.

---

# QA Android AudioRecord acceptance matrix — 2026-11-22

**Owner:** QA & Android  
**Companion stack:** PR #2286  
**Current branch:** qa/v14-companion-os-permission-contract-20261122  
**State:** CONTRACT / DEFAULT_OFF_GUARDS_ONLY / NOT_RELEASED / REDMI_UNVERIFIED

## Scope and safety boundary

The current companion has no microphone provider or AudioRecord read loop. This QA work does not add one, request or grant RECORD_AUDIO, start capture, or mutate the user's device. The companion manifest requests only notification permission. The capability registry now explicitly reports audio_capture=OFF_NOT_IMPLEMENTED, provider NONE, OS permission required, and no result/learning authority. The provider allowlist continues to accept only launch_app.

## Acceptance matrix

| Requirement | Existing evidence | Status |
|---|---|---|
| Permission denied/revoked | Manifest default-off test proves no RECORD_AUDIO or microphone FGS permission is requested | DEFAULT_OFF_PASS; runtime denial path BLOCKED |
| Visible Activity stop/background | No capture Activity/provider exists | BLOCKED_NO_PROVIDER |
| Cancel/timeout | Python Runtime two-phase lease tests cancel C3 and revoke before completion with synthetic PCM/fakes | SYNTHETIC_RUNTIME_PASS; Android capture BLOCKED |
| Short/failed read | No AudioRecord read loop exists | BLOCKED_NO_PROVIDER |
| Duplicate/expired request | Companion launch approval DB tests cover atomic decisions/expiry, not audio lease | PARTIAL |
| One-shot consume | No audio nonce/lease exists in Android companion | BLOCKED_NO_PROVIDER |
| Stop switch/process death | Launch stop switch exists; no microphone service/process exists | PARTIAL |
| PCM zeroization/no persistence | Companion DB schema contains no PCM/audio blob columns; Python stores derived acoustic context, not raw PCM. Python ingress still uses immutable bytes, so zeroization is not proven | NO-PERSISTENCE GUARD PASS; ZEROIZATION OPEN |
| Signature/digest/source/finality | Launch ECDSA receipt and Python PCM16/source/consent/finality checks exist; no Android audio receipt | PARTIAL |
| Store revocation before C3 | Boss head 1105ab56, run 44988042151: Python 3.13 + 3.14 each 52 passed / 26 subtests; synthetic provider/runners only | SYNTHETIC_PASS |
| Redmi microphone | No provider/APK/permission/device receipt | REDMI_UNVERIFIED |

## Required one-shot visible AudioRecord contract

- Capture remains OFF by default and can start only after a visible foreground Activity action plus a separate live source-bound consent lease and OS permission grant.
- No background capture, no implicit model-triggered capture, and no auto-resume after process death.
- Atomically consume a unique nonce before starting; reject duplicate, replayed and expired requests.
- Runtime ingress accepts 8–48 kHz, but signed-consumer PR #2312 (current head `5221314d3c01ab6d874ecc0a8b8ff72c34e504a2`) expects mono PCM16 at exactly 44.1 kHz, maximum one second; Android documents 44.1 kHz as the only rate guaranteed across devices. Android guarantees 44.1 kHz only; 16 kHz may work on some devices. Check AudioRecord.getState()/getSampleRate() and fail closed on mismatch, or use a tested resampler with source/target rates bound into the signed receipt. Never silently relabel or resample.
- Always stop/release AudioRecord and wipe the mutable capture buffer in finally on cancel, timeout, backgrounding, permission revocation, exception or process death.
- Do not persist raw PCM in files, SQLite, logs, backups or crash reports. Python immutable-byte zeroization remains an explicit open requirement; do not claim it is solved by garbage collection.
- Sign the receipt over nonce, source ID, PCM digest, sample rate, frame count, timestamps and finality. Revalidate source and consent before Store admission and again before C3 dispatch; revoke must cancel C3 and tombstone derived context.
- No ASR/transcript authority, learning authority or action authority is implied by microphone permission.

## Evidence boundary

The default-off tests are Robolectric/CI contract guards, not actual microphone tests. Runtime lease tests use synthetic PCM and fake providers/runners. No local Android SDK, APK install, microphone permission, AudioRecord instance or Redmi hardware test occurred. The matrix must be upgraded only when Core supplies the provider and the user separately authorizes the device permission test.


## Cross-lane dependency and Android sample-rate constraint

- Active Perception consumer is PR #2312, current code/test/handoff head `5221314d3c01ab6d874ecc0a8b8ff72c34e504a2`, stacked on this QA companion verifier/nonce branch and the earlier `audio_input.py` ingress contract from #2304. The earlier duplicate PR #2310 is closed unmerged.
- Exact current-head consumer workflow `44992975596` is QUEUED; staged/integrated workflow `44992975599` is IN_PROGRESS at the latest read. No result is transferred from older heads. Earlier #2312 head `98f434d` passed its focused consumer and integrated regression, but its overall staged job still failed two inherited old-profile migration assertions (runtime ERROR / last_error UPDATE / PARTIAL).
- The consumer requires one-shot mono 44.1-kHz PCM16, at most one second (88,200 bytes; 117,600 Base64 characters). Android's AudioRecord reference documents 44.1 kHz as the only rate guaranteed across devices: https://developer.android.com/reference/android/media/AudioRecord. A future visible provider must inspect AudioRecord state and actual client sample rate, register AudioRecordingCallback before capture, and abort on silencing, route, preprocessing or format changes. Never relabel or silently resample.
- #2312 still does not open a microphone, request RECORD_AUDIO, run in background, or implement a capture Activity/provider. It verifies caller-supplied signed PCM only. No Redmi microphone rate or capture is measured.
- The QA companion parent stack still needs re-composition on the current release-development head; do not retarget #2312 or #2286 independently and omit required parents.

## Superseding readback — 2026-11-22 06:00 CET

- **Companion branch head:** `7091c0d2e820f3c75a31821020c7e3bc9b4e2e3b` (QA PR #2286). The exact Android Gradle/Robolectric, broker, outcome, sandbox and staged/integrated workflows for this new head were still QUEUED at the latest poll. Prior head `ade56f08fec407bf75f405dfc1e17c5e6dc4e6f6` had Android companion, broker, outcome, sandbox and Core adapter checks PASS; its staged/integrated job had not completed at that read. The missing Java `Cursor` import observed on an earlier code head is now present in the exact branch file and is no longer the current known compile blocker.
- **New QA fix:** full action ID is now the NotificationManager tag, rather than a 32-bit `String.hashCode()` notification ID. A known collision regression and malformed-ID negative test are in the current head. Exact Android CI for the new patch is pending.
- **Current microphone boundary:** manifest still requests only `POST_NOTIFICATIONS`; no `RECORD_AUDIO` or microphone foreground-service permission. `audio_capture` remains `OFF_NOT_IMPLEMENTED`, provider `NONE`; launch_app is the only provider capability. No AudioRecord loop, microphone request, capture, ASR, vocoder, full duplex or raw-audio learner is implemented in this companion branch.
- **Signed one-shot consumer stack:** PR #2312 is the corrected consumer candidate with the #2286 verifier/nonce dependency and #2304 audio-input contract; it is still a draft stack and must be rebased after the companion/Core parents are integrated. Its 20 targeted tests and py_compile were run in a CPython 3.13.5 x86_64 scratch mirror, not a full Aii checkout. No Android provider or 44.1 kHz device support is proven. PR #2310 is the earlier mismatched-base duplicate and should not be treated as the accepted dependency path.
- **Fresh device read:** private owner-read requests #478 (`PIPELINE_STATUS`) and #479 (`DIAGNOSTICS`) have no authenticated response at the last poll. Installed SHA and updater consent remain UNKNOWN. No LOG_PAGE, UPDATE_REQUEST, shell, APK install, permission change or phone mutation was performed. REDMI_UNVERIFIED.
- **Local environment:** no Aii checkout, Gradle executable or adb is present in this worker; Java 21 alone is not an Android build/test environment. LOCAL_LINUX full project tests and Android SDK tests remain BLOCKED.
- **Next:** read exact-head CI for #2286; then rebase the Android companion + signed audio consumer stack onto the current Boss candidate only after its exact current-base checks are green. Keep audio capture OFF until a visible foreground AudioRecord provider, nonce/revocation cleanup, buffer zeroization and device-specific sample-rate checks are implemented and separately authorized.


## QA companion follow-up — 2026-11-22

- QA branch `qa/v14-companion-os-permission-contract-20261122` currently reaches `9265ae5fb5e8b61ea4c09a245ce93c3920874ef7`.
- Notification lifecycle fix, code/test commit `5510259c1ede0cab26e03fb591f38f389863cb68`: exact tagged notifications are cleared after remote cancellation, local approve/deny finalization, stale Activity review and expired-row cleanup. Expiry IDs are selected and transitioned to EXPIRED in one SQLite transaction. Robolectric regression proves expiry/cancellation removes only the corresponding action's notification.
- Receipt lifetime fix, code commit `091249903081c298502d78eeeafb2cf602e0d4c4` and test commit `9265ae5fb5e8b61ea4c09a245ce93c3920874ef7`: the request deadline gates the one-shot claim, but a claim won just before expiry must still produce a verifiable receipt. The previous `min(request_expiry, issued_at+60s)` could create an already-expired receipt after a late approval. The signed receipt now receives its own bounded 60-second window from `issued_at`; a regression covers a claim at second 1029 with request expiry 1030.
- Migration diagnostic commit `ce56d6b144d700d39188ea6ac7baf2376fc70260` prints the already-sanitized `prepare_source`/`deploy` error details from the old worker. The earlier exact failure `44992007810` remains PARTIAL / runtime ERROR / last_error UPDATE until the new diagnostic rerun identifies the cause.
- Exact CI for code head `9265ae5`: Android companion, broker, outcome, sandbox, migration and staged/integrated workflows are QUEUED at the latest read; no new-head PASS is claimed. Migration-diagnostic head `ce56d6b` also has queued reruns. Full local Aii checkout, Gradle and adb are unavailable; LOCAL_LINUX full-project and Android SDK tests remain BLOCKED.
- Current signed audio consumer is #2312, head `5221314d3c01ab6d874ecc0a8b8ff72c34e504a2`, caller-supplied 44.1-kHz mono PCM16 only. Its consumer workflow `44992975596` is QUEUED and staged/integrated `44992975599` was IN_PROGRESS at last read. It does not open a microphone; no Android AudioRecord provider exists.
- The companion branch remains a draft stack. Compared with release tip `f210999cf556be4d4514427cc9b5cf6d3cf3e984`, it is 164 ahead / 715 behind with merge base `d3ac638b04d166c4fe7611f3d314b1633b7036f8`. The complete #2119 → #2134 → #2271 → #2273 → #2286 parent chain must be reconciled together.
- No APK install, provider IPC, KeyStore operation, microphone permission, AudioRecord capture, phone update, model/weight change or user-data mutation occurred. **NOT_RELEASED / REDMI_UNVERIFIED**.


## Superseding signed-consumer correction — 2026-11-22 08:xx CET

The older cross-lane note below that names PR #2310 and 16-kHz PCM16 is historical and superseded. The active Perception consumer is **PR #2312**, which requires **44.1-kHz mono PCM16**, at most one second (88,200 bytes; 117,600 Base64 characters). PR #2310 is closed unmerged. No AudioRecord provider or microphone capture is implemented by this QA companion branch. Keep `audio_capture=OFF_NOT_IMPLEMENTED`, and do not enable/request RECORD_AUDIO or resample/relabel samples without a separately reviewed, signed rate contract. See the active #2312 dependency note above and https://developer.android.com/reference/android/media/AudioRecord.
