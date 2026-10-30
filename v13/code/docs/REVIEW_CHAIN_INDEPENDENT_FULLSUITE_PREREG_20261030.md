# V13 independent review-chain CI closure and full-suite prereg — 2026-10-30

Owner: `codex/v13-review-chain-audit-fullsuite-20261030-hourly11b`, immutable parent `373d50e92c698163aa4ac773f46f27ec13379e85` (PR #1210 review branch). This branch is review-only, never a merge to main or an edit to another owner's branch. No changes to original v3/native source, model/seed/fixture/scorer or negative gates.

## Original CI independent audit (performed before this prereg)

Actions run **41000353507** tested exact HEAD `ee911ce61a9bb5e867cbaf7674468cc85a0be72d`, conclusion SUCCESS. Downloaded original artifact ID **12953575978**, **6841 bytes**, GitHub and independent SHA256 **ceeea010461cd437d5c4ce81591898e0968df60992c8484528d54a34f48ed71b**. ZIP CRC clean, 23/23 inner SHA256SUMS verified, 10/10 recorded stage exits 0, privacy CLEAN, original v3 ZIP SHA-check exit 0, posthoc report says NO_PROMOTION. Private Library backup `/V13-Checkpoints/2026-10-30/Run11-ReviewChain-Independent/CI_41000353507.zip` was re-materialized and byte-compared identical.

**Discovered evidence discrepancy:** the source checkpoint and scoped BUILD_STATE predicted **37** focused tests, but the original `TEST_RAW.log` unambiguously reports **Ran 31 tests in 0.113s / OK**. This is a documentation/test-count expectation mismatch, **not a failed test**. The existing workflow checks only process exit and does not assert expected test count. Do not claim 37/37. Independent 31/31 passed. Preserve the original CI artifact unchanged.

## Preregistered next checks (before workflow/source)

1. Launch new *separate* Ubuntu software-only full unfiltered suite from this exact review-chain parent with pinned torch 2.5.1+cpu, transformers 4.44.2, peft 0.13.2, numpy 2.2.6 and existing utility dependencies. Preserve every test error and raw output; no `--ignore` or skipped file pattern. Historical Run34/Run37 source-pin errors are expected to remain RED but must not be silently waived.
2. Independently rerun the four focused modules and enforce **exactly 31** discovered tests and zero failures/errors. If new branch source adds or removes tests, fail closed and report the difference, not auto-update the expectation.
3. Verify Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`, model catalog and control tool pins, compile, privacy scan and git diff check. Archive stage exit codes, exact SHA256SUMS and logs on both success and failure.
4. Independent review must verify the original raw and this new run's raw before any claim. GitHub Actions success alone is not proof of the original raw integrity. A full suite failure does not promote a gate and is not reason to stop work on independent organs.

Gates remain: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, no Redmi evidence, canonical_architecture_complete=false, user_full_scope_complete=false.

Next command after workflow: inspect new Actions run and original artifact; verify ZIP SHA/CRC/SHA256SUMS/stage exits, record exact full-suite failures and count; private byte-identical backup; then proceed to disjoint controlled native utility or independent Canon organ. No paid resources or device actions.
