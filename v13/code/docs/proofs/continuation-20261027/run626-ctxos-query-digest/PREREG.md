# Run626 prereg — opt-in query-conditioned, source-valid Context OS Sleep A digest

2026-10-27 UTC. Parent Run625 PR620 head `551e18be6948bdb849d6c1532c138a1c4f576d2c`, descendant of Run624/Run623. Exclusive files: `v13/code/v13/sleep_offline.py`, `v13/code/v13/context_os.py`, `v13/code/v13/runtime.py`, new `tests/test_run626_ctxos_query_digest.py`, Run626 workflow/proof. No edits to Canon, models, frozen cohorts, source/seed hashes, learning/age rights or other owners' files.

## Actual gap

Existing Context OS `COMPRESSED` live layer appends the most recent source-validated digest entries until its character cap. An older source-valid fact can be excluded even when the current user asks specifically about it, while irrelevant recent digest entries occupy the budget. A query-conditioned *lexical* selection is a small deterministic, source-grounded consumer, not a learned semantic retriever. Default current measured `recent` behavior must remain byte-identical.

## Frozen tests and comparison

- Keep `context_items(store,session,exclude_ids,cap)` exact behavior when selection omitted; `digest_selection=recent` default, persisted and visible via `:ctxos status`. Explicit local `:ctxos digest select query|recent` only at idle; invalid values and busy turn fail atomically.
- With a fixed small cap and >=12 source-valid FINAL turns, query a topic from the **oldest** digest entry. Baseline `recent` misses it; opt-in `query` returns the exact source-derived line while not selecting unrelated newer lines. Test no-match fallback, stable tie order, cap, restart, multi-session isolation and source deletion/revocation.
- Actual mocked-C3 Runtime turn must include the selected older digest in its COMPRESSED layer, not only a unit function; source/answer authority stays zero, no tool/weight/age promotion.
- The ranking uses the existing deterministic `memory.relevance` lexical/term/explicit-entity check, with no native embeddings or network. No unmeasured answer-quality claim. Keep recent mode exact, and all existing Run609/610/612/624, `test_sleep_offline`, `test_context_os` focused regressions green.
- Record original exact-parent RED against new test, patched GREEN, source/Canon hashes, privacy, raw evidence and private byte-verified backup. Scope is **Linux SQLite/software lexical source selection**, not STEP2, JEPA or Redmi proof.

No production default switch, no activation of unapproved tools, and negative gates remain STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, jepa_weight 0, V13 incomplete.
