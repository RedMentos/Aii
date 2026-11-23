# Research/Perception handoff — 2026-11-23 run 4

## Checkpoint

- Release-development base branch: `gpt6/v13-private-remote-bridge-20261111`
- Verified base SHA at branch creation: `4dc7595f383e7ba932ee8e9fcf52c5541210ed5e`
- Working branch: `research-perception/v14-speaker-history-nonvoiced-20261123-run4`
- Code head before this handoff: `7a5aa48f63242cfc281addc62be0d39b7ad54582`
- Pull request: pending creation; this handoff is not a release or merge claim.

## Concrete runtime change

The existing timed RAW EAR consumer already sends caller-supplied frame embeddings through `consume_pcm16_voice_window → SpeakerChangeEvidenceRegistry.update → A4 → PerceptPacket/C3 admission`. The registry previously accepted embeddings from every activity class into its bounded reference deque. The A4 decision layer deferred non-voiced decisions, but the registry could still retain silence/noise/impulsive/uncertain vectors and use them as later voiced references.

This candidate now:
- accepts speaker-reference frames only when `activity_hint == VOICED`;
- validates and timestamps non-voiced windows but emits `SUPPRESSED_NON_VOICED`, accepts zero reference frames, and does not add their vectors to the history;
- tracks last input time separately from last voiced-reference time, preserving monotonic stream checks while resetting stale speaker history after a long non-voiced interval;
- retains the existing conservative `DEFER` behavior when no verified calibration artifact exists;
- keeps non-speech acoustic events in RAW EAR/A4's separate activity/salience path rather than dropping them;
- carries exact current-PCM SHA binding, the optional source-bound Teacher Ear hypothesis adapter, and a caller-supplied FASTDIAR embedding wrapper. None of these modules opens a microphone or loads a model.

The tests add four non-voiced activity negatives, history non-poisoning, long-gap reset, and preserve the existing 1s/2s reference-timestamp invariance and threshold-absent no-decision controls.

## Exact files at code head

- `v13/code/v13/audio_speaker_evidence.py` — blob `08b17a39923e0f59a5dbbb9f173954936e59f85a`
- `v13/code/v13/audio_voice_cues.py` — blob `1fc3ac7b6624fcd0d1aef52a77ae6221fdf43288`
- `v13/code/v13/audio_teacher_ear.py` — blob `5a26193c94c864e6ad3af55def59bae040e59f35`
- `v13/code/v13/audio_fastdiar_adapter.py` — blob `f2ebf6d4629777162c04d8f981b7b8c7e11c727e`
- `v13/code/tests/test_audio_speaker_evidence.py` — blob `9cc95cfff3625965d8c881d4347a048a21246ebe`
- `.github/workflows/v14-fastdiar-adapter.yml` — blob `3bfe443cfeb1187f6171c4981f2c12691b07a003`

## Test and platform boundary

- LOCAL_LINUX full Aii suite: BLOCKED. The execution container has no repository checkout; `git ls-remote https://github.com/RedMentos/Aii.git` failed at DNS resolution. No local repository test or compile result is claimed.
- GitHub exact-head CI: PENDING at this checkpoint. The new workflow covers Python 3.13 and 3.14, py_compile, the FASTDIAR adapter tests, the speaker registry and real synthetic A5→A4→C3 consumer regressions, and the public-repository privacy scan.
- TERMUX/REDMI: `REDMI_UNVERIFIED`. No connected phone, AudioRecord microphone capture, speaker model inference, Android latency/RSS or installed candidate receipt was obtained.
- Deployment: `NOT_RELEASED`. Existing auto-update/installed-state evidence applies only to the previously installed SHA, not this branch. No UPDATE_REQUEST was sent.

## Research / reuse boundary

- FASTDIAR paper: arXiv:2610.02941, submitted 2026-10-02; preprint, not confirmed peer-reviewed in this check. It emits 192-D frames every 80 ms from a 2-second causal context, uses an 800-ms self-similarity score and reports a fixed 960-ms diarization delay. Low similarity can also arise from silence/noise; only confident frames update cluster anchors.
- Official code repository: `microsoft/fastdiar`, MIT code license. Its README pins PyTorch 2.13, torchaudio 2.11 and torchcodec 0.15 and documents CPU/GPU inference; this is not a lightweight Termux dependency stack. The repository README does not establish a separate license for released checkpoint weights or all training/evaluation datasets.
- No FASTDIAR code was vendored, no weights/checkpoints were downloaded, and no new runtime dependency was installed. The adapter only validates caller-supplied 192-D embeddings and hashes a local checkpoint if a caller supplies one.
- Primary references: https://arxiv.org/abs/2610.02941 and https://github.com/microsoft/fastdiar

## Integration owner handoff

Core must rebind its staged composer/source pins to the exact new `audio_voice_cues.py` and `audio_speaker_evidence.py` blobs before claiming the audio path is integrated. QA should independently inspect the new suppression branch and retain the negative controls. Boss/Integrator should append the verified PR/CI result to `V14_USER_NEXT_ACTION.md` and the shared board after CI finishes; this branch does not modify those shared-owner files.

## Next executable action

Run the exact-head workflow. If green, request Core's source-pin rebinding and staged/integrated consumer run; then QA review, merge readiness review, and only after the normal release pipeline a separately consented Redmi install receipt. The only current user action is **none**.
