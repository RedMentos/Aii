# Run96 prereg — bounded installation selftest instead of unfiltered developer suite (2026-10-31)

Owner GPT-6 Auto11, review-only child of Run95 source chain exact parent `cca4a8ad562c9e80bdbf3f085d0c3926bbf4f2c8`. Do not edit frozen Runtime/Store/Canon/model/seed/cohort, original source/proof, or `v13/__main__.py` default full selftest.

## Observed source risk (not yet an execution result)
Current `setup.sh` blob `e7302f9e2ce74b6c98bea4df604552993ca44340` installs only numpy and prompt-toolkit explicitly, then calls `$V13_DATA_HOME/bin/v13 selftest`. Current `v13/__main__.py` blob `9248e46e199a4227c296d538e6a2ef969e8e10cb` implements `selftest` as unfiltered `unittest.discover('tests','test_*.py')` (roughly 4907 tests, 28 skips in recent fully provisioned Linux CI). This is an unbounded developer suite during first Termux install, potentially long/unsupported and missing optional Torch/Transformers dependencies. It is **not yet proven** to fail on Redmi; no phone evidence. Current `package_source.py` blob `06167e0bcb82b36cb08841cd31b9618c4ba0926e` unchanged.

## Plan
1. Reproduce the existing installer selftest behavior on Linux in a fresh isolated venv with only the explicit setup Python deps (numpy, prompt-toolkit), no models/downloads. Preserve raw and timeout as RED evidence. No native calls.
2. Add a separate bounded model-free `scripts/install_selftest.py` that runs a fixed allowlist of core Runtime/Store/queue/age/source-handoff tests, reports actual tests/failures/skips, fails closed on empty/import errors, no downloads or model inference, and exits nonzero on failure. `setup.sh` calls it after bootstrap instead of the unfiltered `v13 selftest`; the full `v13 selftest` command remains unchanged and available to developers.
3. Test install smoke with exact minimal dependencies and fresh HOME, missing-dependency negative control, no native launch, no source/model/gate changes; shell syntax, full-source software regression and privacy scan. No default auto-start change.
4. After Run95 source ZIP baseline GREEN, package a **new** Run96 phone ZIP with bounded installer, verify manifest/CRC/hashes/extracted tests. Do not overwrite Run95 original artifact or promote Redmi evidence.

## Gates
Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight0; Redmi UNMEASURED; whole V13 INCOMPLETE. No paid provisioning. If baseline does not demonstrate the suspected issue, review before any code change. Keep failed attempts.
