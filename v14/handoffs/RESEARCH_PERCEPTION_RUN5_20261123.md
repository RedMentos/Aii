# Research & Perception — run 5 handoff (2026-11-23)

## Current branch and integration
- Product-code base: b20e9b1f3dd53af472055adb43da628785494ec4.
- Latest Boss overlay: dfa3945b2bbfdb65d932db74e02f402435494ec4; this adds current V14 work-board/workplan/research/handoff updates but does not change product-code base.
- Perception PR #2433: https://github.com/RedMentos/Aii/pull/2433.
- Branch: research-perception/v14-speaker-history-nonvoiced-20261123-run4.
- Code head before merging the new Boss overlay: cdc7bcc9299cdaa08dbc3b38581503fcdc381ffa.
- PR remains DRAFT / NOT_RELEASED. No force-push.

## Implemented and exact-head tested
1. Non-voiced speaker-history protection: only caller-supplied VOICED embeddings enter persistent speaker-reference history; non-voiced/uncertain frames remain eligible for RAW EAR/A4 novelty but are suppressed from speaker anchors. Impulse fixture asserts no false interrupt, zero accepted speaker frames, DEFER and no persisted embedding vectors.
2. Source-bound A4 outcome: Runtime calls the A4 source-outcome path after final C3 output; source identity/hash and exact Store span are verified before the bounded cue-coverage label and durable exactly-once receipt/policy update.
3. Atomic A4 → N10 loop: A4 computes δ = usefulness − prior policy mean, emits signed reward_error=δ and surprise=|δ|, and carries negative reward_error into next-event caution while surprise contributes salience. Policy state, durable receipt and ModulatorPacket commit in the same Store.tx via Neuromod.signal_in_transaction.
4. Test contract correction: ModulatorPacket.path_id is the canonical field, matching Neuromod.signal.

Code commits:
- 9cd05b97f41f32248540a5a91efe359cfd719171 — canonical path_id test fix.
- 7e24f240682121bd5c64d50065d8bd1f2e84ff88 — atomic A4/N10 packet+receipt+policy transaction.
- ebe09ea32d78ee2daad16e41954217ab3f617dcd — preserve signed negative reward prediction error and route it to next-event caution.
- cdc7bcc9299cdaa08dbc3b38581503fcdc381ffa — fail-closed test for signal_in_transaction outside an active transaction.

Exact GitHub Actions on code head cdc7bcc:
- PASS run 45163129599, V14 A4 source-bound attention outcomes, Python 3.13 and 3.14.
- PASS run 45163129554, v13-private-remote-bridge-tests / offline-bridge-security.
- Prior merged head 8bf7bd6: PASS FASTDIAR adapter, RAW EAR NumPy backend, consent-revocation QA, WebRTC/libfvad comparator, prosody-to-attention regression, runtime deploy integrity and release-event integration.
- Prior merged head Core same-turn and staged/integrated failed before consumer execution at record_only_controller_guard_20261116.py:65 because its SHA-256 allowlist still expects old v13/attention.py bytes; the staged audio composer also pins old audio_voice_cues.py. Core owns those files. The new code head did not receive a fresh Core PR-event run.
- Privacy scan attempt 1 failed only at actions/checkout after repeated GitHub network timeout/early EOF; retry attempt 2 was queued on prior head 8bf7bd6.
- LOCAL_LINUX full Aii checkout/pytest: BLOCKED / NOT_RUN (no checkout mounted; git ls-remote failed due GitHub DNS). Local SQLite transaction contract reproduction PASS, but not the project suite.

## Private device evidence
- PIPELINE_STATUS #767: installed 8bf44cb, auto-update enabled, Runtime/Dashboard CI_WAIT, last_error NONE; it predates green b20e9 integration and does not prove the current candidate installed.
- DIAGNOSTICS #764: stored turn 57.739 s total / 41.627 s TTFT / 38.945 s C3 prefill / 751 prompt / 2 generated; B1/B2 TIME_BUDGET 53.2/54.2 s; correctness UNKNOWN.
- HEALTH #765: 1,209 MiB MemAvailable / 5,569 MiB and 1,030 MiB disk; runtime unavailable in HEALTH; LEARNING_STATUS #766 unavailable.
- No CHAT_SEND, LOG_PAGE, UPDATE_REQUEST, shell, microphone permission/capture, model/weight/permission/data mutation. No new code is installed.

## Research
- R-108: full Nemotron 3 Diarization paper/model-card review. OpenMDW-1.1 weights, 107 MB Q8_0 GGUF, 99.2M parameters, GPU-only paper measurements. NeMo-Speech.cpp Apache-2.0 runtime does not document Android/ARM64 support.
- sherpa-onnx Apache-2.0 and Android arm64 support; documented diarization path is offline and model weights have separate licenses.
- R-109: bounded A4 policy prediction residual feeds N10 and next-event attention; atomicity and negative omission tests pass exact-head CI. It is a heuristic policy/modulator loop, not neural-weight training or truth.
- No model or dependency downloaded; no model selected.

## Next integration
- Core: rebind record_only_controller_guard SHA-256 for attention.py and staged audio composer pins for audio_voice_cues.py, audio_speaker_evidence.py and attention.py; recompute dependent recovery/stage/deployer hashes bottom-up. Do not weaken gates.
- JEPA/N10: review signal_in_transaction and reward_error/surprise semantics.
- QA: review non-voiced suppression, atomic rollback, consent revocation and future microphone-provider lifecycle. Microphone remains OFF; no AudioRecord provider.
- Perception: run source-disjoint A4 outcome/retention ablation after cross-lane integration is green.
- Redmi audio capture, speaker inference, native latent exchange and Android performance remain REDMI_UNVERIFIED.
- User action: NONE.
