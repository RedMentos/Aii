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
- Use bounded mono PCM16 windows matching the Runtime ingress contract (8–48 kHz, maximum one second per window); reject empty, odd-byte, short or failed reads.
- Always stop/release AudioRecord and wipe the mutable capture buffer in finally on cancel, timeout, backgrounding, permission revocation, exception or process death.
- Do not persist raw PCM in files, SQLite, logs, backups or crash reports. Python immutable-byte zeroization remains an explicit open requirement; do not claim it is solved by garbage collection.
- Sign the receipt over nonce, source ID, PCM digest, sample rate, frame count, timestamps and finality. Revalidate source and consent before Store admission and again before C3 dispatch; revoke must cancel C3 and tombstone derived context.
- No ASR/transcript authority, learning authority or action authority is implied by microphone permission.

## Evidence boundary

The default-off tests are Robolectric/CI contract guards, not actual microphone tests. Runtime lease tests use synthetic PCM and fake providers/runners. No local Android SDK, APK install, microphone permission, AudioRecord instance or Redmi hardware test occurred. The matrix must be upgraded only when Core supplies the provider and the user separately authorizes the device permission test.
