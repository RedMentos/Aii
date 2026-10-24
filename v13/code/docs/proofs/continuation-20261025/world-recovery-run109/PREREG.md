# Run109 — F4 WorldState.observe/recover malformed durable outcome fail-closed (preregistered)

Date 2026-10-25 UTC. Base Run108 PR #139 `15aff0fd4224cd56cbd990063b0a18f12c6cca0a`. Owner: `v13/code/v13/world.py` observation/recovery only, `tests/test_world_recovery_invalid_run109.py`, isolated workflow and evidence folder. Run108 forecast sampling is frozen as reviewed. Run106 episodes.py and Run107 episodic_route.py untouched. No native jobs.

## Critical crash window

`Runtime.__init__` invokes `world.recover()` without a catch. Recovery calls `WorldState.observe` on committed action rows that lack a PredictionOutcome packet. Persisted SQLite action outcome/expected JSON may be malformed or contain Python-decoded NaN/Infinity. Currently a malformed JSON or nonfinite timing_error can raise before packet creation, preventing the entire Runtime from starting. An invalid row must never become a scored observation, invented timing, or learning signal.

## Test-first RED, actual SQLite Runtime

1. A completed action with `NaN` duration, `Infinity` duration, malformed outcome JSON, or nested nonfinite value does not brick Runtime restart; no PredictionOutcome packet for that invalid action.
2. A negative/boolean completed duration is refused as invalid timing, not scored or written as a valid World observation.
3. A malformed historical `expected` containing a `forecast` key does not brick restart.
4. A valid sibling action is recovered even when an invalid row precedes it; valid outcomes remain idempotent after another restart.
5. Ordinary finite 3-sample timing outcome still records its exact prediction error and self-caused/non-semantic authority flags.

Preserve RED logs and any test mistakes. No synthetic test promotes native World utility.

## Narrow correction

Strictly validate JSON shape and finite values at `observe` entry before derived packets; reject and log invalid durable rows without mutating original action bytes, creating fake observations, or aborting startup. Recovery continues over other independent actions. Preserve prior valid/failed-action semantics, typed source lineage, no autonomous training authority. `_refresh` corruption of existing PredictionOutcome packets is a separate follow-up if found.

## Primary source

Python json docs (accessed 2026-10-25): https://docs.python.org/3/library/json.html#infinite-and-nan-number-values — default parser accepts NaN/Infinity; `parse_constant` can reject them. Claim limited to standard Python parsing.

## Gates

STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; full V13 INCOMPLETE. Real SQLite/synthetic timing/Linux CI only, not Redmi.
