# Research/Perception handoff — 2026-11-12 11:00 CET

Owner: Perception; stacked on #1835. Scope: PCM16LE → SQLite → A3 source preflight, no native Android promotion.

## Change
- `pcm_store_observer.py`: after strict bounded PCM conversion and before `Store.source`, require callable `projector.predict` and run its read-only two-feature validation. Prevent incompatible A3 dimensions from leaving an unusable durable source record.
- `test_pcm_store_observer.py`: two regression tests verify wrong A3 input dimension and missing projector cause refusal with unchanged SQLite source count.
- Existing consent, provisional refusal, malformed PCM and revocation paths preserved.
- No external dependencies or license changes.

## Evidence
GitHub commit verified via connector. Exact-head repository CI **UNVERIFIED**; Linux git clone failed DNS resolution (`Could not resolve host: github.com`). Tests authored, not claimed PASS. Real Redmi / Android microphone / A5 canonical / B/C productive dispatch remain OFF or UNVERIFIED. No safety claim beyond local fail-before-write for these two failure cases.

## Coordination
Core should agree on canonical A5 and B/C consumer contract; QA should check Android companion source authorization and source retention; JEPA should consume only verified final outcome evidence. Current Python bridge's `consent=True` is a synthetic caller assertion, not OS permission. The preflight does not roll back source writes after a later unexpected A3 runtime error; transactional persistence and retention policy remain open.

## Next
Run exact-head CI, inspect results and fix errors. Implement canonical A5 packet and productive organ consumers, not just additional SHADOW adapters. Historical Redmi RAM ~5.84GB total / ~1.78GB available is not a current measurement.
