# Run49 preregistration — C5/C6 DRAFT source-bound SHADOW (2026-10-31 UTC)

Owner: GPT-6 scheduled continuation. Review-only child of Run48 #1375 at exact `a3440e441011f630ec0cf1d1ba23a08dad3bd661`. Frozen fixture committed first at `fdd0cfdd3fe75cfd4597957bf25bbcd9b8f010fc`; Git blob `94e95f0b797dd0613a8838f989872beff0cc5ebf`, SHA256 `dd7f99895ebb3c425cfa86d9c3dfc18fde0e55a5303ed226aed4c4b9644c02ee`. Three disjoint projects Cedar, Quartz, Moss, seed431. Prior Run44 native RED, Run47 native receiver 6/6 copy, Run48 software agreement and their source/fixture/model hashes remain unchanged.

## Hypothesis and exact scope

The existing real SQLite C5 TEXT_REPORT ActionIntent/CorollaryCopy and a C6 pre-visible DRAFT message can be checked against the exact current USER event/session, two full current SourceRefs, and Run48 C3/JEF agreement without changing any persistent state or granting output authority. Candidate is **isolated/default-off**; no Runtime, ToolStep, output-commit or model integration. It does not call native models. All tests use actual Store/SQLite with synthetic strict C3 JSON strings, not native model answers. No user-approved delivery or tool execution.

The proposed `check_draft` returns only digest/status metadata. It must reject invalid ids, wrong session/event, wrong role, non-DRAFT/committed/final messages, changed text, missing/foreign C5 ActionIntent or CorollaryCopy, wrong generation/owner/permission, revoked/mutated source, wrong C3 choice, and stale/missing action. It must verify the final state within a single SQLite transaction and preserve zero persistent changes. No external effect is attempted inside or after that transaction. Tests also cover restart and source revocation.

## Acceptance

1. Fixture Git blob and SHA256 match above before tests.
2. All new real Store tests and prior Run48/Run46B tests pass; independent adversarial tests include wrong event, foreign action, wrong role/status, wrong C3, revoked source, corrupted packet and restart.
3. `py_compile`, `git diff --check`, public repo privacy scan and frozen source/hash checks pass. Raw logs and per-file SHA256 manifest retained even on CI failure.
4. Result remains `SHADOW_NO_AUTHORITY` with zero Store writes, model calls, tool dispatch, age promotion, STEP2/B3/Body-JEPA/World-JEPA promotion.
5. This is **not** proof of atomic live delivery: a later output effect would need an explicit authorization design and a transactional commit integrated into the actual C6 egress; no external side effect may be inferred from a read-only preflight.

Original failures remain preserved; do not alter the prereg or seed after code is written. Negative gates: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; World-JEPA SHADOW; Redmi unmeasured; whole V13 incomplete.
