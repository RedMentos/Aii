# Research/Perception handoff — 2026-11-12 13:00 CET

Owner: A5 candidate boundary for existing RAW EAR → SQLite → A3 → A4 synthetic route. Base: research-perception/a4-acoustic-salience-20261112-1200 (#1839).

New: `v13.a5_audio_envelope.from_timed_a3` strictly converts existing SHADOW audio result into an observation-only candidate with source hashes, time, acoustic features, A3 embedding, A4 score and explicit unmeasured pitch/speech/speaker. No invented transcript, no Android action rights, no promotion to canonical A5. Tests cover preservation, nonfinite/hash, action/provisional, fabricated transcript.

Important: Candidate is NOT canonical A5, NOT wired to production B1/B2/C2/JEF, NOT Android microphone, NOT learned speech or full-duplex. GitHub code existence alone is not a test PASS. Exact-head CI and Android aarch64 remain UNVERIFIED. Historical Redmi RAM figures are not fresh measurements.

Next: Boss/Core agree canonical A5 schema and B/C ingestion; Perception integrates via actual Runtime without modifying foreign owners; QA runs exact branch tests and permitted Android microphone instrumentation. Maintain provenance and revoke semantics across downstream memory. No new external dependency or model license.
