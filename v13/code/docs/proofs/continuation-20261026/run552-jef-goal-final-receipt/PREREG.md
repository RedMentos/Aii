# Run552 prereg — JEF open-goal completion needs an actual FINAL answer receipt

2026-10-26 before source changes. Exact base Run551 PR #550 reviewed head `d22f07fcbc09c89143c6aa27ae1a6d1d176047be`, Run551 50/50 source tests + focused source-bound workflow PASS, privacy CLEAN, original raw evidence preserved in private Library. Separate package; Run551 tests/source remain unchanged.

## Concrete functional mismatch

`agi.live.goal_turn` currently marks an existing unresolved USER goal DONE when called with `status='FINAL'` on a later similar user text, without checking whether an assistant FINAL message was ever stored. The `tests/test_world_model.py` fixture explicitly exploits that shortcut: it calls `goal_turn(...,'FINAL')` with no assistant message. A crash/recovery race, caller bug or synthetic status can therefore falsely report a user goal as accomplished. Status and topic similarity alone are not delivered work.

## Minimal canonical repair

Retain current conservative lexical relevance and automatic same-topic closure only when the new event has a persisted, nonblank, same-session assistant `FINAL` message. The receipt is checked read-only from Store; do not treat a DRAFT, ERROR, CANCELLED, DEADLINE, other session's message, or empty FINAL as completion. A `FINAL` with no qualifying answer is unresolved and should open a goal if it has none. Existing explicit USER goals, scheduler, Age rights, sources, native models, memory, STEP2/B3 and permissions unchanged. This is necessary but not sufficient for semantic task completion: delivered text can still be incorrect; no truth/utility promotion.

## Test plan / counterexamples

Modify the original LiveGoals fixture to create a real finalized assistant message before expecting DONE. Add model-free SQLite tests for fake FINAL with no message, blank FINAL, non-FINAL message, cross-session mismatch, same-topic real FINAL, unrelated real FINAL, restart persistence and no duplicate goal for same event. Verify no auto-completion when C5 selected CLARIFY or `meta.clarify.apply`. Existing JEF/World/AG9/Run551 regressions must pass. Exact-head GitHub Actions tests and public privacy scan, SHA-closed raw including RED, independent reviewer. No real native inference/Redmi, no claim of improved semantic goal resolution.

Negative gates: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; Redmi unmeasured; full V13 incomplete. Next: measured end-to-end goal utility and remaining JEPA/body execution work, not endless guard refinements.
