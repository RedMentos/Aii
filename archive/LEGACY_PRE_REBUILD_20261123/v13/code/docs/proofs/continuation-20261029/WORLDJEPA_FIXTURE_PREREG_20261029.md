# Prereg: restore World-JEPA synthetic fixture provenance after World-Model event/selection binding (2026-10-29)

Review-only child of PR #1147 exact HEAD `b3d130833f30d5ea2f68a76bffec8cdf9109a3a2`. No runtime, Canon, registered cohort, seed or model/source pin change at registration.

## Observed full-suite RED
Independent full software Actions `40955400194`: 3266 tests, 6 FAIL, 43 ERROR, 28 skipped. Of 43 errors, 27 `RUN50_INVALID_RECORD_COUNT` from `FakeReadOnlyView` returning action rows for the new selection query; 8 `sqlite3.OperationalError: no such table: events` from the old closed-store fixture; 4 missing torch, 2 inherited frozen Run34/Run37 source pins and 2 other errors. These errors are not silently waived.

## Frozen acceptance
1. The 128-row FakeReadOnlyView retains all original action ID, event ID, status, expected, outcome and created values. Canonical JSON projection SHA256 `04285e5717551ecf00ef4bd18267b7dba07a0fe34a49d428df5f1093b985cb92`.
2. The 64-row SQLite fixture retains the same original action columns/values; projection SHA256 `b3cc29df39e21415f7fc835e6eb383e78b4df5804be04c54c453bffcc1f51fca`.
3. Both fixtures supply explicit same-event, same-generation, pre-dispatch `stage=COMMIT` selections; 128/64 observed transitions are admitted by unchanged World-Model v3.
4. Existing World-JEPA array split, training/holdout, read-only, sidecar refusal, no raw ID export, and no learning/authority tests remain unchanged and pass.
5. No synthetic evidence becomes real-source proof. Do not weaken the World-Model gate to rescue fixtures.

Plan: edit only two test fixture owners, `tests/test_run50_world_jepa_action_outcome_adapter.py` and `tests/test_world_jepa_readonly_store.py`, plus new tests/workflow and evidence. No production World-Model/World-JEPA changes.
