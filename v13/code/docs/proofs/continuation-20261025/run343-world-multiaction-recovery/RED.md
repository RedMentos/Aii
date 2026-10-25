# Run343 verified RED — before implementation

- Exact source branch head `f563c3ac6bdd18e71f5036e7332833a92168d493`.
- GitHub Actions `40222050645`, job `121255533829`: **FAILURE**, 31 tests, 3 failures, no errors.
- All 3 failures are new real SQLite/Runtime counterexamples:
  - `test_partial_crash_recovers_second_action_even_if_first_has_packet`: second completed action missing after restart.
  - `test_repeated_recovery_and_observe_are_idempotent`: recovered/materialized action count remains 1 rather than 2.
  - `test_two_observed_actions_same_event_are_counted_separately`: count 1 despite 2 action outcomes.
- Two new negative controls passed: unfinished second action not fabricated; distinct-event count unchanged. Existing World regression tests in the focused selection passed.
- Raw failed CI log and uploaded artifact preserved by workflow (artifact ID/hash to be recorded after upload terminal). No code patch yet, no World/JEPA/Redmi gate promotion.
- Next exact patch: in `v13/code/v13/world.py`, change recovery NOT EXISTS predicate from event-only to event+JSON action_id, and count distinct JSON action_id in materialized view. Keep all other source/action evidence and statuses unchanged.
