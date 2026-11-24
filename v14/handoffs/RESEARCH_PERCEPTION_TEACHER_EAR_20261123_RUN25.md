# Research & Perception Handoff — Optional RAW EAR Teacher Ear (2026-11-23, run 25)

## Scope and ownership

This is an additive A-plane / RAW EAR / A4 / C3 consumer slice on the existing Research & Perception branch for PR #2448. It does not change the historical Canon, active master, model inventory, Age, learning rights, permissions, device data or release branch. Boss owns shared Work Board and V14_USER_NEXT_ACTION synchronization; this handoff supplies the verified facts for that update.

## Code and commits

- Branch: research-perception/v14-audio-duplex-bridge-20261123-run21
- Base: release-development SHA 8d93236c753f0194224c19edc7411d8d7082b1d6
- New adapter: v13/code/v13/audio_teacher_ear.py (commit a336f766a34dc214f0bdae358c743a6db8ccbb76)
- Adapter unit tests: v13/code/tests/test_audio_teacher_ear.py (commit bc2ad501789c96ae5f8e9c0541cdedb83c9756b8)
- Runtime-consent integration tests: v13/code/tests/test_audio_teacher_ear_runtime_integration.py (commit 24857d462b8001848a3680efe0cf6c7a123d8443)
- Runtime consumer wiring: v13/code/v13/audio_voice_cues.py (commit d0fb4e388872590b07df12673eb065b388481516)
- Workflow expansion: .github/workflows/v14-audio-duplex-bridge.yml (code-bearing CI head b08df7bd6fbe6571ea4a980ed024b5d8247566a3)
- Research ledger append R-117: v14/V14_RESEARCH_LEDGER.md (commit ee9a293004b445c6b4193e10f3df0ee80dc6fb75)

PR #2448 remains DRAFT. No release SHA was created; NOT_RELEASED.

## Actual runtime behavior added

The existing acoustic/prosodic RAW EAR remains primary and unchanged by default. The optional SherpaOnlineTeacher adapter:

1. Accepts caller-supplied PCM16 only; no microphone or AudioRecord access.
2. Requires a live caller-held AudioConsentLease and separate teacher_asr_opt_in=True.
3. Loads no model unless explicitly configured. It never downloads model files; a local manifest must pin encoder/decoder/joiner/tokens hashes and paths.
4. Uses CPU and 1–2 threads; returns an untrusted source/generation/consent-bound hypothesis with a window-level time interval, not word-level timing.
5. Keeps the canonical asr_transcript field null. The nested acoustic.teacher_ear record is persisted only when transcript_persist_opt_in=True. The same second opt-in is required before text is added to C3 admission. Without it, the hypothesis is returned only in the ephemeral result.
6. Grants no truth, learning, action, speaker-identity or permission authority.

This is a wired synthetic consumer path, not actual sherpa model inference or user-visible voice. The adapter does not replace RAW EAR nonverbal cues, VAD, temporal voice evidence, duplex policy or the separate speech-output/effector path.

## Tests and evidence

LOCAL_LINUX, CPython 3.13.5:
- py_compile for the adapter, unit test source and Runtime-integration test source: PASS.
- Isolated adapter unit suite: 8/8 PASS, using a deterministic fake recognizer and NumPy-compatible fixture.
- Full Aii Runtime integration tests: NOT_RUN locally; the environment has no mounted Aii checkout and GitHub DNS is unavailable.
- Actual sherpa_onnx import/native model inference: NOT_RUN; package is not installed.

Exact-code GitHub Actions for b08df7bd6fbe6571ea4a980ed024b5d8247566a were queued at handoff creation: audio duplex, staged/integrated, privacy, pre-processing consent, RAW EAR regression and deployment workflows. No PASS is claimed until their exact results are read back. Later ledger/handoff commits are documentation-only and do not change the tested code bytes.

Environment classification:
- LOCAL_LINUX: isolated adapter tests PASS; full repository integration BLOCKED/NOT_RUN.
- CI: QUEUED at exact code head; results pending.
- TERMUX/REDMI: REDMI_UNVERIFIED; no device connection or test.
- Native model/weights: NOT_RUN / NOT_INSTALLED.
- Android microphone and audible playback: NOT_IMPLEMENTED / NOT_VERIFIED.

## Research and model rights

R-117 records the official sherpa-onnx Apache-2.0 runtime and the linked Apache-2.0 English-only 20M Zipformer candidate. The current official model catalogue lists roughly 41 MB int8 encoder + 527 KB decoder + 253 KB joiner; the 20M model is trained on LibriSpeech and must not be assumed to understand German. No similarly small German streaming Zipformer was identified in the reviewed official online catalogue. The Python wrapper's Android Bionic ABI, real model RSS/RTF and Redmi accuracy are unknown. No code, package, model, weight or dataset was downloaded or added.

## User effect, risks and next owner

If later enabled and supplied with a rights-cleared local model, a caller can optionally produce a time-bounded ASR hypothesis from an already-consented audio window. Default behavior remains acoustic-only; transcript persistence and C3 admission need a second explicit flag. No model change or device permission is required for the current code-only PR.

Next:
1. Read exact-head GitHub Actions for b08df7bd6fbe6571ea4a980ed024b5d8247566a. Fix any genuine failure and rerun.
2. QA independently reviews opt-in, source-hash, revocation, packet-persistence and C3-admission regressions.
3. Boss integrates only after exact CI and review; Core still owns the normal Runtime/Operator call site and real Android AudioRecord provider/lifecycle.
4. Before any sherpa package/model experiment, obtain separate explicit approval; before production swap, ask again. Do not download anything or send UPDATE_REQUEST now.

Latest known private device receipt before this candidate: installed 8d93236c753f0194224c19edc7411d8d7082b1d6, updater enabled and UP_TO_DATE. That receipt does not include this unmerged branch. No manual Termux command, UPDATE_REQUEST, model swap or device action is required.
