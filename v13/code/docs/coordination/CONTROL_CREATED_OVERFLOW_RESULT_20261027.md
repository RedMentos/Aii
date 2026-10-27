# WP-T14 persisted created timestamp overflow — independent review checkpoint (2026-10-27)

**Scope:** Review-only draft PR #766, child of #765 exact parent `bc7c5b5d7805b150e4becbafe8816f6ac474b5b2`, not main or production. Prereg `37cf0dc586adca72042543a5b1b22324bf089656` precedes test-only RED `b344710252651e0bd0aa5cdd91c44814bc3b7be9` and source GREEN `63c223af6f0aa37565f3fc25a3f27daef8ed018f`. Source blob `416926df68697ddc802300083b6ee2d4682ee1cb` -> `cee3676d67796e9335ff5c394c5ef1af8fe92099`.

**Change:** `latency()` now excludes a persisted assistant `created` value when numeric finite validation raises OverflowError/ValueError/TypeError. An oversized Python integer `10**1000` formerly crashed `:fabric report`; valid int/float timestamps and existing mark/denominator semantics remain unchanged. This is software robustness only, not a claim that SQLite normally stores such an integer.

**RED:** Actions `40574739148` at `b344710252651e0bd0aa5cdd91c44814bc3b7be9`, expected FAILURE: 17 tests, 2 ERROR in new oversized timestamp cases, 15 others PASS. Raw exits INSTALL0/UNIT1/COMPILE0/PRIVACY0/DIFF0. Original ZIP artifact `12766427133`, SHA256 `8fbcf0b7cc22d10a6b720da3496510bdcd7cdcfed6cf8273217012ebb7fbb344`; CRC/HEAD/source blob checked.

**GREEN:** Actions `40574912676` at `63c223af6f0aa37565f3fc25a3f27daef8ed018f`: 17/17 PASS, all INSTALL/UNIT/COMPILE/PRIVACY/DIFF exits0, privacy CLEAN. Original ZIP `12767575714`, SHA256 `743e8a2fbe72a6cd477a852c606a00ef00bcc2f8fce2bc891b8ddf310930d9e7`; CRC/HEAD/source blob checked.

**Full source-wide:** Actions `40575052640` at `14a08bab05e17a77508e23d1c1d25d5d142c9b89`, source blob unchanged `cee3676d67796e9335ff5c394c5ef1af8fe92099`: **1953 tests OK (1 skipped)**, INSTALL/UNIT/COMPILE/PRIVACY/DIFF all exits0, privacy CLEAN. Original ZIP `12767094016`, SHA256 `e035623f544941d0a110fa9d58559ce2c6e372805cd5b89fafbb951014206cf8`; CRC/HEAD/source blob checked.

All three original raw ZIPs were privately uploaded to `/V13-Checkpoints/2026-10-27/Automation11ZJ-Control-Created-Overflow/` and re-materialized byte-identical SHA256. No private data committed to public GitHub.

**Limits/next:** No Redmi, native, thermal/energy, real-user utility or production integration; no changed model/seed/cohort, no automatic merge. LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, STEP2 UTILITY_FAIL, B3 L1 FAIL, jepa_weight0, Age authority0, V13 incomplete. Independent review of PR #766 stacked after #765 required. A separate child PR #767 now owns canonical stage-order evidence; do not overwrite its branch.

Next exact command: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_control_budget_created_overflow_review tests.test_control_budget_row_integrity_review tests.test_control_budget_finite_marks_review tests.test_control_checkpoint_containment_review tests.test_control_budget`. Next prerequisite: independent owner review, then integrate the whole stacked chain only after parent review; original gates unchanged.
