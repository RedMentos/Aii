# Independent Claude PR641 handover exact-once preregistration (2026-10-27)

Base: review child PR644 head `4abc439c12d38e7034a3506b40005248e685fb1f` on Claude PR641. Separate from Codex integration and concurrent C3 native owner. Files owned: `v13/code/v13/route_supersede.py`, new `tests/test_review_pr641_handover_once.py`, scoped proof/CI. Keep original route words, head weights, learned thresholds, user consent, Z6i/Z6i2 cohorts unchanged.

## Falsifiable defect
`route_supersede.observe` appends one head agreement on every call without deduplicating `event_id`. Re-entering the same request eight times (e.g. after retry or multiple routing paths) can satisfy `HANDOVER_N=8` with **one** actual source event, making the human rule eligible for handover prematurely.

## Pre-registered software tests
1. Repeating the same event eight times leaves **one** observation, not learned, handover refused.
2. Eight distinct source events with matching active head **do** satisfy the existing threshold, and explicit human handover still works.
3. A retry of the same event with a different head answer updates that event's observation; the last disagreement wins and no duplicate count.
Run existing `tests.test_route_words` and new tests on real SQLite Runtime, preserve original RED and GREEN raw CI logs. No native/Redmi evidence, no semantic utility or authority promotion. Negative STEP2/B3/Body-JEPA gates remain.
