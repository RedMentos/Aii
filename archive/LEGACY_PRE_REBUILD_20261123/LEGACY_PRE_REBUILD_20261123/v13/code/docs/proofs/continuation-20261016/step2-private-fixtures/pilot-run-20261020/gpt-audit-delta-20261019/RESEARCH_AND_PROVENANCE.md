# V13 run7 research / provenance — 2026-10-19

Source of truth: https://github.com/RedMentos/Aii/blob/codex/continuation-20261016/v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md

Newer observed integrated code HEAD (2026-10-16 20:41 UTC): `a1973d4120b4de8951faadcb6b75d3b24953184e` on `codex/continuation-20261016`. This is newer than the Library 2026-10-13 v14 isolated Action-JEPA candidate. Do not overwrite integrated runtime with that older candidate.

Read-only inspected from connected GitHub on 2026-10-19:
- `v13/code/docs/HANDOFF_CURRENT.md`: native 610/610 Linux SHADOW toolforecast independently replayed, STEP2 original UTILITY_FAIL, B3 L1 FAIL; private pilot registered but not run.
- `v13/code/docs/proofs/continuation-20261016/step2-private-fixtures/runtime_adapter.py`: row/report format, exact source hashing, six arm roles, native process release semantics and registration invariants.
- `v13/code/v13/runners.py`: RunnerPool.release_history appended on actual runner unload; the existing adapter only requires nonempty/all reaped, not one release per call. The new **offline** auditor independently checks exact per-call release order and count, without changing a registered source.
- `pilot/native-registration.json` Git blob `8d9de77e74fa4e94b21eb55342a7bc5f3157c21f`, `pilot/pilot-fixtures.json` blob `2459e6dc255a3f2e57e576eaa7515831a50f25af`: registration `REGISTERED_NOT_RUN`, fixed A/B/NONE fixture IDs, six arms, 18 rows, 42 maximum native calls, 143 registered source hashes, 3 installed model bindings. This is a metadata/structure inspection, **not** independent byte verification of 143 source files or installed model assets.

Implementation provenance: newly authored stdlib-only Python 3.13 script/tests, no external code, packages or models incorporated. Existing project file conventions and schema names were inspected, but no third-party source code was copied.

Claim limits: synthetic test suite proves local auditor behavior only; native/Redmi evidence absent; report and row hashes are unsigned self-consistency checks; the historical utility and B3 gates remain unchanged.
