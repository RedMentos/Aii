# Research/Perception Handoff — 2026-11-12 10:00 CET

Owner: Perception. Draft stacked on #1834, not independently mergeable.

## Change
- `v13/code/v13/pcm_store_observer.py`: explicit consent argument; bounded PCM16LE → timed JSON via existing PCM bridge; persist via the **actual** `Store.source`; run `observe_timed_audio` and independent `Store.read_source` verifier. No invented store API.
- `v13/code/tests/test_pcm_store_observer.py`: four synthetic tests for real SQLite persistence/restart, source revocation, no-consent/provisional fail-closed, malformed PCM fail-before-write.
- No external dependencies beyond existing V13 and Python stdlib. No third-party license change.

## Evidence and gates
- Tests authored; exact GitHub branch CI and Android hardware UNVERIFIED. Do not mark PASS until executed.
- Output is A5-like SHADOW, not canonical PerceptPacket or real B1/B2/JEF dispatch. Android microphone/Accessibility/MediaProjection OFF.
- `consent=True` is an explicit **test fixture assertion**, NOT an Android OS permission; production source permission must be independently verified by Android companion.
- Existing PCM bridge encodes unknown pitch/speech as zero placeholders; do not treat them as measured.
- Store source persistence is deliberate. Callers must use the existing retention/consent policy; no raw microphone capture in this module.
- Synthetic A3 weight training in test changes numeric weights but does not train from microphone or teacher model.
- Historical Redmi ~5.84 GB total / ~1.78 GB available; current native measurements UNVERIFIED.

## Next
Run exact-head CI and fix failures. Integrate canonical A5 PerceptPacket + B1/B2/JEF organ contracts and source approval/revocation into authorized Android input path. Coordinate Core/QA and JEPA before promotion.
