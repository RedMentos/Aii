# Run315 preregistration — real Linux-native C3 second-turn correction/forget utility

2026-10-25. Owner `assistant/native-c3-second-turn-run315-20261025`.
Parent exact Run314 source ZIP checkpoint `133f813be06dbaa0944dbee26d8270e1175edfbe` (branch-scoped, not main). Owned files only new `v13/code/scripts/native_second_turn_probe_run315.py`, `v13/code/tests/test_native_second_turn_probe_run315.py`, dedicated `.github/workflows/run315-native-c3-second-turn.yml`, proof directory. Do not edit Runtime/Store/Memory/ContextOS, model pins, registered cohorts, Canon or source seeds.

## Goal
Actually exercise F1 exact human-correction source → persistent Memory → C3 prompt after Runtime restart → real pinned native C3 response, then source `:forget` and another restart/new session. Prior Run204 was a deterministic C3 test double, not real native utility. Run267 public pinned bootstrap succeeded but G13 2-day native soak failed day1 wake_priority; that separate negative remains. This is a controlled C3-specific native test, not whole-system G13/JEPA proof.

## Frozen setup
Use unchanged `v13/code/specs/models.json` pins: C3 `LiquidAI/LFM2.5-350M-GGUF` revision `657e078c94084481950a2d555a941481f715536b`, file SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`; llama.cpp runner b10964 source SHA256 `4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe`. Bootstrap via existing `v13.bootstrap` with all registered model hashes unchanged, isolated CPU deps and serialized native runner concurrency group. Test uses an invented synthetic project/code, explicit synthetic correction (no real user secret), global memory scope, three fresh sessions, `route_override=simple`, observers off, lexical recall, ContextOS SHADOW and 64-token C3. No fake model in native job.

## Measurements/acceptance
1. Actual native Runtime outputs terminal statuses for first/second/third questions, native runner identity/model hash and bounded elapsed timings; preserve raw outputs, no hidden fabricated answer.
2. Exact source-bound correction is present in second C3 prompt/context and absent after explicit forget in third. First prompt must not contain the code. Check memory row source and forget state. The context itself is captured via production `LAST_NATIVE_CONTEXT` (not a monkeypatched prompt).
3. Compute `native_second_exact` and `native_after_forget_exact` from actual generated output; report utility as observed PASS/FAIL, never claim model weight learning. If model fails to use correction, preserve UTILITY_FAIL, do not hide.
4. Deterministic fixture test separately verifies harness flow without model and is labelled FIXTURE_ONLY.
5. All raw errors, source/model SHA256s, restart states and native process cleanup saved even if nonzero. No native evidence promoted to Redmi or STEP2/B3/Body-JEPA/jepa_weight gates.

## Stop/continuation
Commit prereg before code, run fixture tests in isolated Linux and actual native CI, checkpoint. A native failure blocks this proof only; continue another independent package. No paid provisioning or private data.
