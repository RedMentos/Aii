# Run94 prereg — explicit offline source-answer CLI for real Age0 operator utility (2026-10-29)

Owner GPT-6 scheduled continuation. Preregister before source/test implementation. Review-only independent child of independently audited Run92 #999 exact `58eb54a05532a5b9d25bd9713faf3bec1d55baff`; does **not** alter Run93 registered native cohort, frozen C3/Memory/SourceConsumer/Runtime/Store/Operator, or main.

## Problem and intended user behavior

The source-verified budget candidate currently requires calling a standalone script; the standard interactive `:verified` intentionally provides a **model-free preflight only** and explicitly rejects native. Add an **explicit, offline top-level CLI** `python -m v13 --home HOME source-answer "What is the budget for Project Elyra?" [--native]`, using existing `BudgetContext` and `query` unchanged. Without `--native`, return READY/CLARIFY/NOT_APPLICABLE and zero native calls. With `--native`, use the existing bounded, hash-verified C3 path and return FINAL only when its exact source/teardown guards pass. This is a human-triggered command, never an autonomous worker, learning path or production `Runtime._turn` integration.

## Fixed implementation and test requirements

- Touch only `v13/code/v13/__main__.py` plus new Run94 tests/docs/workflow. Current CLI blob `aa9995afad35f90b67c64f0a79245570ab3c5189`. Frozen `scripts/ask_verified_budget.py` blob `75ca7f3f197665f665d9582b7f5c2efb1f598235`; `v13/source_consumer.py` `4b73842be25e784f70ade4f6c4ced3fe2dcb9eab`; `v13/runtime.py` `68e7ed1352800174972558f1e0b0683a42c8689a`; `v13/operator.py` `7bf3a992af1db87f6ee2432c2486dbbced0f2bd4`; `specs/models.json` `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`; canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7`.
- **Existing home required**: no silently initialized blank home. Existing Runtime/Store coordinator lock must be respected, no concurrent native query while chat is running. Do not bypass the lock.
- Default preflight must not invoke a model or expose an answer. Existing persisted source `Project Elyra budget = 615 Euro` returns READY, wrong project returns CLARIFY, out-of-scope returns NOT_APPLICABLE. Existing session retained; no new chat, no write to source state.
- Native flag explicit, bounded timeout and max-token arguments forwarded to the frozen query; test forwarding with a mock (software only, not native proof). Query handles deep model SHA, source revocation, teardown and answer gate. Errors must be nonzero, no invented success/answer. The `:verified` interactive semantics must remain model-free and unchanged.
- Focused tests with real Runtime/Store/Memory/CLI preflight and a mocked native call; full test suite, compile, privacy/diff, closed SHA256SUMS. Record original RED if failures. No model install/download in this software package; Run93 independently measures actual C3 native source utility.

## Claim limits

This improves **operator reachability**, not C3 semantic quality, native model execution, JEPA/STEP2/B3/Body-JEPA/LP3, Redmi, Age promotion, or whole V13. Age0 RECORD_ONLY, `jepa_weight=0`, no tool/learning authority; do not merge main.