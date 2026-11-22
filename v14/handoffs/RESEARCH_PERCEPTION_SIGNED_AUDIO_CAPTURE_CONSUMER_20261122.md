# Research/Perception handoff — signed one-shot Android audio consumer — 2026-11-22

## Checkpoint

- Repository: RedMentos/Aii
- Branch: research-perception/v14-audio-capture-termux-consumer-20261122-run11
- Code commit: 206cfd34cffb57952bce49a404b85631ceac5815
- PR: #2310 — https://github.com/RedMentos/Aii/pull/2310
- Stacked parent: PR #2304, branch head 8a8970c64b66b77bb1bb6a5460d0e4be38a6490c
- Current Boss integration branch head read before this work: 0441ab8b229dd17343c03d9350c6848115220416
- Important: #2304 is still based on the earlier Boss parent 6e6f15322c9fa1931dcf733105d2a32d5372edeb and is currently not mergeable after the Boss branch advanced. #2310 is explicitly stacked on #2304, not a direct release PR. Rebase both after Boss/QA resolve the parent integration.

## What the code actually does

New file: v13/code/v13/audio_capture_consumer.py.

1. Builds a fixed request for one second or less of mono 16-kHz PCM16. The request includes a 32-hex request ID, short expiry, canonical SHA-256 digest, permission_bypass=false and model_authority=false. Building it does not contact Android or request a permission.
2. Uses the existing companion controller's pinned key and receipt DB via verifier_from_pinned_controller(controller). It does not auto-pair or trust a new key.
3. Verifies the signed result envelope and P-256 signature using the existing android_companion_ecdsa primitive. It binds the request digest/ID, android.mic source, expected active Runtime generation, PCM SHA-256, exact sample count, monotonic capture interval, 16-kHz mono PCM16 format, actual UNPROCESSED or MIC source, Android RECORD_AUDIO status, local consent, and FINAL provenance.
4. Commits both the nonce and request ID to the existing receipt DB before one-shot submission. Only nonce/request metadata is stored; PCM is not written to disk.
5. Calls the already-added audio_input.submit_audio_only(runtime, audio_window) with the live consent check, linearizable guard and two-phase revocation callback. The Runtime still performs its own consent/lease checks. The returned status is SUBMIT_RETURNED, not a claim of semantic use or successful speech recognition.

The adapter does not open a microphone, call AudioRecord, ask for Android permission, run in the background, transcribe speech, identify a speaker, update weights, grant T8 learning, or authorize actions.

## Exact provider contract Core/QA must implement

The Android companion must provide a visible, explicit, one-shot capture and a result equivalent to:

- Result schema: v14.android-audio-capture-result/1
- Result fields: schema, status=CAPTURED, request_id, pcm16_base64, receipt
- Receipt envelope: body, key_id, signature
- Receipt body schema: v14.android-audio-capture-receipt/1
- Signed body fields: schema, nonce, request_id, request_digest, source_id, generation_id, start_monotonic_ns, end_monotonic_ns, sample_rate, channels, sample_count, encoding, audio_source, permission_granted, os_permission_status, consent_result, local_consent, finality, pcm_sha256, issued_at, expires_at, key_id, key_storage_status

Canonical signing must match the existing Java ReceiptSigner / Canonical.json: scalar values only, keys sorted lexicographically, compact JSON, ASCII escaping, UTF-8 bytes, SHA256withECDSA on the existing pinned P-256 Android Keystore key. The request digest is SHA-256 of the same canonical JSON over every request field except digest.

Required provider behavior:
- Show a visible Activity and obtain explicit local user approval plus Android RECORD_AUDIO runtime permission. No background or hidden capture.
- Capture at most one second; check AudioRecord.getState() and actual getSampleRate(); collect the exact requested sample count or return a failure. Do not silently resample or relabel.
- Use UNPROCESSED only when PROPERTY_SUPPORT_AUDIO_SOURCE_UNPROCESSED reports support; otherwise report the actual MIC source. VOICE_RECOGNITION remains a separately measured candidate, not a silent fallback.
- Register AudioRecordingCallback before capture. Detect silence, device rerouting and preprocessing/sample-format changes; abort or mark the capture invalid rather than treating silence as a valid observation.
- Stop and release AudioRecord immediately; keep PCM in memory only; return it once; clear the provider's one-shot buffer after consumption/cancel.
- Expose live consent_check, consent_guard and consent_revocation_subscribe bound to the same request/receipt reference. Revocation between capture and Runtime consumption must reject the packet.

## Tests and honest environment labels

- LOCAL_LINUX scratch mirror, CPython 3.13.5 x86_64: 20 targeted tests PASS; py_compile PASS. The tests cover signed P-256 fixture verification, request/result binding, tampered signature, altered PCM digest, short sample count, short monotonic duration, wrong source/generation, permission/finality failures, expiry, replay, revoked consent, missing revocation contract, no-PCM-persistence metadata and pinned-key reuse.
- Local P-256 verification microbenchmark: median 11.58 ms across 9 host verifications. This is an x86_64 host measurement, not a Redmi or ARM estimate.
- Full local Aii checkout: BLOCKED in this environment; no repository checkout was available and Git transport/DNS was not available. The scratch mirror is not a full-repository integration test.
- GitHub exact-head CI: queued at last readback — signed consumer workflow run 44988386423, staged/integrated regression run 44988386435. Recheck before claiming PASS.
- TERMUX/REDMI: no microphone capture or Android test. The companion branch inspected for this work has no AudioRecord provider or RECORD_AUDIO manifest entry. REDMI_UNVERIFIED.
- Deployment: no release SHA, no update request, no auto-updater action. NOT_RELEASED.
- No model/weight, permission, user data, app install or device setting changed.

## Research note

Android's official API docs say 44.1 kHz is the only AudioRecord rate guaranteed on every device; 16 kHz may work on some devices. The provider must check the actual rate and fail closed if it is not exactly 16 kHz. Android documents UNPROCESSED support discovery, foreground microphone restrictions, and capture silencing/device/preprocessing changes under concurrent capture. Sources are recorded as R-073 in V14_RESEARCH_LEDGER.md:

- https://developer.android.com/reference/android/media/AudioRecord
- https://developer.android.com/media/platform/mediarecorder
- https://developer.android.com/media/platform/sharing-audio-input

No new paper, model, OSS dependency or weight was selected or downloaded.

## Next concrete actions

1. Core: implement the visible AudioRecord provider and one-shot audio_outcome transport matching the exact schemas above.
2. QA: implement the Android permission/lifecycle/short-read/silence/reroute/revocation/replay/no-persistence negative controls.
3. Perception: wire the returned signed result into this consumer after the provider exists, then run the composed staged Runtime tests and real Redmi capture test.
4. Boss: rebase #2304 and this stacked PR onto the current Boss integration head, recompute exact pins and review the composed result. Keep it DRAFT until that review and exact-head CI are complete.
