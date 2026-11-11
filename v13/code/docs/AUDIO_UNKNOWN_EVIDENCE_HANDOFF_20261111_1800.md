# Perception 2026-11-11 18:00 — unknown acoustic evidence

Owner: research-perception. Base: research-perception/audio-b1-prosody-20261111-1700 (PR #1787).

## Change
PCM16LE RMS-only extractor now emits `None` for unmeasured voiced and non-speech probabilities, instead of inventing measured zero. RAW EAR permits nullable probabilities, rejects invalid non-null numeric values and booleans; A5 forwards nullable measurements; B1 timed views preserve null and B2 RMS remains measured. Real measured 0.0 remains valid and distinguishable from unknown. Tests updated in test_audio_views and test_pcm_features.

## Evidence and limitations
Five source/test file updates saved on GitHub. No end-to-end Python test executed: local GitHub DNS lookup failed; no Android instrumentation, microphone permission, A3 trained projector, full-duplex voice or native performance measurements. Synthetic zero-valued PCM is NOT evidence of absence of speech. Legacy records with 0.0 cannot be retroactively disambiguated and must be treated as uncalibrated for learning.

## Integration contract
Core/JEPA: accept JSON null for optional acoustic probabilities in RAW EAR, A5 and B1. Do not train prosody, speaker, speech/non-speech or moral Judge heads on unknown fields; mask missing targets. RMS remains measured. Preserve provenance and external OS permission boundaries. Run `cd v13/code && python -m unittest discover -s tests -p 'test_*audio*.py' -v` plus `python -m unittest tests.test_pcm_features tests.test_raw_ear_contract -v` against exact commit. Integrate and verify Store restart, B/C runtime consumption, and Android native capture separately.

Age-0 gates unchanged; no desktop requirement.