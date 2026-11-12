# Research & Perception handoff — 2026-11-12 05:00 Europe/Berlin

Parent #1819. Owner A3 source-backed SHADOW inference. This branch adds a real `Store` / SQLite restart test rather than another mock-only adapter.

## Added
- `v13/code/tests/test_a3_real_sqlite_restart.py`: four tests with real `Store(home)`, SQLite reopen, persisted feature source, source deletion/revocation, corrupted source blob, provisional refusal. No production Runtime construction, native sensors, teacher or Android control.
- Test command from `v13/code`: `python -m unittest discover -s tests -p 'test_a3_real_sqlite_restart.py' -v`.
- Test fixture initializes a temporary V13 data directory; does not touch user state.
- The SHA256 integrity check is from `Store.read_source`; it does not authenticate a teacher or authorize model training.

## Evidence
GitHub branch writes verified. Local `git ls-remote` failed DNS resolution for github.com; test execution and exact-head CI are NOT VERIFIED. No Android instrumentation, native Redmi RAM/latency, or quantized inference evidence.

## Remaining
A3 synthetic-only feature bridge; canonical A5 PerceptPacket, production B1/B2/C2/C3 route, real teacher/student supervision, real audio EAR and Android screen/UI permissions remain OPEN/OFF. Core/QA should review contract before operator-facing integration. Avoid altering frozen runtime or other agents' branches.

## Next
Run the exact-head test in CI, fix failures, then integrate with canonical PerceptPacket and a consented Android observation adapter. Retain source revocation checks and a separate OS capability boundary. No 22:00 digest this hour.
