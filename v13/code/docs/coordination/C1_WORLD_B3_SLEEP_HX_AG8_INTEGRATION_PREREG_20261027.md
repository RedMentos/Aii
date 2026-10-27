# C1 + World + B3 + Sleep A + HX134 + strict AG8 shield integration prereg (2026-10-27)

Review-only child of cross-organ PR #791 at source/workflow HEAD `60d36be2c67a392b3e6338f7c887dfc4a1bd346d` (**its combined full CI must pass before merging**). Independent AG8 shield source is PR #790 at `3fd83a07c1e06f515ca32da909bc868285b4dc17` (**its full CI must pass before merging**), reusing earlier verified PR #375 / Run380. No production/main merge.

## Scope and immutable proofs

Copy only the strict AG8 metric shield `v13/code/v13/agi/self_improve.py` exact blob `4ff5ee079653488d9117380c6b7435df38966824`, exact `v13/code/tests/test_ag8_shield_metrics_run380.py` blob `0d07e975513b3adb4c24d3244314a13ba0e73926`, and relevant Run380 prereg/result/BUILD_STATE and workflow evidence. Preserve C1 `057dda1e705053047489516fc9ab10581018f5a4`, B3 bridge `8837693b4ee1b37ed2fec538c40a2b398ad8261a`, B3 degrade `5cc822ecad749887acfad69f5fcba39a5a2dae8f`, Sleep A `469101c9979b9cabe0dbd154cffde40912fa8a2c`, HX harness `78e3fd6c6c40a75db9cb88ea683194011e058d6f`, HX experience `83ede4b83161bc78b5cc718c647d984e06d9f54a` byte-identical. Verify both parents and the original prereg before any CI claim.

## Acceptance

1. Both parent full Linux suites SUCCESS on their exact source HEAD, raw ZIPs CRC/hash/exit verified and privately backed.
2. Two-parent exact-tree merge, no changes to models/cohorts/seeds, AGE/authority/learning rules.
3. Combined focused tests across C1/World/B3/Sleep/HX/AG8 strict shield and full software suite, compileall, privacy scan, diff check. Capture original raw exits and source/test hashes, privately re-materialize backup byte-identically.
4. All negative gates remain: B3 L1 FAIL, STEP2 UTILITY_FAIL, LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, `jepa_weight=0`, Age0, latent authority0, no live HX consumer, no native/Redmi proof, incomplete V13. No auto-merge.

Owner GPT integration reviewer. Only new `C1_WORLD_B3_SLEEP_HX_AG8_*` coordination and dedicated CI workflow are owned; imported exact blobs belong to parent reviews. Next: verify Actions #791 and #790, merge strict shield only if both full suites pass, rerun complete integration.
