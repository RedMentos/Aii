# Perception 2026-11-11 17:00 – B1 timed acoustic features

Branch: `research-perception/audio-b1-prosody-20261111-1700`; base: `research-perception/audio-view-numeric-20261111-1600` (PR #1782).

## Concrete change
`acoustic_views` B1_DETAIL now retains per-frame `pitch_hz`, `voiced_probability`, and `non_speech_probability` alongside RMS and timestamps. Previous B1 output dropped these fields, preventing later prosody/voice/non-speech consumers from receiving already represented acoustic evidence. B2 energy envelope and JEF authority remain unchanged. B1 still samples bounded frames, never asserts transcript, speaker identity or acoustic classification truth.

## Evidence and limits
Added synthetic test `test_b1_preserves_timed_acoustic_features_without_semantic_claims`. GitHub source commit is verifiable; Python test execution is **UNVERIFIED** because GitHub DNS is unavailable in the local test container. No device measurements, no Android microphone authorization, no A3 teacher weights, no native B/C runtime wiring. PCM feature extractor currently uses 0.0 for unmeasured probabilities; this must not be interpreted as real classification confidence. Future contract should explicitly distinguish unknown/unmeasured from observed zero (Core/JEPA agreement required).

## Next integration
1. Run `cd v13/code && python -m unittest tests.test_audio_views -v` (or discovery path) against exact branch commit.
2. Core/JEPA consume B1 timed feature keys under SHADOW; maintain zero action/training authority.
3. Provide explicit measurement-availability fields in RAW EAR before any semantic prosody/speech head learns from these synthetic zeros.
4. Verify persistent Store restart, then Android permissioned audio input, A3 teacher/student and bounded mobile memory/latency.

No change to Age-0/STEP2/B3 gates. No desktop prerequisite.