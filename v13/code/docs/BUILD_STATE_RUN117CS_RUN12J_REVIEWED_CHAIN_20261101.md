# Run117CS BUILD_STATE — exact Run12J reviewed chain restored, no waiver

2026-11-01 UTC. Review-only branch `assistant/v13-run117cs-run12j-reviewed-chain-20261101-gpt6`, draft [PR #1571](https://github.com/RedMentos/Aii/pull/1571), exact parent Run117CR `947b1fa636d1185e610e701a4504d1011fa76247`. Prereg `PREREG_RUN117CS_RUN12J_REVIEWED_CHAIN_20261101.md` committed `fc9d5935fae218448d6b156cfe0942263a6827d1` before implementation. Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`, frozen source tests/fixtures/cohorts/model/runner unchanged. Not production-integrated.

## Exact implementation

Appended `run12j_native_route_admission` to `scripts.integrated_candidates._later` **after** `route_rule_lifecycle`. It uses strict one-occurrence `_replace` with the exact original [Run12J `47b7825704970de86766c3a57fd9ee999ca199a4`](https://github.com/RedMentos/Aii/commit/47b7825704970de86766c3a57fd9ee999ca199a4) patch: reject recursive extraction of arbitrary route strings and admit C2 advice only from one validated, unambiguous successful native `select_processing` function call. No arbitrary live hash whitelist, no production runtime rewrite, no other acceptance change. `INTEGRATED` records this explicit reviewed stage.

All four complete reviewed-chain files now match live **byte-for-byte**. Runtime SHA256 `8a403bffd1c2b14d9caa798cf17ea3c299cea5796115bad40cbaf9a2054072ed`; runners `87312169d871bcb1498ad028df058b0ab6e100f6e51c011ead4b9ecfb1b831c5`, memory_server `78b1eb46b11a55c8ba1a37fabd99bdf480d33f62a2c0d7a97822abc68e5a4672`, store `fe66f92533b20738b5ec384e9d7c0b5ac8b4b4f658c6c1ad23792d813ff29980`. Original source guard and mixed/modified source refusal remain.

## Original raw evidence

[Actions 41260651011](https://github.com/RedMentos/Aii/actions/runs/41260651011) **SUCCESS, 82/82** original and new source-handoff/eligibility/native-firing/B2/quote/chain software tests in 3.080s. All ten `PINS/VENV/DEPS/PIP_CHECK/COMPILE/TEST/CHAIN_AUDIT/NO_SOURCE_MUTATION/PRIVACY/DIFF` exits zero, privacy CLEAN. Run117CR source audit now `EXACT_REVIEWED_CHAIN`, `changed_files=[]`, complete diff **0 bytes**. Original raw artifact `13065540135`, ZIP SHA256 `f9c0624693d6c82f84c7481d8a4cfe5bb5aa777e2ee105536b3dcd372a23e841`, independently CRC clean and **24/24** inner hashes verified. PR-event synthetic merge HEAD `a72d3a41354658c58fc86650a9f32cc0fc4534ba`, source/test blobs pinned. Private Library backup `/V13-Checkpoints/2026-11-01/Run117CS/RAW_GREEN_41260651011_shaf9c06246.zip` re-materialized byte-identical SHA256.

## Limits and next command

Focused source-chain GREEN **does not** make the unfiltered Run117CI 5,331-test full suite GREEN; its original 4 failures, 75 errors, 28 skips remain preserved until a new full unfiltered run with original artifact prerequisites. Next separately preregister a full-suite run on this exact reviewed branch with all known immutable original ZIP prerequisites restored by SHA256, never changing tests or historical negative gates. Also retain substantive independent Body-JEPA/JEF/C3/ContextOS/Callosum work.

Reproduce focused tests with isolated numpy2.2.6, psutil7.0.0, PyYAML6.0.2, Pillow11.3.0, prompt-toolkit3.0.52: `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_run117cs_run12j_reviewed_chain tests.test_run117cr_source_chain_drift_audit tests.test_source_handoff_candidate tests.test_eligibility_fixed tests.test_native_firing_merged_candidate tests.test_native_firing_runtime_candidate tests.test_b2_offer_candidate tests.test_quote_context`.

Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, `jepa_weight=0`, no native/Redmi/learning/whole-system promotion. Remaining platform budget UNKNOWN.
