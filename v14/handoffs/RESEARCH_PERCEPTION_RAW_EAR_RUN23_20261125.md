# Research & Perception — RAW EAR Run 23 handoff (2026-11-25)

## Runtime change

Draft PR #2498 was extended with a signed omission/negative-prediction-error path.

- `v13/code/v13/audio_temporal_prediction.py`: `AudioTemporalPredictor.update()` now reports mean signed prediction error, negative prediction error, omission magnitude and commission magnitude separately. The existing LMS update, weight layout, learning rate, persistence schema and consent/reset behavior are unchanged.
- Adds `predictive_omission_novelty()`, which returns zero unless status is `SHADOW_MEASURED`; measured omission is capped at the existing 0.10 A4 gain.
- `v13/code/v13/audio_voice_cues.py`: the A4 consumer now routes omission novelty into the novelty channel only. It does not modify `external_interrupt`, C3 summary, speaker identity, action/truth/learning authority, or source/consent gates.
- Provisional/unavailable audio windows produce zero omission novelty.

## Commits / readback

- Predictor: `8839946f17973c1a7bd238a60e3173e3f6005815`.
- A4 consumer: `68192953fb3f91163f1488eea095b2e396631dce`.
- Tests: `1d1e53d47424098c2b9a781b75d4b6f8c26cacb2`; test blob readback `65a2a71140d98058dcc8f68fcc790211fccfcd9e`.
- Research ledger R-162: `042ac79d4f378b773660018d316c73c0cd748bee`.
- Workplan append: `7afa1978c0081ce79a3236efcb1764c1f4fc9e21`.
- Next Action append: `5b5efe38da09f10c6e96b9954c214bc907442620`.

## Test evidence

LOCAL_LINUX CPython 3.13.5 formula-level reproduction PASS: eight repeated high-delta updates followed by a zero-delta omission yielded signed prediction error -0.968896, omission magnitude 0.968896, commission 0 and the previous positive-only excess-error channel 0. This confirms the sign decomposition of the current LMS equations only; it is not a run of the repository module or A4 consumer.

- Exact modified source and consumer were not available in the local container: no Aii checkout is mounted and `raw.githubusercontent.com` DNS resolution failed.
- Exact branch CI for the new head: NOT_YET_OBSERVED.
- Full local repository pytest, native audio model, AudioRecord/Termux/Redmi: NOT_RUN.
- Prior #2498 fastpath/consumer CI is for the earlier tested head and does not cover these changes.

## Research and rationale

R-157's mistake-gating work suggests that prediction errors should retain direction and may be useful as a learning/salience signal, but its classification results do not validate audio omission detection. This PR makes the narrower, falsifiable signal available: when the predictor expects a repeated acoustic transition and the transition is absent, the signed error is negative and omission magnitude is positive even when the model beats the persistence baseline. It is not proof that a semantic event was omitted.

## Open integration blockers

- Existing Core staged/integrated audio composition still has a stale exact source pin for `audio_voice_cues.py`. Do not relax the pin; Core/QA must rebind the exact reviewed blob through the recovery → stager → deployer chain.
- Keep the predictor SHADOW/capped. Next tests: held-out alternating/omitted events, no-predictor, shuffled-cue, silence/noise, source/session reset, consent rotation, and restart/rollback.
- No persistent raw data, transcript, speaker embedding, dataset or model weight was introduced.

## Device / deployment

No private live phone receipt or microphone capture occurred. Last available private V13OBS snapshot is historical (2026-11-24): updater enabled, AI runtime STOPPED_BY_USER at `8d93236c753f0194224c19edc7411d8d7082b1d6`; current installed SHA is unknown. No update request, shell, restart, permission change, model/weight swap or data mutation.

REDMI_UNVERIFIED. NOT_RELEASED. No user action needed.
