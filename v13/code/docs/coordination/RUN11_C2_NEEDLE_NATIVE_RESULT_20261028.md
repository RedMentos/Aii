# Run11 C2_CONTROL Needle3 current-catalog Linux native — verified checkpoint 2026-10-28

Owner: Codex; review-only PR #843 child of #842. Prereg `30e57c138dc88d3bdd7675180c5aea725aab385a`, source `ce3a9f7a66dec00826dbe9f02189f8ab31f6ce3b`. Catalog, model, official binary, tool schema unchanged. No main or parent owner branch overwrite.

**Synthetic software guards:** workflow `40631463502`, source `a5872c1d83bea171eb5bf7b59af51979934c3630`: 10/10 PASS, compile/privacy/diff0, artifact 12791602995 ZIP SHA256 `3d4583a8d9738297bc3f9b91baace3392852ec24901b08ded7a6542bc841c12b`, CRC and 11 internal hashes verified. No model downloaded in this guard run.

**Actual pinned C2 Linux native:** GitHub Actions `40631873306`, source `ce3a9f7a66dec00826dbe9f02189f8ab31f6ce3b`, SUCCESS. Artifact 12792140870 ZIP SHA256 `8f250f4e9a24473ce427925624e6f4904d68115776baf8eae2de2c66d7808fb8`, CRC valid and **17/17 internal SHA256SUMS verified**. Guards, native, report binding, privacy, diff all exit0. No model or binary uploaded.

Pinned `Cactus-Compute/needle3` Apache-2.0 model `needle3.cact` 35335380 bytes SHA256 `c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38`; official Linux-x86_64 Needle CLI 1246880 bytes SHA256 `5eb163c5ed33bd914c103ef8eba2134c7bb2d97bafafdd69f410a4a3100e8c37`; `specs/control_tools.json` Git blob `954a3f468f10195fbce12d27f68585ee7edee2c9`; catalog blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`.

Fixed public prompt `Budget 120 Euro. Berechne die Hälfte.`, existing V13 runtime Needle fallback flags `--max 160 --depth 8 --threads 2`, telemetry disabled. Native exit0, 1.018s elapsed, raw stdout375 bytes SHA256 `f60d330e07d9f535820c3d3df9564a7f004e765f75fc85f2e95e34e594306ce3`, stderr0, valid finite unique-key JSON with actual `select_processing` function call route **`both`**, confidence `0.9930` in native output, no timeout/cap, raw complete. **Neither the route's correctness nor confidence calibration is established by this one example**; this is a function-call smoke, not a benchmark. No external tool was executed.

No C2 authority, no JEF end-to-end orchestration, no B1/B2/C3 within this run, no Redmi or thermal/RSS. Previous separate current-catalog B1/B2/C3 serial Linux native run `40631633470` GREEN, but separate jobs do not prove integrated routing.

## Next work

1. Run an actual isolated V13 Age0 end-to-end Linux bootstrap and `v13 probe step12` with pinned current models and Needle worker, closed raw and no user data. Check resource/owner and age gates before launch. No model bytes uploaded.
2. Run full software regression on the C2 source branch (parent 2208 tests GREEN before this addition); do not equate 10 focused tests with full.
3. STEP2 four-arm causal utility, B3, Body-JEPA, learned JEF heads and Redmi remain separate acceptance gates.

Negative gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY; canonical_architecture_complete=false, user_full_scope_complete=false. Remaining platform budget UNKNOWN.

Next focused command: `cd v13/code && PYTHONPATH=.:tests python3 -m unittest -v tests.test_current_c2_native_linux_smoke_20261028 tests.test_native_smoke_io_20261028`.
