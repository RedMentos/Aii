# V14 — isolated rebuild

**Active implementation:** `v14/m1/`  
**Status:** [ENTWURF] — no M1 gate is claimed as passed.

## Separation and preservation

The previous V14 tree was moved intact to `archive/V14_PRE_REBUILD_20261123/`. It is preserved as source material and is not the active implementation path. V13 remains unchanged on this branch. This rebuild has its own branch: `v14/rebuild-isolated-20261123`.

The pre-rebuild Git snapshot is also preserved on `backup/pre-v14-data-rebuild-20261123`.

## Current implementation

- `m1/data.py`: reference DATA parser, chronological split/window builder, manifest and hash-gated test access.
- `m1/array_data.py`: bounded-memory NumPy ingestion and lazy window batches with a common X/S/calendar input bundle.
- `m1/test_data.py`, `m1/test_array_data.py`: synthetic logic tests; not yet a real UCI run.
- `m1/README.md`: detailed protocol, baselines, input parity and M1 gate requirements.

## Next sequence

1. Run and fix all synthetic DATA tests on Python 3.13 and 3.14.
2. Audit split/lag/hash semantics against the M1 protocol and commit a reproducible DATA acceptance report.
3. Implement BASE model adapters on the common `InputBundle`.
4. Implement PROBE models and matched-capacity JEPA/direct-MAE controls.
5. Only then preregister M1a and run the real UCI data pipeline.

No code in this directory is described as implemented-and-validated until code, real state/data path, persistence, tests, telemetry and ablation evidence exist.
