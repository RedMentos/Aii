# Research/Perception handoff — signed one-shot Android audio consumer — 2026-11-22

## Checkpoint

- Repository: RedMentos/Aii
- Branch: research-perception/v14-audio-capture-consumer-20261122-run11b
- Code commit: 05d0e7ecf08fdf69537123793e908bcb479dbefa
- PR: #2312 — https://github.com/RedMentos/Aii/pull/2312
- Direct base: QA PR #2286 branch head 58666ddfc9945612a2117e1a844f812442d4ca64; this supplies the existing pinned P-256 companion verifier/controller.
- Audio ingress dependency: Perception PR #2304 adds audio_input.py. This branch carries the exact same blob 1e9daddcb5dfd8bfb7911090218b4eaf1f103d41 temporarily so the combined consumer is executable before the two parent lanes are integrated. When #2304 is merged, deduplicate the identical file rather than keep two implementations.
- Current Boss integration branch head read before this work: 0441ab8b229dd17343c03d9350c6848115220416. The Core/QA and Perception parent branches still need rebase onto that integration head before release review.

## What the code actually does

New file: v13/code/v13/audio_capture_consumer.py.

1. Builds a fixed request for one second or less of mono 16-kHz PCM16. The request includes a 32-hex request ID, short expiry, canonical SHA-256 digest, permission_bypass=false and model_authority=false. Building it does not contact Android or request a permission.
2. Uses the existing companion controller's pinned key and receipt DB via verifier_from_pinned_controller(controller). It does not auto-pair or trust a new key.
3. Verifies the signed result envelope and P-256 signature using the existing android_companion_ecdsa primitive. It binds the request digest/ID, android.mic source, expected active Runtime generation, PCM SHA-256, exact sample count, monotonic capture interval, 16-kHz mono PCM16 format, actual UNPROCESSED or MIC source, Android RECORD_AUDIO status, local consent, and FINAL provenance.
4. Commits both the nonce and request ID to the existing receipt DB before one-shot submission. Only nonce/request metadata is stored; PCM is not written to disk.
5. Calls audio_input.submit_audio_only(runtime, audio_window) with the live consent check, linearizable guard and two-phase revocation callback. The Runtime still performs its own consent/lease checks. The returned status is SUBMIT_RETURNED, not a claim of semantic use or successful speech recognition.

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

- LOCAL_LINUX scratch mirror, CPython 3.13.5 x86_64: 20 targeted tests PASS; py_compile PASS. The tests use the exact P-256 ECDSAReceiptVerifier source from the QA branch and exact audio_input source from #2304; the companion protocol dependency was reduced to the two symbols imported by the verifier. This is not a full Aii checkout.
- P-256 verification microbenchmark: median 13.864 ms across 9 host verifications. This is an x86_64 host measurement, not a Redmi or ARM estimate.
- Full local Aii checkout: BLOCKED in this environment; no repository checkout was available and Git transport/DNS was not available. The scratch mirror is not a full-repository integration test.
- GitHub exact-head CI: pending/in progress at last readback — signed consumer workflow run 44988855730, staged/integrated regression run 44988855677. Recheck before claiming PASS.
- TERMUX/REDMI: no microphone capture or Android test. The companion branch inspected for this work is still a launch_app-only capability and has no AudioRecord provider or RECORD_AUDIO manifest entry. REDMI_UNVERIFIED.
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
4. Boss: rebase the Core/QA and Perception parents onto the current Boss integration head, deduplicate the identical audio_input.py dependency, recompute exact pins and review the composed result. Keep PR #2312 DRAFT until that review and exact-head CI are complete.
