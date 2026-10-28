# Run82 prereg — Age0 operator source-backed lifecycle without models (2026-10-28)

Owner GPT-6 scheduled continuation; review-only independent sibling of Run77-81, based on exact independently raw-audited Run76 #983 GREEN head `2fa443822f99b367d137f0254e69e20268f664e8`. No source or native/model changes. Scope: **real Python Runtime + Store + Operator on Linux temporary home**, not mock Runtime, no model download, no LFM/Needle native calls, no Redmi.

## Frozen test plan before code

1. Construct real `Runtime(tempdir)`, disable Sleep background cycle, use real `Operator`; capture `:status` and require `learning == RECORD_ONLY` with valid session, `:help` contains required operator commands, `:chats` includes the active session.
2. Add one exact human-provided fact through the existing `Store.event` + `Memory.feedback(... permission='record')` path. Use `:verified What is the budget for Project Elyra?` (F1/F5 source-only preflight) and require READY, exact memory id, no answer generation, no native calls. Explicitly patch `pool.get` to fail if native is attempted.
3. `:export chat json` writes only under temporary home exports and parses as JSON. `:new` creates another session, `:open <old>` restores original, and `:status` reflects it. Unknown session must fail.
4. Close real Runtime, reopen same home, require persisted original session, source-bound `:verified` still READY, and no model access. `:forget <id>` without `--confirm` must refuse; with `--confirm` removes fact; `:verified` must then CLARIFY (no stale source answer). Reopen again and confirm deletion persists.
5. No calls to `:learning commit`, age promotion, tools, native models or external network. The test is software lifecycle proof only, not native output, user-facing quality, C3/B1/B2/JEPA/Redmi or complete blueprint.
6. CI pinned source/tests and exact Run76 parent, focused new E2E + verified preflight + runtime queue tests, full software suite, privacy and original closed raw SHA256SUMS. Preserve any RED, no threshold tuning posthoc.

Next if GREEN: independent review of source-linked operator lifecycle and native/Redmi acceptance separately. All original Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, whole-system incomplete remain.
