# World-Model observed ActionSelection binding — preregistration (2026-10-29)

Parent review-only PR #1143 at `38f21f2d201b742095343bac5150f6808773d21e`, based on PR #1141 World-Model operator and PR #1140 heldout baseline. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

## Actual source concern

`world_model.transitions()` currently selects the newest `ActionSelection` by `event_id` alone. A later packet for the same event can retroactively relabel an already finished action, even though its route was selected before dispatch. Multiple pre-dispatch selections also make the route ambiguous, but current code silently chooses the latest. Such unbound labels can contaminate the training targets and counterfactual coverage.

## Frozen software witnesses before source change

1. A valid `ActionSelection(simple)` before action dispatch yields one observed transition with `a=simple`. After the action has finished, append `ActionSelection(detail)` for the same event with `created > action.created`. The same action must remain `simple`, not be relabeled by the late packet.
2. If the event has *only* a post-dispatch `ActionSelection`, no observed transition is eligible.
3. If two distinct pre-dispatch `ActionSelection` packets exist for one event, no unique route can be proven, so the transition is excluded rather than choosing an arbitrary latest packet.
4. Original `test_world_model`, `test_worldmodel_operator_20261029`, `test_worldmodel_realstore_integration_20261029` remain green. No registered native cohort, model/seed/source pin, numeric target, fit objective, heldout split or threshold changes.

Implementation target: bind packet to the action's event generation and selection-before-dispatch timestamp, require exactly one qualifying packet and matching payload event/generation; reject ambiguous/unverifiable history. This is a conservative data-integrity gate for the existing own-digital World-Model, not proof of causal utility.

Tests are committed before source changes and expected RED on the parent. Linux SQLite software/synthetic only. No age/learning/phone/STEP2/B3/Body-JEPA/LP3/whole-system promotion.
