# WP-Z12d local read-only CLI nonfinite report fail-closed prereg (2026-10-27)

Within existing review-only PR #758 branch `assistant/v13-world-jepa-local-store-20261027`, exact prior remotely saved head `e6588cca05129d809b5d89b0b40fe54111dcd57e`. This prereg is committed **before** new RED tests and GREEN source. Owner remains `scripts/world_jepa_readonly_store.py` and `tests/test_world_jepa_readonly_store.py`; no parent bridge/runtime modifications.

Static defect: `main` catches malformed-store errors around `run_db` but serializes the returned metrics with `json.dumps(..., allow_nan=False)` **outside** the guarded block. Nonfinite/unsupported metrics can raise `ValueError`/`TypeError` and produce an unhandled traceback rather than the promised sanitized `UNAVAILABLE` JSON with exit2. This is a local reporting boundary, not a change to model evidence.

RED: mock `run_db` to return `{'metric': float('nan')}` and `{'metric': object()}`; require a sanitized status and exit2, no raw data echo. Original code expected to raise; preserve raw. GREEN: move strict JSON serialization into the existing guarded block; keep `allow_nan=False`, never coerce nonfinite values to zero or change model metrics, DB read-only behavior, registered seeds/steps or gates. Run focused SQLite tests, compile/privacy/diff with closed raw evidence.

No actual private store or Redmi run, no live hook or Age/JEPA-weight/utility promotion. Prior #754 synthetic JEPA readout still worse than ridge. LP1/LP2/BJ1/STEP2/B3 negative gates, jepa_weight0, Age authority0, V13 incomplete.
