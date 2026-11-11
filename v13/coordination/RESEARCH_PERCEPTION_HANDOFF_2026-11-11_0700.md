# Research Perception handoff — 2026-11-11 07:00 Europe/Berlin

## Source
Parent PR #1739 (head dd483d59); prior route PR #1736; team plan PR #1668; AGENTS.md, v13/AGENTS.md, Cognition, source_segments, existing route and regression tests reviewed.

## Defect and repair
The opt-in route called Cognition.percept (persisting a PerceptPacket) before validating width_detail/width_gist. Invalid widths then failed in source_segments *after* packet persistence. This created partial state for rejected calls.

Candidate now checks both widths (exact int, positive, <= sys.maxsize) before percept. One regression method exercises eight bad values, checking that no PerceptPacket was written. Frozen Runtime/Cognition/Store unchanged. No promotion, native inference, new modality, or gate change.

## Verification and next
GitHub connector write verified; local git ls-remote failed DNS (Could not resolve host: github.com). Exact-head unit tests, full suite, privacy scan and native Android remain UNVERIFIED; do not claim PASS. Run:
```sh
cd v13/code
PYTHONPATH=. python -B -m unittest -v tests.test_percept_runtime_route_candidate_20261111
python -m compileall -q v13/percept_runtime_route_candidate.py
```
Then independently review persistence/restart and full-source/subspan behavior, integrate with Core/JEPA contract owners. Age0 RECORD_ONLY; A3 without checkpoint UNAVAILABLE; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Android unverified.
