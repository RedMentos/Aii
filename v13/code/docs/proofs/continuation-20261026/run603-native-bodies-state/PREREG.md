# Run603 preregistered current-source B1/B2 native state and restart proof

2026-10-26 UTC. Owner GPT automation11. Base exact verified Run602 PR597 checkpoint `50051320ced1907fd4e140e1e25ce218143b3175`. Review-only new branch `codex/automation11-run603-native-bodies-state-20261026`, no main edit.

Problem: original `probe_body_state` demonstrated six native B1/B2 source/context/restart cases historically, but recent ContextOS, Callosum, JEF, B2 state and model/source changes make that proof stale for the current head. Current B1/B2 structural use must be measured on original pinned public model/runner, not inferred from software mocks.

Files owned: new isolated `.github/workflows/run603-native-bodies-state.yml` and this proof folder. Reuse unchanged `v13/proofs.py::probe_body_state`, `v13/bootstrap.py`, `specs/models.json`, `tests/test_body_state.py`. No model, seed, canonical source, runtime, Age, approval or cohort edits.

Protocol: exact source/Canon/model SHA pins, source-only body-state fixture first, pinned isolated dependencies, original bootstrap of public models and runner only after fixture PASS; actual `Runtime` + `probe_body_state` on Linux with separate temp brain and real B1/B2 native offers, 6 cases including restart and ablation, bounded output and no automatic learning. Serialize in `v13-native-c3-run131-serialized` with cancel-in-progress false. Independent postflight requires actual native token receipts, readable sources, bounded context/state, restart, unchanged generation, no updates, reaped process, original negative gates, privacy CLEAN, raw SHA closure. Preserve RED/partial attempts.

Scope: this is Linux-native *structural* B1/B2 context only, not semantic complementarity, distinct trained MoE, receiver injection, body JEPA, Redmi or native sparse weight learning. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE. No anyone-writable Drive, no private data in public raw.