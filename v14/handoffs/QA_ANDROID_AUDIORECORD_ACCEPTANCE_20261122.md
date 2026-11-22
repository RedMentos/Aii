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
- Runtime ingress accepts 8–48 kHz, but signed-consumer PR #2310 currently expects mono PCM16 at exactly 16 kHz, maximum one second. Android guarantees 44.1 kHz only; 16 kHz may work on some devices. Check AudioRecord.getState()/getSampleRate() and fail closed on mismatch, or use a tested resampler with source/target rates bound into the signed receipt. Never silently relabel or resample.
- Always stop/release AudioRecord and wipe the mutable capture buffer in finally on cancel, timeout, backgrounding, permission revocation, exception or process death.
- Do not persist raw PCM in files, SQLite, logs, backups or crash reports. Python immutable-byte zeroization remains an explicit open requirement; do not claim it is solved by garbage collection.
- Sign the receipt over nonce, source ID, PCM digest, sample rate, frame count, timestamps and finality. Revalidate source and consent before Store admission and again before C3 dispatch; revoke must cancel C3 and tombstone derived context.
- No ASR/transcript authority, learning authority or action authority is implied by microphone permission.

## Evidence boundary

The default-off tests are Robolectric/CI contract guards, not actual microphone tests. Runtime lease tests use synthetic PCM and fake providers/runners. No local Android SDK, APK install, microphone permission, AudioRecord instance or Redmi hardware test occurred. The matrix must be upgraded only when Core supplies the provider and the user separately authorizes the device permission test.


## Cross-lane dependency and Android sample-rate constraint

- Perception signed-consumer PR #2310 head 923c4b32bb3f63d6224251b00b6b1f9941db5079 is based on #2304, not on the companion verifier stack. Exact workflow 44988548283 fails on Python 3.13 and 3.14 during collection with ModuleNotFoundError: v13.android_companion_ecdsa. Staged/integrated run 44988548352 passes, but no consumer assertions ran. This consumer is NOT CI-green; it needs a base containing the verifier and durable nonce DB.
- The consumer currently requires 16 kHz mono PCM16, at most one second. Android's official AudioRecord reference says 44.1 kHz is the only rate guaranteed on all devices, while 16 kHz may work on some; check getState()/getSampleRate() and fail closed or use an explicit tested resampler with both rates in the signed receipt: https://developer.android.com/reference/android/media/AudioRecord.
- This reinforces the no-provider boundary: no Android capture has occurred, and no 16 kHz support has been measured on Redmi.



## Superseding readback — 2026-11-22 06:00 CET

- **Companion branch head:** `7091c0d2e820f3c75a31821020c7e3bc9b4e2e3b` (QA PR #2286). The exact Android Gradle/Robolectric, broker, outcome, sandbox and staged/integrated workflows for this new head were still QUEUED at the latest poll. Prior head `ade56f08fec407bf75f405dfc1e17c5e6dc4e6f6` had Android companion, broker, outcome, sandbox and Core adapter checks PASS; its staged/integrated job had not completed at that read. The missing Java `Cursor` import observed on an earlier code head is now present in the exact branch file and is no longer the current known compile blocker.
- **New QA fix:** full action ID is now the NotificationManager tag, rather than a 32-bit `String.hashCode()` notification ID. A known collision regression and malformed-ID negative test are in the current head. Exact Android CI for the new patch is pending.
- **Current microphone boundary:** manifest still requests only `POST_NOTIFICATIONS`; no `RECORD_AUDIO` or microphone foreground-service permission. `audio_capture` remains `OFF_NOT_IMPLEMENTED`, provider `NONE`; launch_app is the only provider capability. No AudioRecord loop, microphone request, capture, ASR, vocoder, full duplex or raw-audio learner is implemented in this companion branch.
- **Signed one-shot consumer stack:** PR #2312 is the corrected consumer candidate with the #2286 verifier/nonce dependency and #2304 audio-input contract; it is still a draft stack and must be rebased after the companion/Core parents are integrated. Its 20 targeted tests and py_compile were run in a CPython 3.13.5 x86_64 scratch mirror, not a full Aii checkout. No Android provider or 16 kHz device support is proven. PR #2310 is the earlier mismatched-base duplicate and should not be treated as the accepted dependency path.
- **Fresh device read:** private owner-read requests #478 (`PIPELINE_STATUS`) and #479 (`DIAGNOSTICS`) have no authenticated response at the last poll. Installed SHA and updater consent remain UNKNOWN. No LOG_PAGE, UPDATE_REQUEST, shell, APK install, permission change or phone mutation was performed. REDMI_UNVERIFIED.
- **Local environment:** no Aii checkout, Gradle executable or adb is present in this worker; Java 21 alone is not an Android build/test environment. LOCAL_LINUX full project tests and Android SDK tests remain BLOCKED.
- **Next:** read exact-head CI for #2286; then rebase the Android companion + signed audio consumer stack onto the current Boss candidate only after its exact current-base checks are green. Keep audio capture OFF until a visible foreground AudioRecord provider, nonce/revocation cleanup, buffer zeroization and device-specific sample-rate checks are implemented and separately authorized.
