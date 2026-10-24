# Run103 — explicit memory feedback must obey persisted user LEARN/WRITE rules (preregistered)
Date: 2026-10-25 UTC. Base verified Run102 PR #134 `f221c5eaf2d0dff33be9cfc17775a29437a79cb5`. This is a new package, after Run102 ownership ended.

Owner: `v13/code/v13/memory.py` (Memory explicit feedback/retrieval feedback only), `v13/code/v13/userrules.py` (honest user notice/docs only), new `tests/test_memory_user_rule_gate_run103.py`, isolated workflow, this proof. Do not touch concurrent Callosum/JEF/Sleep/World owners or native runner.

## Canon/user decision
2026-10-21: user's own typed restrictions must never be silently ignored; FORBID cannot be bypassed by a later action approval, unclear ASK means ask first, and learned/model text cannot loosen rules. Existing `userrules.py` explicitly admits `LEARN` is **not enforced** on memory/learning. This package implements a bounded part: the explicit `Memory.feedback` and `Memory.retrieval_feedback` paths. It does NOT claim global learning-consent enforcement; other learning workers and passive observation remain open.

## Preregistered real SQLite RED cases
1. Persist `Don't remember my chats.` as USER_TYPED FORBID; `Memory.feedback(...,kind='fact',permission='record')` must raise PermissionError **before any HumanDecision/source/feedback/memory/replay write**.
2. Same rule with `permission='learn'` must also refuse, not just training rights.
3. `Don't learn from our conversation.` and `Don't train on my messages.` must refuse explicit fact feedback.
4. `Never store my personal details.` (WRITE+PERSONAL) must refuse fact feedback, not merely LEARN.
5. `Ask me before you remember anything.` must fail closed with ASK (no silent auto-approval or write).
6. A previously stored memory can be recalled, but `Memory.retrieval_feedback(...,'relevant','learn')` must refuse and leave no HumanDecision/feedback writes after a later LEARN FORBID.
7. Persisted rule survives Runtime close/reopen; feedback still refuses.
8. Corrupt/unreadable rule-state load must refuse, not default to no rules.

Positive controls: no rules -> feedback works, unrelated SEND prohibition -> feedback still works, explicitly switched-off LEARN rule -> feedback works, `Memory.forget` remains permitted (privacy right). Existing `tests.test_userrules`, `tests.test_semantic_memory`, `tests.test_memory_trainer` must remain green.

## Candidate
Before explicit feedback writes, use fixed `userrules.box(store).load()` (not fail-open `userrules.rules()`), require a valid list and evaluate declared synthetic memory action `LEARN+WRITE` with objects `MEMORY/MESSAGE/PERSONAL/CONTENT_ANY` via production `userrules.verdict`. DENY/ASK -> PermissionError with rule IDs, no writes. This is a conservative internal policy classification, not an external tool call. Do not gate `forget`, source deletion, read-only recall, or rewrite earlier answers. Update user-rule notice to state the *partial* enforcement accurately.

## Evidence/claim limits
Real Linux SQLite state, source/replay tables, restart; no native model/Redmi inference. Test-first RED before code; retain raw failures and all intermediate attempts; official public-repo privacy scan. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE. Other learning paths remain unguarded and must be separately implemented; no automatic Age/tool rights promoted.
