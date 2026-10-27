# C1/JEF goal-sequence event provenance — preregistration (2026-10-27)

Review-only child of PR #776 exact parent `1d0ab1ca8cf64f7d2d4f9e313ca39e87bf2370c5`; NOT main, not production-integrated. Owner: independent GPT review, files exclusively `v13/code/v13/executive.py`, new `tests/test_executive_goal_sequence_binding_review.py`, dedicated CI and coordination evidence. Preserve every canonical V13 organ, model/seed/cohort, SourceHandoff frozen gate and original failed attempts.

## Falsifiable risk

`Executive._clean` filters persisted `goal_sequence` only by whether each `source_ref` is a valid immutable source. It does not verify the sequence item's `event_id` actually belongs to this session or that the event's authoritative `source_ref` matches. `effort_context` turns those unchecked entries into `prior_goals` read by the reasoning-effort policy. A single persisted C1 state corruption can therefore inject a cross-session valid source or falsely attach a source to another event. A hash-valid source alone is not sufficient authority.

## RED cases before source change

1. Cross-session valid event/source inserted into a second session's `goal_sequence` must be dropped from `view` and absent from `effort_context`.
2. Same-session event ID paired with a different valid source must be dropped, not attributed to that event.
3. Missing/fabricated event ID with a valid source must be dropped.
4. Positive control: two genuine authoritative same-session events retain exact goal sequence and prior goal text; current goal excluded from `prior_goals`.

## GREEN contract

Only retain `goal_sequence` items whose event exists, belongs to the current session, is authoritative and has the exact same `source_ref` as the item; fail closed for malformed values without changing unrelated task, action, model or learning logic. Run RED-focused before source edit, then GREEN-focused and full source-wide software suite; preserve raw test/compile/privacy/diff exit evidence. No native/Redmi claim, no Age/STEP2/B3/Body-JEPA/LP1/LP2/BJ1/jepa_weight promotion, no production merge. Independent review required.