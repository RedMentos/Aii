# M1 clean-room experiment

Status: working draft. This package is an independent copy of selected M1 experiment code; V13 and V14 are not active development dependencies.

## Data contract
- UCI minute-resolution household power data; strict continuity and finite-value validation.
- Calendar boundaries: validation starts 2008-12-01 00:00; test starts 2009-12-01 00:00.
- The gap is cut from the end of the preceding split, not inserted after the next split begins.
- Required gap: max(max_candidate_input_length, horizon, max(seasonal_lags)) + horizon. Current configured maximum is 10,140 rows.
- Test access requires exact data/config/split hashes, complete preregistration fields, an exact match to the executing commit hash, and an fsync-backed access event before unlocking.

## Modules
- data.py / array_data.py: reference and bounded-memory NumPy data paths. ArrayDataset exposes train rows through train_values(); the full matrix is private internal state. The in-process gate is a methodological API guard, not a security sandbox against code deliberately accessing private attributes.
- baselines.py: persistence, seasonal persistence, train mean/median, Ridge-AR and LAD-AR.
- raw_probes.py: linear raw-window and nonlinear raw-window MLP controls.
- bootstrap.py: paired temporal-block bootstrap with block-sum/count weighting, including partial blocks.
- metrics.py: common prefix-horizon and primary MAE metrics, per-window errors, paired multi-model/seed validation and atomic result persistence.
- jepa.py / gru.py / training.py: EMA JEPA, Direct-MAE, frozen-context linear probe, Raw-GRU, train-only channel scaling, streaming collapse telemetry and atomic checkpoints.

## Verification status
GitHub Actions run 45316419035 passed 55 tests on Python 3.12, 3.13 and 3.14 at commit 5760ca1f2a0853357affc00c1e66a3cc5cf6911e. This is synthetic CI evidence only. No real UCI evaluation or test-year access is claimed.

## Next gates
1. Review all baseline and raw-probe semantics against the experiment protocol.
2. Implement direct-MAE and JEPA representation training with identical data, seeds, train/validation policy and probe capacity.
3. Add random-encoder, Raw-GRU and collapse/effective-rank controls.
4. Benchmark actual UCI ingestion and bounded batch throughput.
5. Lock preregistration and commit binding before any test access.
