# Full unfiltered suite original native ZIP prerequisite recovery — prereg 2026-10-30 run11e

Owner `assistant/v13-fullsuite-originalzip-recovery-run11e-20261030`; parent #1227 HEAD `c6ffa9dcce39260033e1c04fc05dcd73757e650d`. No source, test, scoring, model, seed or Canon changes.

Original fullsuite run `41018761078` had **3,635 tests, 3 errors, 14 skips**: two frozen Run34/Run37 `native_source_or_catalog_changed` and one `FileNotFoundError` for `tests/NATIVE_40996792157.zip`. The original native v3 ZIP was recovered from Actions `40996792157`, artifact `12951963045`, SHA256 `98a61f622b64b792f38d766da3ef50e9101571b7e616f2c587d6e89ab5e31c46`, 297,655 bytes, CRC clean, HEAD `5e802d235c9501879a3aff07e5134c1455e1769b`.

## Frozen recovery protocol before implementation
- Workflow **downloads** exact original ZIP using GitHub read-only Actions API, checks HTTP result, SHA256, CRC and HEAD before placing it in the test's already expected `v13/code/tests/NATIVE_40996792157.zip`. It must not commit that ZIP to Git, modify the test or change any historical score.
- Rerun **exact same unfiltered** 3k+ suite on isolated pinned dependencies; retain full original stdout/stderr, exit statuses, SHA256SUMS, source/Canon blobs, pip check/import, privacy and diff.
- Expected, not guaranteed: missing artifact error resolves, leaving **two frozen historical Run34/Run37 errors**. No suppression or test selection. Any new error must be investigated, not reclassified.
- No new native calls, no Redmi, no age/learning/approval/STEP2/B3/JEPA gate promotion. This is software regression with verified historical native input, not new native inference.

Next after checkpoint: independently compare post-fix JEF full suite on its own branch, and continue substantive canonical organ work.
