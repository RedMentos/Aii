# Run129 first exact-head audit — correct negative result, evidence exit plumbing bug

2026-10-25 UTC. Source under test commit `24eae4eaa1aa9f0c54c2117ce41cca96ce025e53`. GitHub Actions run `40153851627`, full-suite job `121050890740`, privacy CLEAN. Pinned torch `2.9.1+cpu`, NumPy `2.3.5`, prompt-toolkit `3.0.52`, sealed Run16 LP3 helper temp-only, offline/no model downloads.

**2241 tests; 4 FAIL, 1 ERROR, 11 skips; 160.517 s.** This is a genuine RED suite, not a pass. Compared to Run126's 8 FAIL/63 ERROR, all SourceHandoff/NativeFiring cascade errors caused by frozen Runtime modification disappeared. All five remaining failures/errors are inherited LP3 Run16 helper cases:
- ERROR `test_unverified_descendant_cleanup_poison_persists_across_attempts`
- FAIL `test_default_cli_read_only_blocks_missing_assets` in three imported/reused contexts
- FAIL `test_successful_leader_with_live_descendant_is_not_success`

Raw artifact ID `12584045881` (expires 2026-11-24T02:20:24Z), ZIP wrapper SHA256 `b558bcab489ed99fe5e95cf8a92b80f7c3f37396b30446e1e764aabd1bc1be71`, 61,677 bytes. Inner `RUN129_FULL_SUITE_RAW.log` SHA256 `e4568d14a8e49802303141d853ccfc927d29c235240c3b6f52dfcd6611f98ef4`, 353,285 bytes. Independent download, CRC and failure names verified. Private Library `/V13_Run129_20261025/V13_Run129_FullSuite_Raw_Wrapper.zip` id `libfile_002510e453488191a1ad9ae17badb257` materialized and byte-compared successfully.

Workflow issue: inherited `bash -e` caused the failing pipeline to exit before `rc=${PIPESTATUS[0]}`, so `steps.suite.outputs.exit_code` was empty. The suite itself was still correctly RED, and the raw log was uploaded. Next narrowly fix shell plumbing to `set +e` around the pipeline, restore `set -e` after capturing rc, and rerun to prove explicit nonzero exit output. Do not alter source tests or negative gates. No native/Redmi/AGI claims.
