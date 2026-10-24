# Run108 — F4 empirical World timing rejects malformed persisted samples (preregistered)

Date: 2026-10-25 UTC. Independent base Run105 PR #137 `81f7d5f837530d38e8f2ee5c150905c9bcd8f03c`. Owner: `v13/code/v13/world.py` forecast sampling only, new `tests/test_world_timing_finite_run108.py`, isolated CI and this evidence folder. Run106 owns episodes.py; Run107 owns episodic_route.py. No shared file writes, no heavy native jobs.

## Problem

`WorldState.forecast` uses durable SQLite `actions.expected` and `actions.outcome` as if numeric timing and input length were valid. JSON parsing in Python accepts nonstandard NaN/Infinity literals by default. A negative, boolean, nonfinite or malformed sample can corrupt the median/range, cause a `dumps(allow_nan=False)` failure, or crash forecast entirely. Such rows are not measured timing evidence.

## Expected test-first RED (real Runtime/SQLite, model-free SOURCE_COPY)

- Negative, NaN, Infinity and boolean durations are excluded, never produce a supported forecast or packet containing nonfinite numbers.
- Negative, nonfinite, boolean and missing historical `input_chars` are excluded.
- Malformed JSON expected/outcome rows are skipped, not allowed to abort a valid later forecast.
- Three valid prior same-profile/same-session action durations retain the exact median, sample IDs and observed range, including after restart.
- Existing failed-action and profile/session exclusions remain intact.

Preserve original RED logs, including unexpected test defects. Commit prereg before tests.

## Narrow fix

Validate each historical sample before admission: parsed JSON objects, matching profile/role, strict finite nonnegative duration (no bool), strict finite nonnegative integer input chars (no bool), skip malformed rows without fabricating a replacement duration. Do not alter original action records, observation/learning authority, registered native cohorts, telemetry labels or Canon gates.

## Claim limits

Linux GitHub Actions real SQLite, synthetic timing fixtures only. No native timing measurement, Redmi proof, new World predictive accuracy, or gate promotion. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE.
