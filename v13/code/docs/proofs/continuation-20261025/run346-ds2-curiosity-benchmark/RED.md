# Run346 RED — DS2 new-kind measurement missing (before patch)

- Exact head `99750707144cbc63fa095299c03a360aa974959c`.
- Actions `40223066147`, job `121258626525`: **FAILURE**, 12 tests, 1 fail + 1 error. Both new cases fail only because `run()` lacks `new_kind_interactions` and `new_kind_final_kl`; existing DS1/policy semantics tests pass.
- Raw artifact `12610137447` SHA256 `186fefb03c483ed999398debb00de239219b77e59e9df3457e349a59155b93d2` independently downloaded, CRC clean, 3/3 internal hashes verified, embedded HEAD exact. Private backup `/V13/checkpoints/2026-10-25/V13_Run346_DS2_RED_raw_sha186fefb0.zip`.
- Frozen paired 20-seed evaluation intentionally did not run while telemetry was missing; no results invented, no policy changed or promoted.
- Next: minimal `sandbox.run` telemetry-only addition, rerun exact-head 12 tests and frozen paired 20-seed evaluation, report SUPPORTED_LAB_ONLY or NOT_SUPPORTED against preregistration.
