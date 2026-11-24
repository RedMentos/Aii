# Research & Perception — Teacher Ear stream consumer correction (2026-11-24 run 29)

## Actual defect and code change

The optional contiguous Teacher Ear path had two mismatches at the real A5/A4/C3 consumer boundary:

1. `consume_pcm16_voice_window()` annotated `SherpaOnlineTeacher | SherpaOnlineTeacherStream`, and the stream implemented the same `transcribe_pcm16()` contract, but the runtime type guard accepted only `SherpaOnlineTeacher`. A real stream session therefore failed before entering the consumer.
2. A stream may revise already-emitted words. The stream contract represents a correction as `revision=true`, an empty delta, and a new `cumulative_hypothesis`. C3 previously read only the delta, silently losing the correction even when transcript admission was explicitly opted in.

Fixed on PR #2448:
- `audio_voice_cues.py` now accepts exactly the two declared Teacher Ear consumer types. ASR opt-in, transcript-persistence/admission opt-in, live lease, source/generation, temporal/VAD identity and default-off checks remain unchanged.
- With transcript persistence/admission explicitly enabled, C3 receives a bounded `asr_revision_untrusted=` summary containing the replacement cumulative hypothesis when `revision=true`; ordinary chunks still deliver only their delta. The transcript remains marked untrusted and has no truth, learning or action authority.
- The streaming Runtime integration regression now uses three contiguous 500-ms windows: first hypothesis, delta extension, then a correction. It asserts exact source hashes, chunk count/timing, delta-only second admission, explicit revision admission, and final stream cleanup. The test uses a fake recognizer; it does not prove real model inference.

## GitHub state and exact readback

- Repository: `RedMentos/Aii`
- Working branch: `research-perception/v14-audio-duplex-bridge-20261123-run21`
- PR: [#2448](https://github.com/RedMentos/Aii/pull/2448), base `8d93236c753f0194224c19edc7411d8d7082b1d6`, still DRAFT / NOT_RELEASED.
- Consumer type-gate fix: `d0c0f4ca366b97dcc1334d0a20f21bea94f5b9b6`; readback blob `5cf2a47b0bdf95d95e4aa3def2cd6ff817252893`.
- Revision-to-C3 fix: `2dd5c4990a84f88c9ad96dfcf37539bf25649df8`; readback blob `e46a47bb93615126c8ee149baebfb6df9813fbee`.
- Three-window integration regression: `dd409b8e19960e62826a281cd4a85de5459cb44c`; readback blob `4aa78e52f4848aba1d4ec9b1492e7c4b6e8ee696`.
- Branch and PR head readback at checkpoint: `dd409b8e19960e62826a281cd4a85de5459cb44c`.

## Tests — exact status

- LOCAL_LINUX full Aii checkout: BLOCKED. No repository checkout is mounted; `git ls-remote https://github.com/RedMentos/Aii.git` failed with `Could not resolve host: github.com`. No local `py_compile` or repository pytest was run for these changes.
- CI: exact-head push run 45294606645 and PR run 45294614943 for the revision code, then 45294672434 and 45294666726 for the updated integration test, all ended `startup_failure` with zero jobs. No test process ran; this is CI BLOCKED, not a code-test PASS or FAIL.
- The workflow `.github/workflows/v14-audio-duplex-bridge.yml` includes `test_audio_teacher_ear_runtime_integration.py`; it must execute on a functioning runner before acceptance.
- No local fake-runtime test was rerun in this execution. Prior focused audio-duplex tests and older module checks do not cover these new bytes.

## Product effect and limits

- Expected effect after tests pass: a configured, separately opted-in streaming Teacher Ear can enter the existing caller-supplied PCM consumer; incremental deltas reach C3, and corrected cumulative hypotheses are no longer silently omitted. The independent transcript-persistence/admission opt-in remains required.
- Current path remains synthetic caller-supplied PCM → RAW EAR/A5 → A4 → C3 admission. No real sherpa model was loaded in the regression, no normal full C3 generation was driven, and no Android microphone provider exists.
- Android AudioRecord/foreground-service capture, playback/full duplex, speaker identity/calibration, learned endpointing, Android lifecycle/revocation and Redmi timing remain NOT_IMPLEMENTED / NOT_VERIFIED as appropriate.
- Latest sanitized device evidence in public blocker #1904 comment 7108089370: base `8d93236` installed, auto-update enabled, pipeline Runtime `CI_WAIT`; separate diagnostics say `STOPPED_BY_USER`, autostart false and model process stopped. Do not restart or send CHAT_SEND. PR #2448 is not installed; REDMI_UNVERIFIED.
- No model, weights, dependencies, permissions, stored data or device state were changed.

## Research note R-122

Official sherpa-onnx docs (checked 2026-11-24) still list the English streaming Zipformer 20M model for resource-constrained embedded systems. Its int8 encoder is 41 MB, decoder 527 KB and joiner 253 KB; the model card declares Apache-2.0 and reports LibriSpeech WER 3.94 / 9.79 for greedy decoding. It is English-only and trained on LibriSpeech; those figures are not conversational, multilingual or Redmi measurements. sherpa-onnx itself is Apache-2.0 and the project was updated 2026-11-23; its Python wheel docs list Linux aarch64, not Android/Bionic Termux. Treat this only as an optional Teacher Ear candidate. No model or package was downloaded and no swap is proposed.

## Next executable step

1. Restore a runnable exact-head GitHub Actions job; then run Python 3.13/3.14 audio-duplex, Teacher Ear, RAW EAR consumer, staged Runtime and integrated regression on the exact current head.
2. Independent QA/Boss review the consumer gate, revision semantics, same-target-turn idempotency and commit-before-cancel/handoff recovery together.
3. Only after CI and source review, coordinate with Core/QA on the separate visible, user-started Android AudioRecord provider and revocation lifecycle. Keep capture and Teacher Ear model loading OFF until their own consent gates and device tests exist.

**User action: none.** Preserve the device's STOPPED_BY_USER state; do not issue a manual Termux command, restart, duplicate update request or model download.
