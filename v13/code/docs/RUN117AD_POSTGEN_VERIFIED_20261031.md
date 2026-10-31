# Run117AD verified software checkpoint — 2026-10-31

Review-only PR #1510, child of Run117AC #1509. Prereg `e1210ee90767b9232b2141aa0ce3520cf1fd1a0b` preceded candidate `caa47a03390a49644c5540e994eafdbbf09a92a3` and tests `6cd549ddf061b2c1536eb07ea178355d16c5d3c5`. Original Run117AC CI **RED** run `41234060257` remains preserved: its test selection attempted original native replay without the required original ZIP; it is not reclassified as GREEN.

Verified source HEAD `a1a9d31128784bf46fbb6e4f37a655b106f0490a`; GitHub Actions `41234588852` / job `124635580174` **SUCCESS**; 55/55 model-free tests in 2.714 s; all exit codes DEPS/FIXTURE/TEST/COMPILE/PRIVACY/DIFF = 0. Artifact ID `13055117418`, Actions-uploaded ZIP SHA256 `51f57435f421eeb12eb1abf9f7b85346e4fbe1a9578adc3319765c5b8b26a39a`. Frozen seed1065 fixture SHA256 `cb008f27a4d1ef7f0f288419ac276ebb67c8d7958da3c62104994822dd90634d`.

Verified remote Git blobs:
- postgen source `47f64f2d81b5241ea5e66b3297370d319c952ac3`
- postgen tests `6e5472d87b1146cf6224cea26b71448aa219a2ee`
- prereg `b72053c09b7600742ea83dd6a20e78de90c97c6b`
- child CI `837e868c22f5d99c2a0ee946c6d3dbc808192632`

Result is only a **trusted callback software SHADOW** check over actual persisted SQLite Store and synthetic Body offers. No original native ZIP replay, no new native model inference, no independent external side-effect containment. Even a PASS returns only hashes and lineage; no output, tools, approvals or learning. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, `jepa_weight=0`, no Redmi and no whole-system completion.

**Open**: parent Run117AC CI must be repaired or its artifact-dependent replay separately staged; do not delete or overwrite original RED. Native B1/B2 quote availability remains 3/6 partial RED from Run117U. Next independent package: preregister original Run117Z native-output replay through this *combined* postgen bridge, download immutable artifact `13054946077` and verify outer SHA256 `65939e4dea18f15bf11d5b1b3c5128f5a6128c6d03b9d2beb090f185d03fb69a` before using the six recorded typed outputs. This will be recorded replay, NOT native inference of the combined bridge.

**Owner**: Run117AD GPT-6 review branch; other active Claude/Codex branches untouched. Exact next command after artifact fetch: `cd v13/code && V13_RUN117Z_ORIGINAL_ZIP=<verified-original.zip> python -m unittest -v tests.test_b1b2_jef_span_c3_postgen_shadow_candidate`. Run full suite separately with original historical source-pin failures retained. Remaining platform budget UNKNOWN.
