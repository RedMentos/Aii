# Research & Perception handoff — RAW EAR next-delta prediction

Date: 2026-11-25
Owner: Research & Perception
Repository: RedMentos/Aii
Candidate: PR #2498 — https://github.com/RedMentos/Aii/pull/2498
Branch: research-perception/v14-raw-ear-next-delta-20261125-run13
Base: research-perception/latent-event-scope-20261125-run12 (PR #2496; stacked candidate, not a release base)

## Code delivered

- Code checkpoint: 58aee47736ddddde7d19c390bd878b37481f5fe1
- Latest branch checkpoint after docs/board sync: f159e4be437a1e8fe60669539c9d74a06909086d
- v13/code/v13/audio_temporal_prediction.py: 13-D normalized RAW EAR cue vector (8 continuous values + 5 activity indicators), absolute cue-delta prediction, 182-parameter linear LMS, zero-context-only bias row, gradient norm and weight bounds.
- v13/code/v13/audio_voice_cues.py: calls the predictor on FINAL windows and includes only its capped 0.10 predictive novelty in A4. It does not alter external_interrupt, speaker evidence, C3 summary, PerceptPacket payload, truth/action authority or persistent model weights.
- State is process-local, bounded to 16 source/generation streams and bound to SHA-256 of the active consent receipt. PROVISIONAL is ignored. Source/generation reset, receipt rotation, chronology/gap reset, LRU eviction and explicit runtime reset clear state. No PCM, transcript, speaker embedding or training sample is stored.
- v13/code/tests/test_audio_temporal_prediction.py: unit and actual caller-PCM16 consumer tests.
- .github/workflows/v14-raw-ear-fastpath.yml: includes new module and test.
- .github/workflows/v14-raw-ear-vad-comparison.yml: includes new module and updates exact audio_voice_cues.py blob pin to a8fc1ab23b79231b44738892e3c120771c072687.

## Tests and exact evidence

- LOCAL_LINUX / isolated module copy / CPython 3.13.5: py_compile PASS; 10/10 unit tests PASS. This was not a full Aii checkout.
- LOCAL_LINUX microbenchmark: 10,000 updates in ~0.74–0.84 s; 182 parameters; ~6.8 KB for one stream's weight rows and list storage. No Android inference claim.
- CI / exact PR RAW EAR fastpath: 126/126 tests PASS on Python 3.13 and 3.14. This includes the new synthetic A5→A4→C3 consumer test, consent reset/provisional behavior and existing speaker/voice tests. The same workflow's py_compile, synthetic benchmark and public-content privacy scan passed.
- CI / VAD comparison: first run FAIL because the comparison job expected the pre-change audio_voice_cues.py blob. The workflow pin was corrected to the new exact blob. Rerun was pending at the last recorded checkpoint.
- CI / staged-runtime and integrated-regression: queued/in progress at the last recorded checkpoint; not marked PASS.
- Local full-repository tests: BLOCKED because no Aii checkout was mounted and GitHub DNS was unavailable to the local container.
- Device: REDMI_UNVERIFIED. No connected phone, AudioRecord provider, microphone, Termux, Redmi native timing/RSS, install or deployment receipt was available. NOT_RELEASED.

## Research and limits

R-142 records the full NAPE paper review: arXiv:2608.19863 v1 (2026-08-20). The paper uses causal next log-mel patch-embedding prediction, shift, causal masking and stop-gradient. It is a preprint; no peer review verified. NAPE-S is ~19M parameters, but the reported pretraining used AudioSet and 46-GB L40S GPUs. The OSS repo main revision is 489319835e9efb19028b08dfe5d215e92d64e567; its README MIT badge conflicts with the Apache-2.0 LICENSE, and no separate checkpoint license was verified. No code, model, weight, dataset or dependency was reused.

This V14 pilot is not NAPE, a learned spectrogram patch encoder, JEPA/EMA, persistent body-weight learning or full-duplex voice. It measures online pre-update error against a persistence baseline on deterministic synthetic alternation/omission fixtures. It has no frozen-weight held-out cohort and must remain SHADOW.

## Shared records updated

- v14/V14_RESEARCH_LEDGER.md — R-142.
- v14/V14_LIVE_WORKPLAN.md — this run's code/test/device checkpoint.
- v14/V14_WORK_BOARD.json — V14-022 and V14-006 run13 checkpoint.
- v14/V14_USER_NEXT_ACTION.md — next action and no user action required.
- v14/V14_CANON_COVERAGE_INDEX.md — A3 audio/A4 evidence overlay.
- Historical V13 Canon bytes and V14 master were not modified; no master backup was required.

## Next executable work

1. Complete exact VAD-comparison rerun and staged/integrated CI for PR #2498; do not weaken source-hash checks.
2. Add a frozen-weight held-out cohort and compare against persistence, no-predictor, shuffled-cue and no-consent controls.
3. Measure source/voice retention and confirm A4 novelty does not create false interrupts.
4. Only after QA exposes an explicit, user-approved AudioRecord provider/receipt contract, connect permitted Android microphone input and obtain actual Redmi evidence.
5. Keep persistent model-weight updates, learned audio patch embeddings, JEPA/EMA coupling and full-duplex speech as separate open requirements.

User action required: NONE. No manual Termux command, model download, permission change or device operation requested.
