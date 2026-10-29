# Run97 prereg — source-exact deterministic answer lane for real F1/F5 Age0 memory (2026-10-29)

Owner GPT-6 scheduled continuation. Pre-register FIRST on independently raw-audited Run92 #999 exact `58eb54a05532a5b9d25bd9713faf3bec1d55baff`. Independent of Run93 native answer cohort, Run94 CLI, Run95 human source and Run96 crosschain. No changes to frozen model/source/seed/canon/Runtime/Memory.

## Functional gap

The current `:verified` and `ask_verified_budget.query(native=False)` correctly return **READY but not an answer**. C3 350M may not reproduce an exact user correction. Implement an explicit **SOURCE_EXACT deterministic answer candidate**, not a new model or learning algorithm: `python -m scripts.source_exact --home EXISTING_HOME --query "What is the budget for Project Elyra?"`. It may answer `Project Elyra budget: 615 Euro.` **only** after the existing real F1/F5 `verified_recall_messages` source admission and a second pre-egress check bind the exact source, query, session and message digest. No native inference, no synthetic authority.

## Frozen protocol

- One existing real Age0 home and session; no home creation, no model install/download, no new session, no concurrent runtime bypass. Use frozen `scripts/ask_verified_budget.BudgetContext` and `_preflight` unchanged, frozen `v13/source_consumer.py` `4b73842be25e784f70ade4f6c4ced3fe2dcb9eab`, `scripts/ask_verified_budget.py` `75ca7f3f197665f665d9582b7f5c2efb1f598235`, `v13/memory.py` `53dc948d0d360f94743ad996eb83ea0e85c2dd0b`, `v13/runtime.py` `68e7ed1352800174972558f1e0b0683a42c8689a`, `specs/models.json` `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7`.
- Fixed public synthetic source `Project Elyra budget = 615 Euro`, query `What is the budget for Project Elyra?`. Exact output `Project Elyra budget: 615 Euro.`, `mode=SOURCE_EXACT`, `status=FINAL`, `native_calls=0`, `model_called=false`, SourceRef and memory ID bound. **No model output is ever represented as a verified fact**.
- Missing, wrong project, out of scope, conflicting, revoked, tampered or cross-session sources refuse with no nonempty fact answer and zero native calls. A source revoked or changed between the first and second preflight must refuse before egress. The second source check is required even under the Store coordinator lock.
- Only explicit bounded project-budget grammar already supported by SourceConsumer; no general question answering, arbitrary external facts, new source authority or learning. No `:verified` semantics changed.
- New isolated `scripts/source_exact.py`, tests/docs/workflow only; focused/full suite, source/privacy/diff, closed raw hashes. No torch/native model weights in the runtime path (full software suite may install pinned CPU test dependencies as in Run91).

## Negative gates

A deterministic exact source answer is not C3 semantic quality, native generation, STEP2 complementarity, B3 receiver, Body-JEPA, LP3, Redmi, age promotion or whole-system completion. Age0 RECORD_ONLY, jepa_weight=0, no weight commits.