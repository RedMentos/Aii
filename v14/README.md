# V14 — isolated rebuild

**Active implementation:** `v14/m1/`  
**Status:** [ENTWURF] — no M1 gate is claimed as passed.

## Separation and preservation

The complete pre-rebuild repository root — including the previous V14 project, V13 source, documentation, CI workflows, experiments and supporting files — is preserved as one tree-level archive under `archive/LEGACY_PRE_REBUILD_20261123/`. See `archive/ARCHIVE_MANIFEST.md` for the recovery map.

The previous full V14 master is preserved at `archive/LEGACY_PRE_REBUILD_20261123/v14/V14_MASTER_BLUEPRINT_AND_RESEARCH_20261119.md`. The unchanged historical V13 Canon is preserved at `archive/LEGACY_PRE_REBUILD_20261123/v13/blueprint/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md`.

Immutable snapshot: branch `backup/pre-v14-data-rebuild-20261123`, commit `32373358983a16560af60f4283e9ad0dc448b5a4`, original repository-root tree `5b8e8842331ed45f006fcfd8f265f5fd739bcf6a`.

This branch is an isolated V14 M1 experiment workspace. `v14/m1/` does not replace the complete V14 architecture or the old runtime. The full V14 project remains preserved in the archive until a separate, explicit integration plan is reviewed.

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
