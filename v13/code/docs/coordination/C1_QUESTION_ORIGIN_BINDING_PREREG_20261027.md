# C1/JEF unresolved-question source binding — prereg (2026-10-27)

Review-only child of C1 goal-sequence review branch at exact parent `b29c0436e5c39c2bda9ab6711b1437725a6c110f`; upstream PR #776, NOT main or production. File ownership: `v13/code/v13/executive.py`, new `tests/test_executive_question_origin_binding_review.py`, dedicated CI, coordination evidence only. All model/source cohorts, Canon and negative gates unchanged.

## Falsifiable source-integrity risk

`Executive._question_valid` currently checks a hash-valid `open_questions[].source_ref` and a stored `OfferPacket` from the same session, but does **not** require that the question source equals the offer's originating authoritative event source. A forged persisted C1 question can pair a real offer with a valid source from another session (or another event) and pass into `report_context.unresolved_observer_hypotheses[].source_request`. This launders unrelated source text as an unresolved observer question.

## RED before implementation

1. A real same-session offer with `needs_reentry=true` cannot authorize a question whose source is a valid event in a different session.
2. Same-session valid source from a different event cannot be substituted for the offer's originating event source.
3. A question cannot attach a current event source to a genuine older offer from the same session.
4. Positive: a genuine `Executive.update(offers=[offer])` question remains valid across a subsequent user turn, with original source/uncertainty, no new authority.

## GREEN

Require the question's exact source_ref to match the stored authoritative event for the referenced offer, with session/event binding. Preserve legitimate earlier unresolved questions across turns. Reject malformed packets/state fail-closed, no new tool, model, memory, age, learning or output authority. Capture RED focused then GREEN focused and source-wide software evidence, raw exits, privacy/diff. No native/Redmi or JEPA/STEP2/B3/LP1/LP2/BJ1 promotion; jepa_weight0 and age_authority0. Independent review, no auto-merge.
