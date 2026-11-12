# Research/Perception handoff — 2026-11-12 12:00 CET

Owner: A4 salience; stacked on #1837. Adds deterministic bounded RMS/ZCR salience directly to A3 timed audio A5-like SHADOW result, plus unit and SQLite integration assertions. This is NOT canonical A5, neural salience learning, speaker identification, semantic risk inference, Android microphone, or permission authority.

## Evidence and caveats
- GitHub code persisted on this branch. Local equivalent Python smoke PASS; exact GitHub checkout / complete repository CI UNVERIFIED.
- Score 0.75*RMS + 0.25*ZCR is a declared heuristic, not empirically calibrated. 'pitch_hz' and 'speech_probability' in upstream strict schema remain synthetic placeholder zeros, explicitly marked unmeasured.
- A4 evidence has no Android action authority. Historical Redmi ~5.84 GB total and ~1.78 GB available are not current benchmarks.
- Tests cover deterministic bounds, invalid/nonfinite inputs and SQLite observation presence; production A5/B/C and source permission lifecycle remain open.

## Next
Core/Boss: agree canonical A5 PerceptPacket and B1/B2/C2/JEF ingestion contract. QA: execute exact-head tests, Android native authorized microphone provenance and permission revocation. JEPA: distinguish heuristic salience from supervised teacher labels; do not train on fabricated acoustic placeholders. Preserve RAW EAR nonverbal signals and full duplex voice scope. 
