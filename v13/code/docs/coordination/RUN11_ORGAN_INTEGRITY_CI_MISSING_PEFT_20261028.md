# Run11 organ checkpoint integration — second CI prerequisite RED (2026-10-28)

Source-only PR #920 `2611a4b5b0c50158d2130b7a0b1cfc9f4e9036e1`, Actions `40689839187`: **31/31 focused PASS**, full `2385` tests with **4 import ERROR, 11 skipped**. Missing modules: `peft` in `test_body_jepa.MinorSubspaceTests.test_wide_and_tall`, and `transformers` in `test_body_jepa_checkpoint_fit`, `test_lp3_shift_row_control_20261028`, `test_lp3_state_prefix`. Original run is **RED for isolated CI prerequisites**, not a full-suite PASS and not an organ logic failure. Compile/privacy/diff skipped, not green.

Original raw artifact `12816483337`, ZIP SHA256 `88c83811b844f8dc33e531a61f79e9a5c623a790669685f54a8f01b5d1f6b383`; CRC CLEAN, HEAD matches, focused.exit=0, full.exit=1. Private Library backup `/V13-Checkpoints/2026-10-28/Run11-Handoff/ORGAN_FULL_MISSING_PEFT_40689839187_sha88C83811.zip`. First RED `40688965960` (missing torch) separately retained.

Third source-only CI run adds pinned `transformers==5.20.2`, `peft==0.21.2`, and the canonical lightweight dependencies from existing staged12 software workflow. Exact `organ.py` donor and four tests unchanged. No native/Redmi/gate promotion; preserve RED attempts.
