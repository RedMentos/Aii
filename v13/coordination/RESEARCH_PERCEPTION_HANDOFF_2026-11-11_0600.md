# Research Perception handoff — 2026-11-11 06:00 Europe/Berlin

## Verified source review
Base PR #1736 head bc50253a75fd43225a4e61085641827cc41aed8a; team plan PR #1668. Read AGENTS.md and v13/AGENTS.md, route candidate, source_segments, Cognition and Store interfaces.

## Concrete defects
1. The route candidate contained literal backslash-n sequences inside a Python comment/if block. This produces invalid Python syntax; the prior candidate cannot be imported as written.
2. The prior test expected successful nonzero-span processing even though the documented A5 guard intentionally rejects nonzero spans before persistence. That test could not pass against the specified safety contract.

## Repair
- Replaced escaped newlines with valid Python statements and explicit fail-closed nonzero span guard.
- Replaced contradictory nonzero-span success test with rejection/no-packet assertion.
- Added a zero-start shortened-span source-exact regression.
- No changes to frozen Cognition/Runtime, no native model or new modality; A3 remains UNAVAILABLE without checkpoint.

## Evidence and limitations
GitHub content writes succeeded. Container git clone failed with DNS error `Could not resolve host: github.com`; therefore exact-head import, unittest, full suite, privacy scan, and Android verification were NOT executed. No PASS is claimed. Next runner should execute:
```
cd v13/code
PYTHONPATH=. python -B -m unittest -v tests.test_percept_runtime_route_candidate_20261111
python -m compileall -q v13/percept_runtime_route_candidate.py
```
Then test actual Store/Cognition persistence and compare immutable source after restart. Verify no other A5 subspan bypass, request cross-owner review before touching frozen runtime. Keep Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION.
