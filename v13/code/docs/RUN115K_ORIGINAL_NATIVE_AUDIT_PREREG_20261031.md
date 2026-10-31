# Run115K independent original Run115J native audit — preregistration (2026-10-31)

Owner: GPT-6 automation; review-only child of PR #1492, exact parent `5ad05ec4c70d75a9e872ba0b6083481a01b04394`. No production merge, model change, frozen cohort rescore or authority change.

## Frozen input before auditor implementation

Original GitHub Actions run `41220947533` at source `8b8321933a6d16c2b924283d22086f90858088bc`; original artifact ID `13049409740`, SHA256 `f09b40bf4e30c08f183a3421cbd0961951727117915d56319d6dc1879e4738de`. Registered Run115J seed997 fixture SHA256 `3cfe98d4903aaef56dd412ad426d743941fa0115b346cdf77d9abeaf2fbeb2a0`. Expected exact 6 projects Kairo/Lythos/Oxara/Perrin/Sereon/Valtor and 12 native C3 FINAL calls; 0 native B1/B2/JEF/C2. Run115I NO_GAIN and Run115C structural RED are immutable separate results.

## Independent checks (no use of native script's scorer)

The stdlib-only auditor must refuse wrong outer SHA, ZIP CRC, missing/duplicate entries, bad SHA256SUMS, nonzero stage exits, wrong HEAD, fixture hash, incomplete rows, missing native FINAL/reap, role/source leaks, oracle in prompt, missing source pointers, incorrect arm attribution, malformed or non-exact JSON, false NONE, or any output/tool/learning/age authority. Independently score six exact pairs against frozen expected choices/remaining; report raw-vs-typed and a narrow exploratory signal only. Verify the extracted phone source ZIP CRC and required Run115J fixture presence, but do not claim full device integrity without manifest parity. Tests must cover positive original artifact and negative tampered/structural synthetic cases. Preserve original evidence unchanged.

## Claim limits

Even if the typed formatter scores 6/6 and raw C3 0/6, this is a **deterministic JEF exact-source recipe copied by native C3** on six synthetic, exact-grammar tasks, NOT learned JEF/C2, independent C3 reasoning, native B1/B2 quote verification, production runtime, Redmi or STEP2/B3/Body-JEPA/whole-system success. All negative gates stay negative.

## Checkpoint and next

Private original ZIP backed up byte-identically in `/V13-Checkpoints/2026-10-31/Run115J-Native-Original-Audit/Run115J_seed997_original_shaF09B40BF.zip`. New auditor/tests are isolated in `v13/code/scripts/run115k_original_raw_audit.py` and `v13/code/tests/test_run115k_original_raw_audit.py`; run `python -m unittest tests.test_run115k_original_raw_audit -v` from `v13/code`, then audit the original artifact directly. CI remains necessary for repository-context parity.