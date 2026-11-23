# V13 Run11 — semantic cache forget-vs-encoder atomicity prereg (2026-10-28)

**Owner:** isolated review child of PR #920 at exact `17a1a4d24b9a565531e331ee393210e3a8cae5ff`, itself review-only from #919. Do not overwrite parent, other owners, frozen Runtime, registered models, cohort, seeds, or main.

## Source-level counterexample and functional requirement
`v13/code/v13/semantic_memory.py` `SemanticKeys.similarities` gathers active correction rows, calls an optional potentially slow embedding encoder, then unconditionally writes each new `memory-embed:<source_id>...` state. A concurrent `:forget` can delete the source and cache **during the encoder call**, after which the returning encoder can recreate the deleted vector state. `Memory.recall` may then raise `Dangling/gelöschter SourceRef` while ranking a stale row. This is a source-level defect hypothesis, not yet a measured runtime RED.

## Frozen behavioral contract and tests
- Use the existing Store SQLite transaction/mutex to validate **live memory + source** and publish a new cache vector in one transaction. If `:forget` wins first, do not recreate cache; if the encoder wins first, `:forget` deletes cache later. Also exclude now-revoked cached vectors from similarity results and clear the last query vector if nothing live remains.
- Preserve the existing source-backed answer-only policy: embeddings are relevance keys, never values or user decisions. `Memory.recall` must quietly drop a row that became deleted during the encoder, but must **not** suppress a live-source hash/provenance mismatch.
- Pre-registered synthetic interleaving tests using real Store SQLite + deterministic fake encoder callback: forget during new-key encode; forget during cached-key query encode; stale direct-call row after forget; one revoked and one live row in the same batch; live corruption still fail-closed; ordinary caching still works. No model inference, no claim of quality or unlearning weights.
- Source-pinned Linux software CI: focused memory tests, full suite, compile, official privacy/diff; retain raw log, stage exits and hashes. Separate concurrency group, no native/model job. Preserve any RED.

## Acceptance and non-promotion
No resurrected `memory-embed:` state after completed `:forget`, no forgotten correction returned, no stale `last_query` authority, live source integrity failures still explicit. All original negative gates unchanged: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, Redmi unmeasured, whole-system incomplete. Do not mark whole V13 or source revocation across every organ complete.

## Next commands
`cd v13/code && PYTHONPATH=.:tests python3 -m unittest -v tests.test_semantic_memory tests.test_semantic_forget_encoder_race_20261028 && PYTHONPATH=.:tests python3 -m unittest discover -s tests -p 'test_*.py' -q`. Follow original Actions artifact audit and next independent Canon package. Remaining platform budget UNKNOWN.
