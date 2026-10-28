# Run87 prereg — Age0 emergency-stop state through backup and offline restore (2026-10-29)

Owner GPT-6 scheduled continuation. Independent review-only child of **GREEN** Run83 #990 exact `3545dab0faa3d548df58557ed8376a6162c51d9a`, Actions 40783355033 SUCCESS, which includes Run82. Disjoint from Run86 #993 (RED-first paused-preflight diagnostic under correction); this branch does **not** import Run86 or change its original evidence. No native models, new training, production source edits or user data.

## Frozen real software E2E test
1. In a fresh Linux temporary home instantiate real Runtime/Store/Operator, disable Sleep, keep Age0 RECORD_ONLY, create one explicitly human-recorded Project Elyra budget fact, and verify source preflight READY before stop (zero native calls).
2. Engage `:stillstand` and require confirmed idle, NOTAUS, queue pause and Age freeze. While paused, `:verified` must fail closed with RUNTIME_NOT_IDLE (source-code guard `ask_verified_budget._age0_only`; separately discovered in original Run86 RED Actions 40784995222). No native model call.
3. Human-typed `:backup` while the coordinator is paused must produce a valid archive with a manifest, member SHA256s and models_included=false. Backup is a user-requested local snapshot, not autonomous work.
4. Close Runtime. Offline `backup.restore(home, archive)` must create a safety backup; reopen same home. The restored emergency stop must remain ON with all three parts stopped; source memory must remain recorded and `:verified` must still refuse during pause.
5. Explicitly release `:stillstand aus`. Only now `:verified` must return READY with original source id and zero native calls. Reopen once more to confirm release and source durability.
6. Run exact source/hash-bound focused tests (including Run82/83 and standstill), full suite, compile, privacy/diff and closed raw SHA256SUMS. Keep all original RED, including Run86's, and any new RED. No threshold edits or silent retry.

This is Linux software persistence/safety evidence, **not** a Redmi/native test or semantic-learning proof. Keep STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA unavailable, LP3/jepa_weight=0 and whole-system incomplete. Do not merge into production main automatically.
