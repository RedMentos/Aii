# Research & Perception handoff — 2026-11-11 08:00 Europe/Berlin

Parent: #1743 head 827f06942f12c467592e7eb29d294bc42082e1b8; team plan #1668; AGENTS.md. No frozen Runtime/Cognition/Store changes.

## Change
Added `v13/code/tests/test_percept_route_restart_candidate_20261111.py` to test the existing opt-in A0/A5 -> B1/B2 source-view candidate across an actual Store close/reopen. It calls real `Store`, `Cognition.percept`, and `run_percept_route`; checks exact persisted PerceptPacket payload and reconstruction of both source views after reopening. No synthetic student feature is fabricated.

## Evidence and limitations
The GitHub connector confirmed creation of the test file. Local `git ls-remote` failed DNS (Could not resolve host: github.com); therefore the test itself was NOT run, and no PASS is claimed. CI and Android hardware evidence remain UNVERIFIED. This test is a candidate until exact-head execution; it does not prove A3 projection, B inference, Android runtime, or learning.

## Next verification
```sh
cd v13/code
PYTHONPATH=. python -B -m unittest -v tests.test_percept_route_restart_candidate_20261111 tests.test_percept_runtime_route_candidate_20261111
python -m compileall -q v13/percept_runtime_route_candidate.py tests/test_percept_route_restart_candidate_20261111.py
```
Follow with privacy scan, CI and Core/JEPA contract review. Keep Age0 RECORD_ONLY, A3 unavailable without real checkpoint, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, vision/audio unavailable; Android-first remains release target, not PC.
