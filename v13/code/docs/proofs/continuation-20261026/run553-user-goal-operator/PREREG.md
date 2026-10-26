# Run553 prereg — usable explicit USER goal lifecycle in persistent Termux chat

2026-10-26, committed before source changes. Base Run552 PR #551 current verified head `62904a658e238a44c3b56477d380d42d68d21bbb`, source-only 64/64 and source-bound general Actions PASS on exact earlier Run552 code, raw backed up privately. This is a separate functional user-interface package, not a retroactive Run552 change.

## Observed functional gap

JEF/AG3 persists USER goals, but `:growth goal <Title>` only adds and `:growth goals` only lists. A user cannot explicitly mark a goal DONE, abandon it, or reopen it from the chat despite `GoalStore.set_status` supporting all three. Run552 improves receipt-bound automatic closure but a delivered FINAL answer does not prove semantic success. The user must be able to correct the goal lifecycle without editing SQLite or waiting for a TTL.

## Change and authority

Extend the existing typed operator path `:growth goal status <goal_id>`, `:growth goal done <goal_id>`, `:growth goal abandon <goal_id>`, `:growth goal reopen <goal_id>`. Mutations only for goals whose `origin=='USER'`, only from the operator's explicitly typed `:growth` command, never from model text, scheduler or automatic learning. Preserve `:growth goal <Title>` and `:growth goals`. Reject unknown IDs, malformed arity and any SYSTEM/SELF goal mutation. Keep status transitions conservative: done/abandon only for open/active/blocked USER goals; reopen only from DONE/ABANDONED; redundant actions return current status without adding false evidence. Preserve notes/history and restart. No new Age rights, tool grants, background dispatch, model/seed/cohort changes.

## Acceptance

Source-only Runtime/Store/Operator tests: create via existing command, list/status, done, restart persistence, reopen, abandon, idempotent retries, malformed IDs/arity, SELF/SYSTEM refusal, and prove untyped assistant output does not invoke the command. Existing World/JEF goal tests and Run551/552 regressions PASS. Exact-head Actions pinned source/Canon checks, privacy CLEAN, SHA-closed raw (retain failures), independent review. No Redmi/native/semantic success claim. STEP2/B3/Body-JEPA/jepa_weight/whole-system gates unchanged.

Next: practical phone workflow and actual STEP2/JEPA utility evidence, not additional unmeasured scaffolding.
