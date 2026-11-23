# Research/Perception handoff — 2026-11-23 run 4

## Checkpoint

- Release-development base branch: `gpt6/v13-private-remote-bridge-20261111`
- Verified base SHA at branch creation: `4dc7595f383e7ba932ee8e9fcf52c5541210ed5e`
- Working branch: `research-perception/v14-speaker-history-nonvoiced-20261123-run4`
- Current branch head after this handoff update: `0b5fff121828363fd1bea5fd96e0fcaefabeaf22`
- Pull request: [#2433](https://github.com/RedMentos/Aii/pull/2433), DRAFT / NOT_RELEASED.

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
- `v13/code/tests/test_audio_speaker_evidence.py` — blob `5b2cddd3b30a98c5d13ee463fb9934f97bb31d99`
- `v13/code/tests/test_audio_fastdiar_adapter.py` — blob `32486cb34b655f76133b0c1e157e3c60d1442cd6`
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


## First exact-head CI cycle — 2026-11-23

The first CI cycle on the code candidate exposed two consumer-contract issues and they were fixed before proceeding:

- The RAW EAR/WebRTC comparator workflow still expected the pre-update `audio_voice_cues.py` blob. Its expected source pin now matches `1fc3ac7b6624fcd0d1aef52a77ae6221fdf43288`.
- `v13/code/experiments/benchmark_raw_ear_backends.py` used the new speaker registry without the required `current_chunk_sha256`; it now passes the exact synthetic PCM digest already computed by the benchmark.

First-run evidence at head `09f4233e4b1a9f39d9b95b02acaa71cf5681e7f3`:
- FASTDIAR diagnostic adapter: Python 3.13 and 3.14 SUCCESS.
- RAW EAR pre-processing consent-revocation QA: SUCCESS.
- RAW EAR prosody-to-attention: Python 3.11 and 3.13 SUCCESS.
- Public privacy scan: SUCCESS.
- NumPy backend regression suite: 130 tests PASS on Python 3.13 and 3.14; its later benchmark step failed only because the new required PCM digest was omitted.
- RAW EAR/WebRTC comparator: 8/9 tests PASS; the sole failure was the stale expected source blob.
- Staged/integrated matrix was still running at first readback.

Both failures were corrected and read back. Current branch head: `86620113afceb5287aaa840aa014f9e8e304d416`.
- `v13/code/experiments/benchmark_raw_ear_backends.py` blob: `99833db447768198b85541f99dce6e2ce34abeb6`.
- `.github/workflows/v14-raw-ear-vad-comparison.yml` blob: `d9f29037f3eef15bde87d10a684ff872ed53c571`.
- New exact-head CI after these two fixes: QUEUED/IN_PROGRESS at this readback. Do not count either fix as tested until the rerun completes.



## Run 4 follow-up — current exact checkpoint

- Branch head after the test, ledger and handoff updates: `0b5fff121828363fd1bea5fd96e0fcaefabeaf22`.
- New integration regression: `test_impulsive_non_speech_reaches_a4_novelty_without_speaker_or_interrupt`. It sends one exact-hash-bound synthetic PCM impulse through `consume_pcm16_voice_window`, supplies a matching caller embedding batch, and asserts IMPULSIVE A4 novelty, no external interrupt, `SUPPRESSED_NON_VOICED`, zero accepted/history frames, `DEFER`, C3 activity visibility and no vector persistence.
- Exact previous-head workflow results at `0d97e9faec926992acc6b513381fa15edc93b08a`: FASTDIAR adapter, NumPy backend, WebRTC/libfvad comparator, RAW EAR consent-revocation, RAW EAR prosody-to-attention and public privacy scan all **SUCCESS**. The shared staged/integrated workflow **FAILED** because Core's `integrated_audio_context_candidate_20261121.py` still expects `audio_voice_cues.py` Git blob `b18e450162b062b09368a12b1ca18924ed8c5025`, while this branch's exact blob is `1fc3ac7b6624fcd0d1aef52a77ae6221fdf43288`. The failure fan-out is 16 failed / 237 passed / 10 skipped / 2 errors / 47 subtests; both migration cases return PARTIAL downstream. No Perception-owned file was changed to hide or bypass this pin.
- Fresh exact-head CI for `0b5fff121828363fd1bea5fd96e0fcaefabeaf22` is required because the impulse test and ledger/handoff updates were committed after that previous run. No PASS is claimed for the new test yet.
- LOCAL_LINUX full Aii checkout remains BLOCKED: no repository checkout is mounted and GitHub DNS lookup fails in the execution container. A CPython 3.13.5 isolated numerical check of the synthetic impulse yielded 32,000 bytes, RMS 0.007905, crest 126.49 and the expected 0.35 A4 novelty floor; this is not a repository test.
- REDMI remains `REDMI_UNVERIFIED`: no AudioRecord provider, microphone capture, native speaker inference, Android RSS/latency or new installed SHA. No model/weight/permission/data change and no UPDATE_REQUEST.
- Research ledger appended as R-083 with full-paper FASTDIAR confidence-gate details, reported conditions, license/weight caveats and the explicit distinction between voiced-only history and calibrated confidence gating. `V14_USER_NEXT_ACTION.md` was updated with the verified current checkpoint and no-user-action boundary.
- **Next:** poll exact-head CI; Core must rebind both current audio source blobs and recompute dependent recovery/stage/deployer pins bottom-up; QA review the non-voiced and A4 impulse path. No user action is required.
