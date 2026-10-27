# HX1/HX3 approval-origin binding — preregistration (2026-10-27)

Independent security/integrity review-only child of `assistant/v13-hx134-c1-world-b3-integration-20261027` at `02ebbedfc984992035c4634f05168fa3b8996b7f` (the verified HX1/HX3/HX4 candidate, not main). Owner: GPT reviewer. Only `v13/code/v13/agi/{self_improve,harness,experience}.py`, `v13/code/tests/test_harness_hx.py`, this coordination folder and a dedicated workflow may change. Other branches/owners untouched.

## Falsifiable issue

`HarnessLibrary.apply(proposal,settings)` currently accepts a caller-provided dict with `kind=harness`, `status=APPROVED`, `shield.passed=true` and a matching diff without loading the persisted AG8 proposal. `ExperienceLibrary.record` similarly trusts caller-supplied `APPROVED` + shield and an evidence file. A forged dict can therefore bypass the **stored human approval** origin gate for SHADOW harness state and HX3 experience entries. No live harness consumer currently exists; this is not a demonstrated live exploit.

## Test-first plan

1. RED tests: a forged `APPROVED` proposal with no AG8 stored record must fail closed for both HarnessLibrary.apply and ExperienceLibrary.record. A mutated copy of a genuinely approved proposal (e.g. changed shield or diff) must also be refused. No writes or entries on rejection.
2. GREEN source: bind both APIs to the exact stored AG8 proposal by ID, kind, status, shield, diff, base generation and full immutable snapshot. Use the existing store's versioned state and fail closed on missing/malformed records; no authority changes.
3. Positive regression: genuine `SelfImprovement.propose -> evaluate -> approve` remains usable; HarnessLibrary.apply/rollback and ExperienceLibrary.record/lookup/restart remain intact. Full suite and focused tests, compileall, privacy/diff checks. Preserve original RED and GREEN raw CI evidence and hashes.
4. No auto-approval, no new live consumer, no Age/learning promotion. Existing STEP2/B3/LP1/LP2/BJ1 failures and `jepa_weight=0` remain; no native/Redmi measurement.

Expected first command: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_harness_hx`. The test-only RED commit precedes any production source fix. Later CI runs must be tied to exact branch HEADs and must not be misreported as native evidence.
