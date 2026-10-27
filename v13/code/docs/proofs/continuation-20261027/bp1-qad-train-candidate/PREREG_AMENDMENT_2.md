# BP1 QAD train-only corpus hash diagnosis correction — amendment 2 (2026-10-27)

**This corrects the transposition in PREREG_AMENDMENT_1.md; retain amendment 1 as the failed diagnostic record, do not silently rewrite it.**

Independent byte-level read of the original immutable PR #677 artifact `12715684803` (`bp1-output/MANIFEST.json`, ZIP SHA256 `12a66c12019ee267cac12defd0b281f34fbcac5dc1f2e941236ae4ebf9a5f56c`) shows the original source-corpus SHA256 is **64 characters**:
`1872a3adf6e51e05e604053539d50ae05c955b221f78f1951d1f68e2a12f926c`.

The newly written candidate script **and its synthetic test fixture** mistakenly used this **60-character** non-SHA:
`1872a3adf6e51e05e604053539d50ae05c955b221f78f0cce39c0703f8cf`.

That explains native Actions 40475705217 TRAIN exit1 before optimizer. The original manifest and data are correct and remain immutable. The test fixture and candidate's expected literal must be corrected to the 64-character original, with prospective software RED before source fix and independent GREEN afterward. No changes to original data, model, LoRA config, seed, age or negative gates.