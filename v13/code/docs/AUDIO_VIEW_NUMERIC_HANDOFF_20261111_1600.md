# Perception handoff — 2026-11-11 16:00 Europe/Berlin

Owner: research-perception. Parent: research-perception/audio-view-integrity-20261111-1500 (PR #1779).

## Finding
The B1/B2/JEF acoustic consumer compared RAW EAR and A5 numeric fields for equality, but if BOTH copies were corrupted in the same way (e.g. pitch_hz=NaN or non_speech_probability=-0.1), the equality guard passed. RMS already had downstream validation; other numeric fields did not. This is an integrity and finite-number validation gap, not evidence of native Android input.

## Change
- v13/code/v13/audio_views.py: validate pitch_hz (None or finite 20..2000 Hz) and voiced/non-speech probability (finite 0..1) before emitting SHADOW views.
- v13/code/tests/test_audio_views.py: matching dual-copy corruption regression for NaN, inf, bool, negative, None.
- No changes to B/C Runtime, authority, permissions or active gates.

## Reproduction / verification
Expected command from repository root: PYTHONPATH=v13/code python -m unittest v13.code.tests.test_audio_views -v
Actual: NOT RUN. Container cannot resolve github.com; no clone available. Connector writes confirmed, but GitHub CI and Redmi Android remain UNVERIFIED. No benchmark, A3 proof or end-to-end claim.

## Next
1. Run tests on exact PR head and fix failures.
2. Core/JEF integration: use bounded A5->B1/B2/JEF SHADOW consumer, no authority promotion.
3. Persisted Store restart and T8 source integrity; Android microphone consent bridge and full duplex remain OFF.
4. Run privacy scan and branch integration review before merging; respect source handoff freeze.
