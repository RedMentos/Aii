# WP-T14 checkpoint accounting containment — software checkpoint (2026-10-27)

## Scope and lineage
- Review-only PR #765, child of PR #763 exact parent `54e6d42e483cd1a15eec6e00e27a7672632db574`; not main or production.
- Prereg `3a2627c3dd585e519c579e22db55c7b4d62919a0` before source/tests.
- Original `control_budget.py` blob `f2beff6b2b3df4c1a98a4763e6ec93e17a8dabfa`; fixed source commit `e9d0b087be97a1eb4ef7ece214ff0cb70869777d`, blob `416926df68697ddc802300083b6ee2d4682ee1cb`.
- Original budget limits, persisted-row integrity, finite stage marks and Age rights untouched.

## RED/GREEN evidence
The old `checkpoints()` counted external absolute paths, `../` traversal, symlinked external files and duplicate aliases as control checkpoint bytes. It also returned external paths in the report. The new candidate strictly confines canonical regular files to `home/checkpoints`, rejects symlinked components, deduplicates by canonical path, reports relative names only, and never opens file contents.

**RED Actions 40568617342 expected FAILURE** at `fc4dad6f05cb2c61c1601b81127a0d211f578c47`: 14 tests, 3 FAIL, INSTALL/COMPILE/PRIVACY/DIFF exits0, raw ZIP artifact `12763886975`, SHA256 `4f35cdc2247faa85aa6cc6a939cc39704570ef07d59b47074642955d228ee24e`.

**GREEN Actions 40568672861 SUCCESS** at `e9d0b087be97a1eb4ef7ece214ff0cb70869777d`: 14/14 PASS, all INSTALL/UNIT/COMPILE/PRIVACY/DIFF exits0, privacy CLEAN, raw ZIP artifact `12763274096`, SHA256 `a7e2f4ba3882943da8db5ac20f4d699392a1115405bc61f7708c69468950568d`. Original ZIPs CRC/HEAD checked, privately backed up under `/V13-Checkpoints/2026-10-27/Automation11ZI-Control-Checkpoint-Containment/` and re-materialized SHA256 byte-identical.

Full source-wide Actions **40568704310 PENDING** at source-unchanged `d4b5b9dec06e59d9141fea38f5500fc5f53fbf13`; not claimed complete until closed raw exits.

## Limits and next action
This is **accounting containment only**, not approval/cryptographic SHA verification of referenced artifacts. `Store.generation()` verifies its manifest integrity separately; actual referenced checkpoint-byte hashes remain an independent question for the generation owner. Avoid expensive unapproved hashing on Redmi until budgeted and specified.

Next exact command: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_control_checkpoint_containment_review tests.test_control_budget_row_integrity_review tests.test_control_budget_finite_marks_review tests.test_control_budget`. Independent review required before integrating stacked PR #765 after #763. No native/Redmi/thermal/energy proof, no model/seed/cohort changes, no auto-merge. LP1/LP2/BJ1/STEP2/B3 negative, jepa_weight0, Age authority0, V13 incomplete.
