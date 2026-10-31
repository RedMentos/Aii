# JEF full-suite exact-original native artifact prerequisite resolution prereg (2026-10-31)

Owner GPT-6 scheduled continuation. Review-only child of full unfiltered RED PR #1423 exact `1edd8b3b19997f9d5de3a2f5e0420ef3e4ab40d2`. Commit and remote-read-back before workflow. No production source/test/Canon/model/cohort changes; CI-only read-only original artifacts.

## Observed fresh-scratch blockers

PR #1423 original full suite Actions 41175500095 ran 4616 tests, 4 failures, 66 errors, 28 skipped, raw ZIP SHA256 `aee143795316319f9945a52d8892bbbb5b0d2ca0432cc1e34751e5ab7e6cf3ae`. One `test_run13x_original_native_receipt_replay` setup requires original `RUN13X_ORIGINAL_ZIP` and another `test_step2_expression_diagnostic_20261030` requires `tests/NATIVE_40996792157.zip`. Both are exact original public Actions artifacts, not fabricated fixtures:

- Run13T original Actions **41097658020**, artifact **12996917793**, SHA256 **`86f728599312518bfa67efa0ae16e66be0eaec9ccfd8c3da8710fba40192717c`**, original HEAD `d9d0b312168000283e84109ec3e7951304e6520b`, ZIP CRC PASS, 39/39 inner hashes, 16 original native rows.
- STEP2 original Actions **40996792157**, artifact **12951963045**, SHA256 **`98a61f622b64b792f38d766da3ef50e9101571b7e616f2c587d6e89ab5e31c46`**, original HEAD `5e802d235c9501879a3aff07e5134c1455e1769b`, ZIP CRC PASS, 53/53 inner hashes.

Both were independently downloaded and verified locally **before** this prereg. GitHub Actions workflow will fetch them read-only using `actions: read`, verify exact bytes/inner hashes/HEAD, stage Run13T as `RUN13X_ORIGINAL_ZIP` and STEP2 as the exact original `v13/code/tests/NATIVE_40996792157.zip` **only in ephemeral runner worktree**, then run the same unfiltered full suite with same pinned Python3.12/NumPy2.2.6/torch2.5.1+cpu/transformers4.44.2/peft0.13.2 as PR #1423. Original source/tests and their hashes remain unchanged; no native rerun.

**Acceptance:** both original ZIPs verified, all prerequisite/dependency/pin/compile/privacy stages zero, full unfiltered test identities compared against PR #1423 RED and parent baseline PR #1425 when terminal. Remaining historical failures must remain RED and unwaived. Preserve raw and private byte-verified backup. No STEP2, B3, Body-JEPA, JEPA, Redmi, Age or whole-system promotion. Serialize heavy full suite with current owner group `v13-native-c3-ag12-20261030` and never cancel an active owner.
