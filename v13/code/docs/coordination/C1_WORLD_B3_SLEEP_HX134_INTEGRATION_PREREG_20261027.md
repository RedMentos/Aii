# C1 + World + B3 + Sleep A + HX134 cross-organ integration prereg (2026-10-27)

**Review-only, not main.** This prereg is committed before any integration candidate. Primary base is verified PR #787 at `edbb440f0a4298f1d740aa6260ca2b16e2791e7f` (tested source HEAD `a5afac87f19b46c100a1bfa51dccb8dcc4981c87`, Actions `40595165234`: 2015 full software tests OK, one skipped). Proposed independent HX1/HX3/HX4 source is review child PR #789 at `7a56a53018fa6db9c0d783ee45065ee4dfaf4bed` (its full CI **must pass before integration**), building on PR #788, itself based on Claude HX source. Prior PR #163 supplied earlier tested request revocation/evidence freshness logic; retain that provenance.

## Exact scope

Copy HX source/test blobs from verified PR #789 only after exact-head full suite passes:
`v13/code/v13/agi/{__init__,self_improve,harness,experience,blind_select}.py`,
`v13/code/tests/{test_harness_hx,test_hx_approval_run133}.py`, plus the HX-specific prereg/result/BUILD_STATE evidence documents and dedicated workflow files if needed. Preserve the C1/World/B3/Sleep base byte-for-byte. Keep a two-parent merge commit and verify source blob IDs and ancestry. Do not transplant stale global ROADMAP/HANDOFF or modify frozen model/cohort/seed.

## Required falsifiable checks

- C1 persisted source provenance, World observed-outcome SHADOW, strict B3 L1 seven-arm/seed/report/promotion gates, Sleep A exact memory identity, HX AG8 stored approval and request status, HX3 stale evidence and HX4 blind selector must coexist.
- Run focused cross-organ tests, full Linux software suite, compileall, privacy scan and diff check on the **same exact HEAD**; close original raw logs, hashes, CRC and private byte-verified backup. Fail on any raw exit or source hash mismatch.
- Verify SHADOW-only harness/experience: no new live prompt consumer, no self-approval, no Age advancement. All original B3 L1 FAIL, STEP2 UTILITY_FAIL, LP1/LP2/BJ1 negative gates, `jepa_weight=0`, authority0 and incomplete full V13 stay unchanged. Linux software tests are not native receiver/Redmi/semantic utility proof.

Owner: GPT integration reviewer; only new `C1_WORLD_B3_SLEEP_HX134_*` coordination and workflow files are locally owned; imported HX blobs remain exact parent bytes. Both parent review branches and other agents' work remain untouched. Next: verify PR #789 full-suite Actions artifact, then construct two-parent exact-tree candidate and run full cross-organ CI. No auto-merge.
