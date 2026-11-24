# V14 M1 — forecasting experiment

**Status:** [ENTWURF]. DATA and the current baseline set have synthetic CI coverage from the pre-reset snapshot. Raw-window controls are now added on the clean branch but have not yet been executed by CI. JEPA/direct-MAE PROBE is not implemented. No real UCI result or test-year evaluation is claimed.

## Files

- `data.py`: small-fixture UCI parser, timestamp checks, chronological boundaries, strict missing-window rejection, horizon-aligned seasonal values, calendar features, deterministic fingerprints and hash-gated list test loader.
- `array_data.py`: bounded-memory NumPy `ArrayDataset`, two-pass UCI ingestion, direct float32 matrix, lazy window batches, common `InputBundle(X, S, calendar)`, batch memory ceiling and audit-first test gate.
- `baselines.py`: Persistence, Seasonal Persistence, Train Mean/Median, Ridge-AR, LAD/L1-AR and streaming MAE evaluation.
- `test_*.py`: synthetic regression tests for DATA, array ingestion and current BASE.
- `raw_probes.py`: newly added Raw-Window-Probe (linear MAE readout) and Raw-Window-MLP (one-hidden-layer nonlinear control), both using the common flattened X/S/calendar bundle and train-only fitting. Synthetic tests are present; exact CI has not yet run on this branch.
- **Still missing:** experiment runner/statistics, direct-MAE, JEPA encoder/predictor, random-encoder probe, collapse metrics and M1b/M1c.

## Real-data path

Use `ArrayDataset.from_uci(path, config)` for the full cohort. The list parser is for small fixtures/reference checks only. The source is not downloaded by this package; the actual run must use a locally supplied extracted UCI file and record the parsed-data fingerprint.

## Safety of evaluation

Do not materialize test windows before preregistration. The test gate must verify exact preregistration/config/split/data hashes and persist+fsync the access event before unlocking. A hash is a tamper-evident identifier, not an authorization system by itself.

See [the active V14 workplan](../WORKPLAN.md) for the complete experiment constraints and execution order.
