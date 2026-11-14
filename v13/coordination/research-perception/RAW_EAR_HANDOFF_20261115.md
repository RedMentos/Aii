# RAW EAR A-plane contract handoff (2026-11-15)

Scope: additive pure-Python packet and synthetic acoustic fixture; no runtime capture, ASR or native inference activation. Explicit source ID, timestamp range, consent scope, provisional/final, provenance, RMS/peak/ZCR and optional teacher revision. Non-speech evidence is retained even with no transcript.

Issue #1904 remains P0: the audio contract does not repair C3 prefill or B1/B2 timeouts. Integration requirement: Core must add a source-bound A5 adapter to actual PerceptPacket and B/C contracts without expanding native prompt tokens unboundedly; QA must verify Android capture consent and no raw PCM persistence. JEPA may consume only opt-in source-bound outcomes.

Offline command from v13/code: `python -m unittest discover -s tests -p 'test_audio_raw_ear_contract.py' -v`.
Tests committed but **NOT EXECUTED in this run**: GitHub connector writes succeeded, local environment could not resolve github.com for checkout. CI and Redmi are UNVERIFIED. This is a draft for independent review, not a release.

Low risk: dataclass, strict validation, synthetic fixture. High risk / NOT implemented: microphone lifecycle, teacher weights, streaming timing synchronization, speaker identity, A3 projector, full-duplex and voice effector, real Android consent, live runtime wiring. Keep official Age0 and GATES unchanged. No private data or weight changes.
