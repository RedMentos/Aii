# V13 Run11 organ rollback integration — first combined CI RED prerequisite (2026-10-28)

Review-only PR #920, prereg `5fc338d3bca1943da562a83b8e55e61c64004302`. Exact source `17a1a4d24b9a565531e331ee393210e3a8cae5ff` ported donor `organ.py` and four test files byte-identical from verified PR #440.

Original Actions `40688965960`: **focused 31/31 PASS**, full `unittest discover` **2375 collected, 4 import ERROR, 28 skipped**. All four errors are `ModuleNotFoundError: No module named 'torch'` in existing `test_body_jepa_checkpoint`, `test_body_jepa_checkpoint_fit`, `test_lp3_shift_row_control_20261028`, `test_lp3_state_prefix`. No organ regression failure was reported. This is **CI dependency RED**, not full-suite PASS or evidence of failed organ functionality. Compile/privacy/diff stages skipped on first run and cannot be claimed green.

Original artifact `12815714689` ZIP SHA256 `4d7f3dace48a8f9174d3f6c8c63db3cbe3582898ca7c624f6e7ed46fe2b847eb`, CRC clean; `focused.exit=0`, `full.exit=1`. Private Library backup `/V13-Checkpoints/2026-10-28/Run11-Handoff/ORGAN_FULL_MISSING_TORCH_40688965960_sha4D7F3DAC.zip` re-materialized and byte-compared identical.

Corrective change only adds pinned isolated CPU `torch==2.14.1` from the same PyTorch index already used by `.github/workflows/automation11-step2-staged12-software-20261028.yml`, plus conservative runtime env. Source and test blobs unchanged. Rerun focused, full, compile, privacy and diff on new exact head. Preserve first RED. No native or Redmi claim; all negative gates unchanged.
