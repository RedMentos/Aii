# WP-T8 Sleep B for_event observed-state integrity — review checkpoint

Date 2026-10-27 UTC. Owner GPT-6 continuation. Review-only child of PR #745 exact parent `e8edc8a83bbf66624cda9482367daf7acabc3eee`. Prereg `e804536221b9dc0fb5a71b48fd5fb055ee61ef54` before tests and code.

## Change

`world_model.for_event` previously decoded the recorded forecast without validating its JSON, required input, resource and timestamp, and could invent a zero-input state. Sleep B's route-alternative consumer now returns `SIMULATION_UNCERTAIN`, confidence 0, `INVALID_OBSERVED_STATE`, HYPOTHESIS for malformed observed data; valid events still delegate to unchanged counterfactual logic. Source `dc88e350eace31ad82a30aa125064dd2221cc18d`, world_model blob `03048707912a23a2ae75a0944a58e39a7134a595`. No model or authority change.

## Evidence and preserved failures

- Initial test-only RED `b09b0a0a43aae875e03da4a9b2163cf496bbbdbb`, Actions `40543504962`: 12 tests, 9 ERROR (some fixture contamination from mock intercepting unrelated store.state); other four exits 0. Artifact `12752206675`, ZIP SHA256 `dcf691f844a9d5e25262b8b1af498770dbfe71818fbbb40ea71bd3b5f8662369`, private byte-exact backup. **Do not claim all 9 errors as implementation counterexamples.**
- Clean RED replay: separate test-only branch `codex/automation11p-red-clean-20261027`, exact original world_model blob `95059f97bf58a1979cc8c016ba6061d94be85512`; Actions `40544298279` at `be00b142e1d35a8f94ae8cbef71b95183a8d33c8`: 12 tests, **6 expected FAIL + 2 expected ERROR** for malformed JSON and missing/invalid observed state; other exits 0. Artifact `12751279900`, ZIP SHA256 `d80c00c91a05fdb92ab3bc36adeb5dc3e127dc3cc89163db5273b63a7d66850a`, CRC clean, private byte-exact backup.
- First GREEN focused `40543550150` source `dc88e350eace31ad82a30aa125064dd2221cc18d`: one fixture ERROR due valid-path mock intercepting store.state; artifact `12752516595`, ZIP SHA256 `a47446c426d0105d5260c8d1e128c4c42c06ced3bacd26cf8b21eb494506d0f9`, preserved privately.
- First full suite `40543578378` at `46aca17c50e9d291d7757434930f8f08ed85b8e4`: **1921 tests, 1 fixture ERROR, 1 skipped**, all other exits 0. Artifact `12752705702`, ZIP SHA256 `b9fc8d372b679d266f48ce6748546470252844c502cdb455a3290df44f3de4b9`, private backup. No PASS claim.
- Corrected GREEN test-only fixture `c21b5e7c3aab055efe652ef480de406a9825e38c`, focused Actions `40544080260`: **12/12 PASS**, INSTALL/UNIT/COMPILE/PRIVACY/DIFF 0; artifact `12750689479`, ZIP SHA256 `ea0218b829b04709b8fd880b2657b4ef98b10f90d46d876a58d491464c61b134`, CRC/source/HEAD verified, private byte-exact backup.
- Corrected full suite Actions `40544080303` **PENDING**, no full-suite PASS claim yet.

Private artifacts under `/V13-Checkpoints/2026-10-27/Automation11P-World-Event/`. No raw private logs in GitHub.

## Gates / next

LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; `jepa_weight=0`; Age authority=0; Redmi unmeasured; V13 incomplete. No native/model/Redmi or main merge. Next: inspect Actions 40544080303 exact raw exits and backup, independent review, continue separate World-JEPA readout package.