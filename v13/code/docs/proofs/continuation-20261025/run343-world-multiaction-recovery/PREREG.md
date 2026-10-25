# Run343 prereg — WorldState multi-action crash recovery and action count (2026-10-25)

Base exact verified Run342 checkpoint `da6042dccf7c3a3c08f591165b7d094793b6d230` (includes latest Run340 owner seam). This independent package owns only `v13/code/v13/world.py`, new Run343 tests/workflow/proofs. No frozen SourceHandoff Runtime, Canon, model/source/cohort hashes, learning/age/approval, native jobs or current gates are modified.

## Concrete source bug, not a hypothetical new feature
Production `Store.start_action` permits multiple distinct C5 action IDs for one EventEnvelope. `WorldState.observe(aid)` writes `PredictionOutcome` per **action_id**. But `WorldState.recover()` excludes a pending action if **any** PredictionOutcome already exists for its event, so a crash after recording the first of two actions leaves the second never recovered. `WorldState._refresh()` counts distinct **event_id**, even though it calls the field `observed_action_count`; multiple observed actions within one event are undercounted. Both violate durable per-action World-state continuity and make world evidence incomplete.

## Frozen acceptance before code
- Real Runtime + Store SQLite with one real user event and two distinct `start_action`/`finish_action` outcomes, no mocked database. Observe first action, close/restart, call `recover()`; must persist second PredictionOutcome exactly once and `observed_action_count==2`.
- Repeat `recover()` and `observe()`: no duplicate packets, count unchanged, source provenance remains readable, integrity check clean.
- A single event with two observed actions must report count 2, not 1; two separate events still report 2. No status promotion from unfinished DISPATCHED/no outcome or corrupted source.
- RED-first source-only test on current code, preserve failure; smallest SQL correction using action ID in NOT EXISTS and distinct observed action IDs in materialized view. No fabricated actions or outputs.
- Run focused World/Runtime/Store regression suite, privacy scan, closed raw hashes and exact remote byte verification. No native model, Redmi or semantic-world learning claim. `G-SELF-WORLD-005` and full V13 remain open.

Next: add adversarial tests/workflow, execute exact-head RED, patch, rerun GREEN, checkpoint, independent review, continue another package.