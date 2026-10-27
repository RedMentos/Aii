# Run643 prereg — current review-chain Termux source ZIP (2026-10-27 UTC)

**Parent:** Run642 scoped source checkpoint `fcd53e127b8cc08ce7151e1f7de0dd367a0fe41b`, PR #639; Run641 PR #638, Run640 PR #636. **Owner:** GPT-6 Run643, only new scoped proof/workflow; no model or production source changes. The Run642 native experiment is separately owned by Actions `40437401540`; this package must not start a second native model job.

## Intervention
Use the existing audited `scripts/package_source.py --phone-install` (Git blob `06167e0bcb82b36cb08841cd31b9618c4ba0926e`) on the exact checkout to create `V13-Phone-Run643.zip`. No inference models, user database, secrets or private chat are included. Independently verify with `verify_phone_zip_current_run268.py` (Git blob `880dbd2cebb0aac5c7b37e25a5ca8487b796cfa1`) and full `WORKSPACE_FILES.json` member hashes, reject duplicate/traversal/symlink ZIP entries. Extract into an isolated directory, run package tests, explicit portable 94 live integration tests, Run641 real tiny B3 bridge-weight regression and selected operator smoke (no model). Record original raw ZIP SHA256, file count, source head and all negative gates.

## Acceptance
Package + independent source ZIP verifier + package tests + extracted 94/94 portable integration + extracted `tests.test_bodyport` and `tests.test_b3bridge` PASS; isolated NumPy 2.3.5 / prompt-toolkit 3.0.52; privacy CLEAN; ZIP CRC and all manifest hashes PASS; no private data or model bytes. Do not claim native inference, Redmi device test, complete V13, STEP2 or B3 utility from source packaging. A failure remains RED, never relabelled. Preserve raw logs, hashes and original ZIP privately and on review branch; verify remote bytes.

## Next
After verified ZIP, inspect Run642 native job separately and continue functional learning or World-JEPA integration. Keep age/approval and all canonical negative gates unchanged. No automatic production merge.
