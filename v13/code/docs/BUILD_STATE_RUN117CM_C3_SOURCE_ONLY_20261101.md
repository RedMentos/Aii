# Run117CM BUILD_STATE — JEF/F1/F5 source-only C3 candidate

2026-11-01 UTC. Review-only child of Run117CL at exact parent `da5eac838296ca32eb4d111b781d45dfc8823a4e`. Owner Run117CM. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`, registered native source/model/seed/runner cohorts unchanged.

## New source-safe research path

New default-OFF `v13/jef_c3_source_only_shadow_candidate.py` (final blob `6886799315457fe51698e43fd483707da7b9b5e2`, initial pre-hardening blob `977534a8e6b9afd3db5a9fad5f318383e400f944`) constructs a source-verified C3 prompt from exact human policy, sheet and current request after strict existing F1/F5 admission. It deliberately does **not** expose JEF's computed `suggested_action` or `typed_jef_action` to the model. The output is a **prompt only**, no model call, no tool/output/learning/age authority. A second admission and full-span source reread fail closed on mid-composition changes. Bounded payload 16,384 bytes, two distinct human source records, latest USER event, explicit operator opt-in.

New real-Store test final blob `b512efece4875586a7ffa6cb9e709175de382161` (initial blob `fc4c35cc68be33d91f75593b80c39ec8d5bd168d`): deterministic no-oracle payload, reversed memory ID order, default-OFF and fake TTY rejection, foreign/revoked/stale source, mid-composition revocation and size cap. Existing JEF/B1B2/C3 tests included. Source admission blob `5449e4f4481174b17433ae3e5af035e90a90dce0` and full-source reader blob `7cfae3d54e49718181813cea68238301e2ffae87` unchanged.

## Evidence and next command

Initial [Actions 41258283362](https://github.com/RedMentos/Aii/actions/runs/41258283362) **SUCCESS**, 26/26 software tests, original artifact `13063904123`, 4,131 bytes, ZIP SHA256 `c395790bcb8c08d43bade0b64e1c7087b8bd961d2bbe491f797000068abcbd0d`; independently CRC clean, 16/16 hashes, all seven stage exits zero. After explicit negative-gate/revalidation fields were added, intermediate pin-RED source runs preserved. Terminal corrected [Actions 41258353876](https://github.com/RedMentos/Aii/actions/runs/41258353876) **SUCCESS** at source `c6381e9a46f4b3feec991a6126413b4d2fb5712d`: original artifact `13062974316`, 4,134 bytes, ZIP SHA256 `c96882062c2e272ac48e2388866fa54de8e4f32b09675eae3d41c61b9016b519`; independently CRC clean, **16/16** inner hashes, **7/7** stage exits zero, **26/26** real-Store/JEF/C3 software tests PASS, compile PASS, privacy CLEAN. This is prompt-construction proof only. Exact command: `cd v13/code && python -m unittest -v tests.test_run117cm_c3_source_only_candidate tests.test_run82_jef_b1b2_c3_dual_source tests.test_b1b2_c3_source_envelope_candidate tests.test_run83_native_driver_fake_c3 tests.test_run117cj_c3_native_absence_gate`.

Next: independent prompt-leakage review, then preregister a **new disjoint native** source-only vs typed-correct vs typed-wrong cohort before any native inference; keep original negative results. No current evidence of independent C3 reasoning, utility or RSI/AGI.

Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, `jepa_weight=0`, no Redmi/learning/tool/whole-system promotion. Full-suite Run117CI remains separately RED or pending until raw audit. Platform budget UNKNOWN.
