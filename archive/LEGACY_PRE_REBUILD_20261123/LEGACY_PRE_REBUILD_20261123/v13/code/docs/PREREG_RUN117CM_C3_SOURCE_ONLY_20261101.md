# Run117CM prereg — default-OFF source-only C3 research envelope

2026-11-01 UTC. Review-only child of Run117CL handoff branch at exact parent `da5eac838296ca32eb4d111b781d45dfc8823a4e`. Owner: Run117CM. Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. No native model, Redmi or learning.

## Why this candidate

Run83/117CH demonstrated **typed JEF answer copying**, not independent C3 reasoning. A future source-reasoning pilot must avoid leaking the fixed reader's answer to C3. This default-OFF software-only module builds a source-verified prompt with the full human policy, option sheet and current request, but **no suggested_action or typed_jef_action**. It uses the existing strict F1/F5 human-source admission and full-span SourceRefs; rechecks after composition; no output, tool, model or learning authority. It is not installed in Runtime and does not replace the canonical typed-JEF formatter.

Source module blob `977534a8e6b9afd3db5a9fad5f318383e400f944`; test blob `fc4c35cc68be33d91f75593b80c39ec8d5bd168d`. Six real Store synthetic software tests: deterministic no-oracle envelope, reversed memory-ID order, default-OFF and fake approval, revoked/foreign/stale sources, mid-composition revocation, payload size bound. Existing frozen Run73/75/82/83 cohorts and source/model/seed hashes unchanged. This is **not a preregistered native cohort**; any future native comparison must register a disjoint unseen cohort and strict scorer before inference.

## Acceptance and negative gates

Software acceptance: all new and existing JEF source-envelope tests pass; source refs and Canon pinned; privacy/diff/compile clean; original raw ZIP and stage exits preserved. Do not infer independent reasoning, model utility, STEP2 or learning from prompt construction. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, `jepa_weight=0`, no whole-system completion.

Exact command: `cd v13/code && python -m unittest -v tests.test_run117cm_c3_source_only_candidate tests.test_run82_jef_b1b2_c3_dual_source tests.test_b1b2_c3_source_envelope_candidate tests.test_run83_native_driver_fake_c3 tests.test_run117cj_c3_native_absence_gate`. Next: terminal raw audit, independent prompt-leakage review, then preregister native source-only vs typed-correct vs typed-wrong arms on new disjoint source tasks. Remaining platform budget UNKNOWN.
