# Research & Perception — RAW EAR speaker-window chronology

Date: 2026-11-25
Branch: `research-perception/v14-audio-speaker-window-order-20261125-run27`
Base: PR #2472, `402b7aa5f09f04f6d11e7e14bd0b8d6e14adbfae` (current-release rebase at `8d93236c753f0194224c19edc7411d8d7082b1d6`).

## Defect and consumer

The A5 → A4 → C3 RAW EAR consumer calls `SpeakerChangeEvidenceRegistry.update()` from `audio_voice_cues.consume_pcm16_voice_window()`. The registry previously validated only the ordering of supplied embedding-frame end timestamps. It did not retain or validate the complete input window's `start_ms/end_ms`.

That allowed a later window to start before the preceding accepted window while its sparse supplied embedding-frame end timestamps still advanced. The separate `TemporalVoiceEvidence` smoother already rejected backwards window starts; the speaker-evidence branch did not apply the same interval invariant.

## Change

- Track last accepted window start/end separately from the speaker-reference frame clock.
- Reject backwards starts and non-advancing ends before any history/state publication.
- Preserve interval chronology when a model/calibration revision or a long voiced-history gap resets embedding history.
- Equal starts remain valid for cumulative/sliding windows when the end advances.
- No speaker identity is assigned; similarity remains diagnostic and caller thresholds remain uncalibrated. No PCM/vector persistence, model load, learning authority, or action authority is added.

## Tests added

1. Backwards start with advancing embedding-frame timestamps is rejected; previous state remains intact; equal-start cumulative continuation succeeds.
2. Window end regression is rejected even if supplied frame timestamps themselves advance.
3. Model-revision history reset does not reset the stream's interval clock.

## Verification boundary

- Exact repository test command: `python -m pytest -q tests/test_audio_speaker_evidence.py` (existing `v14-raw-ear-fastpath` workflow runs it on Python 3.13 and 3.14).
- LOCAL_LINUX full checkout/exact test: BLOCKED / NOT_RUN in this execution environment; GitHub DNS cannot resolve and no repository checkout is mounted.
- Redmi/Termux: REDMI_UNVERIFIED. No phone receipt, microphone capture, device action, update request, model/weight/permission change.
- Release: NOT_RELEASED. This branch is a child of #2472 and requires its full review/integration chain.

## Integration

Core/QA should retain the source-bound consent lease across the full A5/A4/B1/B2/C4/C3 turn as already required by #1904. This change only hardens the optional source-bound speaker-similarity history used inside the existing audio consumer. It does not resolve the basic-chat/B1/B2 P0, native microphone capture, calibrated diarization, or trained latent coupling.
