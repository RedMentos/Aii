# Run70 prereg — World Model action-selection chronology

2026-10-24. Base Run69 PR102 672858e8156bd11c9f3409d351fd9286f4a67393. Ownership: only `v13/code/v13/world_model.py` transitions ActionSelection lookup and new tests/evidence. Do not modify JEF Run68/69, original blueprint, training cohorts, model hashes, Age/approval or World Model objective.

Hypothesis: `transitions` currently uses the latest ActionSelection for an event even when it occurred AFTER the action being scored. Multiple actions/selections in one event can therefore silently relabel an earlier action with a future route, corrupting World Model (s,a)->y training. Test real SQLite with two selections/actions, no preceding selection, equal-timestamp ties, unrelated event. Fix only selects the latest same-event ActionSelection with `created<=action.created`, ties ordered deterministically by `created DESC,rowid DESC`. No future lookahead or fabricated action.

Use SQLite official SELECT ORDER BY semantics https://www.sqlite.org/lang_select.html. Preserve original negative gates and claim only software/synthetic until actual Store/native/Redmi proof.
