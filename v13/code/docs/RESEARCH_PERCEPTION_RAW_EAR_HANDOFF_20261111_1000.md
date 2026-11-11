# Research & Perception handoff — 2026-11-11 10:00 Europe/Berlin

## Scope
Added `v13/code/v13/raw_ear_contract.py` and `v13/code/tests/test_raw_ear_contract.py` as isolated, opt-in Age-0 RAW EAR acoustic input contract. Synthetic PCM16LE source SHA-256 binding, monotonic timed frame features (RMS, pitch, voiced/non-speech probability), provisional/final status, optional teacher-bound ASR. Explicitly preserves acoustic signals without forcing a transcript. Bounded 120 s, 4096 frames, supported sample rates. No speaker identification.

## Integration ownership
Core: connect only to an authenticated Android companion receipt and Store SourceRef; reject external capture unless OS grant verified. QA: native permission/lifecycle and stop-switch tests. JEPA: consume source-bound acoustic observation/outcome pairs without conflating teacher text with raw acoustic data. C3 voice effector/decoder is separate and not implemented here. A5 and B1/B2 binding not yet connected.

## Evidence and gates
Four synthetic unit tests authored; exact GitHub commit CI not yet verified. No real microphone, Android or acoustic learning benchmarks. Android microphone permission, MediaProjection, full duplex, speaker representation, speech decoder/vocoder, weight updates, A3 training/export remain OFF/UNAVAILABLE. No claim of a new native modality. Runtime activation unchanged. Android-first primary product remains mandatory.

## Next
Run `cd v13/code && python -m unittest tests.test_raw_ear_contract`; integrate source_ref to persisted A5 PerceptPacket and verify restart, then Android-native authorized capture with consent receipt and timed source provenance. Evaluate privacy constraints before real audio storage.
