# Native retrieval source delivery audit

The preserved 2026-10-04 full acceptance result at
`docs/proofs/acceptance-current-20261004/memory-retrieval.json` is
`MEMORY_RETRIEVAL_PARTIAL`. The held-out source was `400 Euro` for the budget of
Projekt Kelmo16. The approved retrieval head admitted the exact correction with
probability 1.0. Both native language responses omitted the amount. The original
collector required B1 to use it; C3's failure was recorded only as an
informational observation. This historical failed evidence is retained.

`tests/integration_retrieval.py` now requires both existing native consumers to
include the expected amount in their actual FINAL model response. The existing
held-out source, corpus, partitions, numerical learning gates and native output
criterion are unchanged. No generated output becomes a human correction.

The collector observes `NativeRunner.generate` directly. It saves the exact
unmodified message list, its canonical JSON SHA-256, actual native role and
post-call metrics. The wrapper forwards the same message object, positional
arguments, keyword arguments and yielded tokens. It does not insert or alter
prompts, supply answer text, edit a source, or intercept model scoring.

For each of C3_LANGUAGE and B1_DETAIL it separately verifies:

- The structured correction contains the exact stored topic, `400 Euro` and
  matching raw query; an admitted memory ID alone is insufficient.
- The last user message equals the original query.
- Every durable `context_source_refs` entry remains readable, with both the
  exact query and correction represented by source text.
- The captured message hash matches, the actual native role matches, generation
  completes and native `history_trimmed` is false.
- The native FINAL model response satisfies the original expected-amount check.

Source delivery is a distinct claim from native answer quality. Correct delivery
can pass while a model still ignores context; that outcome remains a failed
native consumer check. A successful delivery audit is not evidence of general
factual reasoning, native body training, semantic truth learning or Redmi
performance. This Linux fixture does not substitute for a new phone run.

`tests/test_retrieval_capture.py` exercises observer transparency, exception
preservation, missing bindings, message tampering, prompt trimming, wrong native
roles and erased source lineage with synthetic fixtures. The saved log is
`docs/proofs/retrieval-capture-unit-20261007.log`; its four passing unit tests make
no native quality claim. Native rerun evidence must be saved separately, with
the current runtime and collector hashes.
