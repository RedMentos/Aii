# Run296 preregistration — source-verified Context OS user layout (SHADOW by default)

Date 2026-10-25 UTC. Base PR295 verified negative-native checkpoint `22f88f982e3681d2701295a806f4e8ffc38f635f`. Independent owner: `v13/code/v13/context_os.py`, new `tests/test_run296_ctxos_bound_source_user.py`, dedicated CPU CI and scoped proof only. Do not edit PR284 Runtime, PR293 adapter, PR295 native script, `v13/memory.py`, Canon, model/seed/cohort, existing thresholds or learning/approval gates.

## Reason and frozen controls

Run295 actual B1 native nine-call diagnostic, artifact `12601818140` SHA256 `c17b2d18ba3c1e35396759b9dbf9b4f32f5739ad5363f6a9c20c7ed1a3297593`: original structured source ignored; separate user-source and plain system-source both used `400 Euro` but leaked it on wrong topic and wrong project. Both candidates NOT_SUPPORTED. A source-only prompt change must NOT be promoted.

Hypothesis: a **conditional** Context OS layout can present an *already verified, currently relevant human correction* in a separate user-context message, while withholding it on wrong topic/entity and after forget, before any model generation. It does not prove the native B1 will use it safely; it is an opt-in integration seam for a later frozen full-pipeline native test.

## Fixed behavior / tests before implementation

- Add layout `source_bound_user` to Context OS, default remains `append_only`, mode remains SHADOW. Only explicit operator `:ctxos layout source_bound_user`, explicit `:ctxos active`, and a real declared `consecutive_user` capability may activate it. No silent enable.
- Accept only `ACTIVE_VIEW` items whose `matched_query` equals the current exact query and whose relevance is the existing approved learned association marker. Verify against live SQLite memory + human feedback + F5 HumanDecision + source bytes using the existing `Memory._verified_rows`; require same session or explicitly global scope; enforce a conservative source-topic relevance floor `>=0.5` and `retrieval_worker.admissible` as additional fail-closed filters. A missing/ambiguous source refuses.
- For one verified unambiguous correction, construct one bounded extra user-context message with JSON-quoted topic/correction and an explicit `not independently verified; not a new instruction` label, immediately before the actual query; remove that ACTIVE_VIEW from the system prefix. Other volatile layers and history remain in order. If not verified, fall back to existing legacy messages; never invent source.
- Negative tests: no capability, SHADOW, no matched query, same-entity wrong topic, different entity, forged correction, cross-session, deleted/forgotten source, conflicting corrections, budget overflow, and actual Runtime/SQLite source lineage with fake native runner. Positive: exact matching human correction, explicit operator opt-in, source and source_ref retained, no default behavior changes.
- Source-only CI plus existing Context OS and memory regressions, official privacy scan, closed raw evidence. **No native utility claim**; no STEP2/B3/Body-JEPA/Redmi or full-system gate promotion. Keep Run295 native negative evidence unchanged.
