# Run301 — WorldModel held-out split must not share the same user event

Owner GPT-6 automation. Base Run300 remote head `5f4e6f7d0735a97aca1f1d3165666307ef5200e3` / PR #299. Owned: `v13/code/v13/world_model.py`, new `v13/code/tests/test_world_event_group_holdout_run301.py`, `.github/workflows/run301-world-event-holdout.yml`, this proof directory. No edits to active native owner or frozen Runtime/Store.

## Hypothesis
`WorldModel.fit()` uses a deterministic index-level 1-in-4 holdout. Multiple own actions derived from the *same* USER_TEXT event can be split across train and heldout, inflating prediction metrics via event-level leakage. A model's held-out metrics must be independent at least at the source-event level; this does not prove external causal generalization.

## Preregistered RED/GREEN controls
1. Pure deterministic `_split` control: 24 rows, 12 event groups repeated twice. No group may appear on both sides; both train and heldout nonempty. With 24 unique groups, the new split must exactly match the old index-hash split (no registered unique-event cohort change).
2. Actual production Runtime/Store SQLite: 24 valid source-grounded actions from 12 distinct user events (two actions per event) with action selections bound to chronology. `transitions` preserves each event id; `fit` reports `group_split=EVENT_DISJOINT`, train/heldout group counts, and a disjointness flag, while keeping source bindings valid after restart.
3. If 24 observations all belong to one event, refuse fitted heldout metrics with `INSUFFICIENT_INDEPENDENT_GROUPS`; do not promote a synthetic or in-sample score. Failed/cancelled action status/source checks from Run298 remain unchanged.
4. Existing WorldModel, source-lineage, chronology, confidence/abstention and Run298 terminal-outcome tests remain green. Official privacy scan CLEAN. RED raw artifacts and final GREEN logs retained.

## Scope
Software/actual SQLite with synthetic action timings; no native model or Redmi, no causal/world utility proof, no STEP2/B3/Body-JEPA promotion. Do not alter Canon, registered model/seed/source hashes, current WorldModel revision or existing persisted model bytes. This changes only how **new** multi-action-per-event fits choose held-out examples; unique-event fits preserve the previous deterministic split exactly. If an independent holdout is impossible, fail closed.

Next after GREEN: independent review of grouping keys and restart, durable checkpoint, then another distinct canonical package.
