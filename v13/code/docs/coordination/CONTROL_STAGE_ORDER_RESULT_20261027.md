# WP-T14 canonical stage-order accounting — independent review checkpoint (2026-10-27)

**Scope:** Draft PR #767, child of #766 source-tested parent `14a08bab05e17a77508e23d1c1d25d5d142c9b89` (source blob `cee3676d67796e9335ff5c394c5ef1af8fe92099`). Prereg `35d95e2c1826859cfe72af2e14d3f6004f4ce965` precedes new test RED `114eec1ed7f616a9e92bc3e096bb4893f8d51309` and source GREEN `83f145ab47c2e56e47616b8334199db3c6b36294`. **Not main/production.**

**Change:** Runtime `mark()` writes ingress→policy→perception→memory→routing→observers→focal→output→native→finished in canonical order. Old `durations()` sorted malformed persisted timestamps by numeric value, accepting reversed known stages and misattributing control/body latency. Candidate reads known marks in `STAGES` order and excludes descending timestamps; sparse and tied ordered marks remain valid. No threshold/age/learning/model changes.

**RED Actions `40575282391` expected FAILURE:** 20 tests, 2 FAIL in reversed-stage cases, 18 others PASS. INSTALL0/UNIT1/COMPILE0/PRIVACY0/DIFF0. Raw ZIP artifact `12767705712`, SHA256 `c19111d6f7004fdfd1f9a570ba3a53a8db10b198917b0738f004e4f6cf3ec5fb`, CRC/HEAD/source blob verified.

**GREEN Actions `40575320349` SUCCESS:** 20/20 PASS, all INSTALL/UNIT/COMPILE/PRIVACY/DIFF exits0, privacy CLEAN. Source blob `b51d173aa562321f3cfb3da9bc7373733eb0d733`; raw ZIP artifact `12766617524`, SHA256 `4f6c13ac9d4386b299a5d6f1bcde0f83340870793b7cbc9cc008ed85450dae44`, CRC/HEAD verified.

**Full source-wide Actions `40575372933` SUCCESS:** source-unchanged `1cddfab18f0252fcac77dc0573c22670dc8e4264`, **1956 tests OK (1 skipped)**, all raw exits0, privacy CLEAN, raw ZIP artifact `12766178490`, SHA256 `7f5c0d921a83e8cdb883578f05af3436c21826882e8412b188bc1979cb5798fc`, CRC/HEAD/source blob verified. All original raw ZIPs privately backed up under `/V13-Checkpoints/2026-10-27/Automation11ZK-Control-Stage-Order/` and re-materialized SHA256 byte-identical.

**Limitations:** No native/Redmi/energy/thermal or real-user utility proof; no production integration. Negative LP1/LP2/BJ1/STEP2/B3, jepa_weight0, Age authority0, V13 incomplete. This does not validate every possible corrupt SQLite payload. Independent review and parent-chain reconciliation required; no auto-merge.

Next exact command: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_control_budget_stage_order_review tests.test_control_budget_created_overflow_review tests.test_control_budget_row_integrity_review tests.test_control_budget_finite_marks_review tests.test_control_checkpoint_containment_review tests.test_control_budget`. Owner assistant/GPT; next prerequisite independent frozen-runtime review of #767 stacked after #766/#765/#763.
