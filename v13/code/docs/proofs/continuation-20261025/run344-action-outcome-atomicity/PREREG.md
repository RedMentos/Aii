# Run344 prereg — C5 ActionOutcome atomic persistence and exact replay (2026-10-25)

Base: Run343 verified checkpoint `e0f8ff1c5329e2f57ea52c6230489ea26ee5ccc3` (Run342 + Run340 included). Ownership: `v13/code/v13/store.py`, new Run344 tests/workflow/proofs only. Do not edit frozen SourceHandoff Runtime, Canon, model/source/cohort hashes, age/approval rights, native experiment owners or negative gates.

## Observed defect
Production `Store.finish_action` unconditionally inserts an `ActionOutcome` packet in one SQLite transaction, then updates `actions.status/outcome` in another. A crash or injected SQL failure between commits leaves a durable packet claiming a terminal result while the action is still DISPATCHED. Repeating `finish_action` for an already completed action can overwrite the action's original outcome/status and add a second contradictory `ActionOutcome` packet. `WorldState.observe` may then return a stale earlier observation for the same action. This violates exact outcome provenance, crash consistency and fail-closed replay.

## Predeclared acceptance
- Use real Runtime/Store SQLite and a real EventEnvelope, with synthetic local action outcomes (no native inference). Finish an action once: exactly one terminal action row and one bound ActionOutcome packet.
- Same exact outcome replay, including after restart and concurrent calls, is idempotent: no second packet and no change in original status/outcome bytes.
- Different status or actual outcome replay is rejected, original action+packet remain byte-identical.
- Inject SQLite UPDATE failure *after* packet INSERT inside a transaction; verify rollback leaves DISPATCHED/outcome=NULL and no ActionOutcome packet, then retry successfully.
- Unknown action ID and malformed outcome fail closed without packet creation.
- Existing C5/World/Store source-only regressions remain green. Original terminal statuses and allowed initial transitions preserved; no new action permission.
- RED-first test, raw failed evidence saved; smallest transactional implementation; exact-head GREEN, independent raw hash verification, private Library backup, branch-scoped checkpoint. No STEP2/B3/World-JEPA/AG6/Redmi/V13 completion claim.

Next: add test and exact-head workflow; preserve RED; implement one-transaction finalization with a strict same-outcome replay check; rerun and independently review.
