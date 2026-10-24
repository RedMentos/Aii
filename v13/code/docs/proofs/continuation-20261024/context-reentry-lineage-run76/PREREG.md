# Run76 prereg — Context OS append-only source lineage

2026-10-24. Base Run75 PR108 `be84e884f0bcbd049e317c178f9511cf08da3dbc`.
Owner: `v13/code/v13/context_os.py`, `v13/code/tests/test_context_append_provenance_run74.py`, and new `v13/code/docs/proofs/continuation-20261024/context-reentry-lineage-run76/**`. Do not change CI workflow or other active owners' files.

Problem: append-only re-entry currently compares only the last turn's visible user text and assistant role. If earlier retained history or a source reference changes without changing that final text, it may reuse an obsolete recurrent prompt. A latest event containing extra messages may also pass. Native history source validity is independently checked by `history.native_history`, but Context OS must not reenter a transcript with a different history identity.

Test-first expected RED: changing earlier text, earlier source metadata, latest user source reference, or adding a third message to the last event must block `append_reentry`; valid active multi-turn history must still append. Existing SHADOW behavior, exact pin, legacy fallback and original gates unchanged.

Implementation proposal: store a deterministic digest of the full prior history row sequence and the current query SourceRef digest, without copying source text into state. Before reentry compare the earlier rows byte-exact and require exactly one user/assistant pair in the latest event; match the previous query SourceRef against the latest user metadata when a source ref was provided. Legacy transcript state lacking new bindings fails closed to rebuild.

Evidence: first red GitHub-hosted Linux CI, then green; run `python -m unittest -v tests.test_context_append_provenance_run74` via existing read-only focused CI plus official privacy scan. No model download, no native or Redmi claim. Keep raw failing logs and exact CI run IDs. Do not promote STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0 or full V13 INCOMPLETE.
