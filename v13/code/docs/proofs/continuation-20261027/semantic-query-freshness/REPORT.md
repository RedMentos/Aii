# WP-N8 / STEP3 semantic query freshness — review checkpoint

Date 2026-10-27 UTC. Owner GPT-6 continuation. **Review-only** child of PR #741, exact original parent `fe57536308819b6facc5947d24fcff66468ab34e`; PR #742. Preregistration `84fce9a19920aadc0fa3613a0ff3b03161e9cce7` preceded RED tests and runtime changes. Canon, model files, registered cohorts and hashes unchanged.

## Defect / patch

The query vector cached in `SemanticKeys.last_query` was keyed only by a digest of query text, not by turn. A later identical query with embedding disabled, `top_k=0`, or encoder failure could leave the previous vector available to `episodes.observe_turn`, creating an unearned semantic boundary signal. Synthetic regression reproduced stale-vector consumption.

`Memory.recall` now invalidates the snapshot before all exits, including zero-top-k and no-pool; direct `SemanticKeys.similarities` clears at entry and publishes only after complete successful computation. Successful same-turn reuse remains; source values, thresholds, cache integrity and Age authority are unchanged. Scope is memory/episode freshness only; it is not a new semantic-learning utility proof.

## Exact RED / GREEN

- Initial test-only RED source `9201bb9a30fb0ceba22b62f582bf5cbaa66c508c`, Actions `40538336718`: 27 tests, 2 expected FAIL plus 1 fixture teardown ERROR. This attempt is retained, not silently discarded. Raw ZIP `12749537041`, SHA256 `8845a2d1fa622768480b4b9d3b5701075daa7265a4cd2cb69da248ed1babcf94`.
- Corrected fixture-only RED `7f91dd1065b59521b949a3169d3ecd7356799304`, Actions `40538480865`: 27 tests, **2 expected FAIL, 0 ERROR**, INSTALL/COMPILE/PRIVACY/DIFF exits 0; UNIT exit 1. Raw artifact `12749915629`, ZIP SHA256 `0566c897991087096be8ddde6ac33fa496ab6683e13145672be29e58c010d515`, CRC clean, source blobs unchanged from parent.
- GREEN exact runtime source `1281f8c13e0283db463291a7ed7e584b07a45621`, Actions `40538755066`: **27/27 PASS**, all five exits 0. Artifact `12748529749`, ZIP SHA256 `30eab2255b0a0c306dfd16948284c134a26c6b66f08d59b2eee73404d8492755`, CRC clean; memory blob `98fc0e30f42f885fb759b7e8b5dbab761932c5a5`, semantic blob `21767b69232db976eb011dd4c578003498f044e0`.
- Parent PR741 full suite independently inspected at exact source `4984b6006e4f38d659db59c2a05334a8d18ccf53`: Actions `40535266430`, **1911 tests OK (1 skipped)**, five exits 0, artifact `12748496582`, ZIP SHA256 `42fc105432d5711284fa01dfd8eda60fa46e19eca888bc1b50e23f9343fb6b46`.
- Own full software suite launched at `bb27d538f12fcb65b747cac96b1a2013fcd05915`, Actions `40538877446`: **PENDING** as of this checkpoint; do not claim full-suite PASS until exact raw exit audit.

All four ZIPs above were privately backed up to `/V13-Checkpoints/2026-10-27/Automation11L-Semantic-Query/` and independently materialized/byte-compared equal to downloaded originals. Public GitHub stores only synthetic tests and closed proof metadata, not private raw artifacts.

## Gates / next

LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; `jepa_weight=0`; Age authority 0; Redmi unmeasured; canonical architecture and user full scope incomplete. No native run or learned gain claimed. Next: inspect Actions `40538877446` exact raw exits, hash/privately back up its ZIP, update this report and branch-scoped state, independent review PR742. Then select next distinct canonical package, do not merge into main automatically.
