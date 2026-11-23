# C2/Needle native route provenance isolated Linux pilot — prereg 2026-10-30

Owner `assistant/v13-c2-native-route-provenance-20261030-0425`, review-only child of STEP2 v3 PR #1204 at exact parent `f41ecd93e50b475787a9a13272d1c2c20e99fb6e`. The separate 27-turn v3 native Actions `40996792157` owns the heavy runner now; **do not launch this C2 native job until it finishes**. This is an independent **C2-only route invocation** proof, not a change to v2/v3 registered cohorts or a STEP2 utility test.

## Fixed before implementation

Three fresh synthetic human text prompts, seed **43**, ordered:
1. `Compare two local options and reason about their budget and timing.`
2. `Summarize the previous context in one sentence without inventing details.`
3. `Hello. Is this a simple greeting?`

Canonical JSON prompt SHA256 `c952103c6f36bff983659977783f2b6447264bc72e93f76412a69f91ca1fde25`, compact JSON separators, calculated before code. One fresh isolated Age0 Runtime per prompt, `route_override=auto`, `observer_mode=off`, no learned route head, no procedural memories, no prior conversation, `control_seconds=20`, `learning_mode=RECORD_ONLY`, `latents_enabled=false`, `jepa_weight=0`. Invoke `Runtime._route(text, stored_authoritative_event, deadline)` with a genuine installed pinned native Needle/C2 runner; do **not** run C3/Body inference or submit an assistant answer. This is an internal test interface, not a production command or full end-to-end route acceptance.

**Proof contract:** native invocation is proven only when route info contains actual `native_control` and `native_control_metrics` with `role=C2_CONTROL`, `operation=C`, `status=FINAL`, a process memory measurement and matching stored `ExecutiveControlContext` packet/source. Record actual route source separately: `NATIVE_C2_ADVISORY` only if native proposal selected; `BOOT_SCAFFOLD` with native_control means the native control ran but did not select route. Reject `OPERATOR_ROUTE_OVERRIDE`, `APPROVED_EXTERNAL_HEAD`, `control_unavailable`, missing metrics, revoked or cross-session source. Record native PID/process cleanup; never infer a C2 proof from a synthetic unit stub. Preserve failed raw. No external actions, no tool calls from models, no learning.

**Source pins:** Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`, catalog `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, tools `954a3f468f10195fbce12d27f68585ee7edee2c9`, actual model/binary verified deep by existing bootstrap/ModelManager. New source/test/workflow pins frozen after software preflight. Native workflow uses same GitHub Actions concurrency group `v13-step2-budget-paired-native-20261030` to serialize with v3. Maximum native job 25 minutes, no paid resources.

**Outcomes:** report `NATIVE_C2_INVOCATION_PROVEN_3_OF_3` only if all three genuine isolated invocations meet the contract, with source/model/process/packet links; otherwise `PARTIAL_RED`. This is **not** C2 calibrated confidence, not C2+C3 integrated quality, not STEP2 complementarity, not phone proof, not B3 or JEPA. Full architecture incomplete, Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, all historical failures retained.

**Execution:** add source-only evidence validator tests first; verify isolated Linux software preflight and preserve raw; after v3 heavy run terminal, launch pinned native workflow; independently audit raw ZIP SHA/CRC/SHA256SUMS and privately back up; then plan integrated C2+C3+Body counterbalanced acceptance without route override.
