# Run431 — WorldState recent receipt boundedness / stale materialization

Date 2026-10-26. Owner GPT. Independent F4 source-only candidate stacked on Run424 PR422 at `ce8b402dc4fad188b7143657bda6b09e103c803a`. Does not touch frozen native STEP2, model catalog, preregistered fixtures, age or learning gates.

## Observed source counterexample

Run424 `WorldState._refresh` sorts **all** PredictionOutcome rows by creation time and limits to 128 *before* rejecting corrupt/forged rows in Python. Thus 140 newer malformed rows hide an older valid observed action from `recent` while the independently computed valid count remains one. A second case: after a formerly valid last receipt becomes invalid, a future SQL-prefilter with an early `if not rows:return` would leave stale materialized state. Both violate truthful read-only own-action state.

## RED-first and proposed repair

Tests `test_world_valid_recent_window_run431.py` commit before code. The first test inserts 140 malformed newer rows after one legitimate committed receipt, restarts twice and demands count/recent/last_event agree. The second corrupts the sole persisted receipt, calls `_refresh` and demands state clear without altering raw evidence. Record the failing Actions artifact before code. Then filter to source-bound valid receipts in SQLite **before** applying the bounded recent limit, recheck every selected row in Python and materialize empty state if no valid receipts remain. Preserve SQLite CASE malformed JSON guard and all Run424 atomic ModulatorPacket/PredictionOutcome writes and recovery. Run inherited World restart tests and privacy scan. Distinguish software SQLite from Linux-native and Redmi.

## Negative gates

STEP2=UTILITY_FAIL, B3=FAIL, Body-JEPA=UNAVAILABLE, jepa_weight=0, Redmi unmeasured, whole V13 incomplete. Never promote from source-only tests.
