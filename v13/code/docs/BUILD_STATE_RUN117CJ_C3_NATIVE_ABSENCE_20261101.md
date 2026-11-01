# Run117CJ BUILD_STATE — actual no-native-weight negative gate after synthetic C3 harness repair

2026-11-01 UTC. Review-only child of Run117CH PR #1561 at exact parent `594143dc778e4317f0b011b862a7b94232567488`. Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7`, registered Run83 seed839 fixture, native script, runner/model hashes unchanged. Owner: Run117CJ.

## Why this is required

Run117CH fixed only the **synthetic** `DryRuntime` rehearsal, allowing it to pass without a real model cache. That test intentionally mocks model file hashes and C3 outputs. It cannot prove that production native C3 would run or that missing weights are acceptable. Run117CJ adds a separate real `Runtime`/Store negative preflight with no fake model path and no file-hash mock. On a fresh home, the production Run83 entrypoint must preserve `STRUCTURAL_RED`, `Unavailable`, zero native/body calls, zero committed output and learning/delivery authority, a closed Store and a persisted raw error report. A second check asserts that the real native entrypoint still references the actual Runtime class.

The synthetic positive test and actual native-absence negative test run together, so a future edit that accidentally makes the real path silently accept absent weights is caught. No model download, native inference or age/learning promotion is claimed.

## Source pins and verification

- Production native script blob `68dcb88818c7c4efb2bb3297d2d0c93c140d9362`, fixture `a590a359df5b2baed2c622c949ed9c793e185265`, synthetic-only test `883f5ea8a34cfd68aa46ce338cf4b68288e1d3b1`, new negative test `c9bf2dc8ff0c0fbcbeeafdf1eee7bb82e25eeb1a`.
- Exact focused command: `cd v13/code && python -m unittest -v tests.test_run117cj_c3_native_absence_gate tests.test_run83_native_driver_fake_c3 tests.test_run52_b1b2_cross_turn`.
- Original focused [Actions 41257796795](https://github.com/RedMentos/Aii/actions/runs/41257796795) **FAILURE** at `150362cc00dc394b6ad01e9594c6a757795b6f0f`: **7/8 tests passed**, including the actual no-weights `STRUCTURAL_RED` negative control. One *test assumption* was wrong: the native entrypoint uses an isolated subclass of production Runtime, not the identical class. Original artifact `13063639334`, 3,831 bytes, ZIP SHA256 `4fa3f9f465cc3a48d9a5c301ee3dd95c33d6fb89e9e7b981efadb8ead5719d9c`; independently CRC clean, 16/16 inner hashes, all stages except TEST_EXIT=1 zero. Corrected assertion checks subclass and inert-worker override; no production code modified. Intermediate pin-RED retained.
- Terminal corrected [Actions 41257878800](https://github.com/RedMentos/Aii/actions/runs/41257878800) **SUCCESS** at source `79bf9d84fb75ccf6549bbb134ab6f6c8f5f0be17`: original artifact `13063763909`, 3,602 bytes, ZIP SHA256 `b27c8e7a9684860709dddbd9c109541fbcf40452b1de5757165c4ce0c0dada06`. Independently CRC clean, **16/16** inner hashes, **7/7** stage exits zero, **8/8** focused software tests PASS, compile PASS, privacy CLEAN, diff check PASS. Actual missing-weights gate returns STRUCTURAL_RED/Unavailable as required; this is a successful negative control, **not native inference**.

## Negative gates and next

Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, `jepa_weight=0`, no native/Redmi/learning/authority/whole-system completion. No production merge. Next: verify terminal raw, inspect the concurrent unfiltered Run117CI full-suite original evidence, then prioritize true native model/runner prerequisites without weakening original source gates. Platform budget UNKNOWN.
