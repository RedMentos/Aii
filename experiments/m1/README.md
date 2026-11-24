# M1 clean-room experiment

Status: working draft. This package is an independent copy of selected M1 experiment code; V13 and V14 are not active development dependencies.

## Data contract
- UCI minute-resolution household power data; strict continuity and finite-value validation.
- Calendar boundaries: validation starts 2008-12-01 00:00; test starts 2009-12-01 00:00.
- The gap is cut from the end of the preceding split, not inserted after the next split begins.
- Required gap: max(max_candidate_input_length, horizon, max(seasonal_lags)) + horizon. Current configured maximum is 10,140 rows.
- Test access requires exact data/config/split hashes, complete preregistration fields, an exact match to the executing commit hash, and an fsync-backed access event before unlocking.

## Copied modules
The data pipeline, NumPy array path, baselines, paired block bootstrap, and raw-window probes were copied as starting material and moved under this package namespace. Copying is not validation.

## Evidence status
No tests have been run on this branch by this session. No real UCI evaluation has been run here. Earlier reported Python 3.12 results belong to a separate local run and are not evidence for this branch.
