# V14 Perception → Core/QA handoff: consent-gated Android AudioRecord ingress

**Date:** 2026-11-22  
**Status:** DESIGN / NOT IMPLEMENTED / REDMI_UNVERIFIED  
**Owners:** Core & Harness (companion/provider + Termux bridge), QA & Android (OS permission/lifecycle/security), Research & Perception (A-plane contract + Termux audio consumer).

## Current verified boundary

- PR #2304 composes caller-supplied mono PCM16 into the staged Runtime: audio packet → RAW EAR cues → A4 temporal/attention evidence → C3 scalar admission. The current path is synthetic/CI input, not microphone capture.
- The companion source inspected on qa/v14-companion-os-permission-contract-20261122 currently advertises only launch_app; its manifest has no RECORD_AUDIO, and its provider has no audio-capture method. The app is targetSdk 33. No Android microphone provider is implemented.
- Keep the existing PCM16 path and all A0–A5, voice, speaker/prosody, non-speech, provisional/final and privacy obligations. This handoff adds an input source; it does not replace RAW EAR or turn audio into transcript-only STT.

## Proposed one-shot contract

1. **Default OFF.** Add a distinct audio_capture capability. It is not READY unless Termux is paired, companion stop-switch is enabled, and the Android runtime permission is granted. Permission grant alone is not continuous consent.
2. **Request:** paired Termux calls a provider method with a fresh 32-hex request ID, a digest over all request fields, duration_ms <= 1000, sample_rate=16000, channels=1, encoding=pcm_s16le, and expiry no more than 60 seconds. Reject unknown fields, duplicate IDs with changed payloads, expired requests and any model-supplied permission flags.
3. **Visible approval:** provider returns PENDING_USER_APPROVAL and posts an explicit notification. A non-exported AudioCaptureConsentActivity shows package, requested duration, sample rate, purpose and expiry. Only the user's visible “Capture one second” action may request RECORD_AUDIO from Android. Deny, cancel, timeout or app stop yields a signed non-capture receipt.
4. **Foreground-only capture:** for this one-second sample, capture inside the visible Activity; do not start a background microphone service. Recheck permission and companion stop state immediately before opening AudioRecord. Stop/release on Activity stop, cancellation, timeout, permission failure or read error. No hidden/background capture.
5. **Source metadata:** prefer UNPROCESSED only if Android reports PROPERTY_SUPPORT_AUDIO_SOURCE_UNPROCESSED; otherwise use MIC and report the actual source. Never label a processed MIC stream “unprocessed”. Capture mono PCM16 at 16 kHz for at most 1 second; fail closed if the device cannot initialize that format rather than silently changing the A-plane sample rate.
6. **No raw persistence:** never write PCM to SQLite, files, logs, analytics or network. Keep at most one 32-KB sample in a bounded in-memory one-shot slot, expire it, and clear the byte buffer after consumption/cancel/process death. The base64 representation is about 43 KB and exists only in the provider response; no public issue/PR/chat may contain it.
7. **One-shot result:** paired Termux polls audio_outcome(request_id). A captured result is returned once as base64 PCM plus a signed receipt containing request ID/digest, source_id=android.mic, generation/session nonce, monotonic start/end, sample rate, channels, sample count, encoding, actual AudioSource, OS permission state, consent result, finality and PCM SHA-256. The result is removed after read. A second read returns CONSUMED.
8. **A-plane consumer:** the Termux adapter verifies the companion signature, request digest, PCM hash, sample count, expiry, source and consent; then calls the existing audio_input.submit_audio_only / consume_pcm16_voice_window route with finality=FINAL. Store only source/time/feature receipts; never store the PCM. A4 gets acoustic cues, C3 gets the bounded scalar summary, and optional ASR remains a separate teacher path.
9. **Revocation/stop:** companion disable, user cancel, Activity stop, OS permission revocation, process death or timeout must cancel the request and clear any in-memory bytes. No request may grant learning, speaker identity, tool or cross-organ weight authority.

## Tests required before promotion

- JVM/Robolectric with an injected fake AudioRecord backend: permission denied, user deny/cancel, short reads, zero/negative/error reads, initialization failure, timeout, activity stop, stop-switch during capture, duplicate request, changed digest, expiry, one-shot consume, buffer zeroization and no file/DB/log persistence.
- Python Termux adapter: malformed Bundle/base64, signature mismatch, digest mismatch, PCM hash mismatch, wrong sample count/rate, stale generation, expired consent, duplicate outcome and no-provider negative control.
- Staged/integrated Runtime: FINAL source-bound packet reaches A4/C3 once; PROVISIONAL remains A4-only; revocation between capture and consume rejects; restart loses transient PCM safely; no-audio and noise controls remain negative.
- Redmi acceptance (not yet run): Android 13 visible permission prompt, capture/stop, app background, permission revoke, process death, sample-rate support, peak RSS/latency, source receipt and no persistent raw bytes. No Android claim before this receipt.

## Platform constraints

- Android's microphone is a while-in-use runtime permission. Keep the one-shot Activity visible while requesting and capturing.
- If a later design genuinely needs a microphone foreground service on Android 14+, declare FOREGROUND_SERVICE_MICROPHONE and android:foregroundServiceType="microphone"; the OS requires RECORD_AUDIO and restricts starting that service from the background. Prefer the foreground Activity for the one-second sample to avoid that extra authority.
- No permission is requested by this PR and no installed app/model/weight/data changes are made.

## References

- Android 14 foreground-service type requirements: https://developer.android.com/about/versions/14/changes/fgs-types-required
- Background start restrictions for while-in-use permissions: https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start
- Runtime permission guidance: https://developer.android.com/training/permissions/requesting
- Existing A-plane contract: v13/code/v13/audio_input.py, v13/code/v13/audio_voice_cues.py, v13/code/tests/test_audio_speaker_evidence.py.
