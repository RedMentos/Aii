# WP-Z12b independent action-index review — RED → GREEN

2026-10-27 UTC. Review-only PR #752, child of #749 exact base `bfeee06983a9a3bf7a00fd525c036c234b429fb0`, sibling of #751. Prereg commit `2f5c12bc7e896eed4dab4a3f24eb42dcfe893d1e`; test-only RED commit `cef90097fe515fb724ec5135606727c703e5b609`; GREEN source commit `374365b8764b7805d361accc632d3c7c5e29e9ee`.

## Confirmed defect
Before the patch, `score_model` called `np.eye(4)[action]` before checking that action indices were valid. An invalid -1 action silently indexed the final action and passed the one-hot equality guard if paired with action3. Invalid 4, float and bool arrays raised IndexError rather than controlled ValueError; wrong-shaped array failed with a different error. This is a **scorer input integrity** bug, not proof that the original valid frozen source rows were corrupted.

## Closed evidence
**RED** GitHub Actions run **40558023606**, exact checkout `d4f42342210196aef5009218c1f91d8c7e0895a3`, conclusion FAILURE as expected. 6 focused tests; one new test had five subcase failures: two FAIL (negative -1 accepted; wrong shape message), three ERROR (index 4, float, bool). Other 5 tests PASS. INSTALL/COMPILE/PRIVACY/DIFF raw exits 0; UNIT exit 1. Original RED ZIP artifact **12758042897**, SHA256 `f82855af5ec14c88f0ff481e078c8301e103c87af635d2aa218fa1542df97d6d`, CRC PASS.

**GREEN** GitHub Actions run **40558428083**, exact checkout `d329cd2167ab11fe2a53358f329eece4dc2d3e65`, conclusion SUCCESS. **6/6 focused tests PASS**, all five raw exits INSTALL/UNIT/COMPILE/PRIVACY/DIFF 0, privacy scan CLEAN. Patched heldout harness Git blob **`7a6fe2d5d2c3e22388437f40f5cc775428520909`**. Original World-JEPA model source unchanged. GREEN ZIP artifact **12757903621**, SHA256 `7dd7fae0c74dd6004b09f0394878b1645c59c6fae83908430aec747deb138c2d`, CRC PASS.

Both original raw ZIPs saved to private Library `/V13-Checkpoints/2026-10-27/Automation11V-World-Action-Index/` and re-materialized byte-identical by SHA256. Rejected anyone-writable Drive destination not used.

## Scope
Patch checks action ndarray shape, integer dtype (signed/unsigned but not bool), and [0,3] range before one-hot indexing; no model, registered source, training constant, optimizer, runtime, permission or Age change. Original PR #749 frozen result hashes and failed attempts preserved. No native LLM, no Redmi, no real-world World-JEPA proof. LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, STEP2 UTILITY_FAIL, B3 L1 FAIL, `jepa_weight=0`, Age authority 0, V13 incomplete. Independent full-suite review and integration remain open; draft PR, no main merge.

## Full software regression closure
Latest extended regression (object and unsigned out-of-range action tests included) **Actions 40558868194 SUCCESS**, exact checkout `4f855102a23b4cf60248850dce30b0545bb49abd`, **1933 tests OK (1 skipped)** in 214.510 s, INSTALL/UNIT/COMPILE/PRIVACY/DIFF exits 0, original model blob `5ffd56097e66a37e2922e39d1dc0ba86cb28a760`. Raw ZIP artifact 12759701132 SHA256 **`464865c844dcf9be48c5e7b842f9835c1d5b4bdf756647dd8266773e5ce3e24c`**, CRC PASS, private Library copy re-materialized byte-identical. An earlier pre-extension full suite Actions 40558702335 also passed 1933 tests (1 skipped), ZIP SHA256 `457c57d0e2240b632e4f4d038d5112e226b5186b6a172ecd521b748d2e8f1f0b`, also privately byte-verified. These are software tests, not native/Redmi/utility proof.
