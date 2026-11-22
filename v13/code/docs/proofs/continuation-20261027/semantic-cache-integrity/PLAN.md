# STEP3 semantic embedding cache integrity — preregistered review

Date 2026-10-27 UTC; owner GPT-6 continuation. Review-only child of PR #740 exact `130083fa8fcd7b5ee0cd81635d654da0e4927cfe`; current `semantic_memory.py` blob `a7c22c6775b67db6ab06aa07c6f4ab3b43706988`. SSOT and pinned EmbeddingGemma model/source/seed hashes unchanged.

## Defect and expected RED

`SemanticKeys.similarities` accepts any persisted list of the configured length as a cached embedding. It does not validate numeric type, finite values or the required unit norm from `truncate`. An otherwise valid SQLite cache state such as `[1000000.0]*dim` (finite JSON) is accepted, and `cosine` clamps its huge dot product to 1.0. A completely unrelated query can then receive maximum semantic similarity without any encoder call. This is a relevance/provenance integrity failure in the STEP3 retrieval channel, not a model-quality claim.

Preregister a real Runtime/Store synthetic test: create a human-approved memory, persist an oversized finite vector under its exact cache key, call `similarities` with an unrelated query and the real memory row; assert invalid cache is re-encoded and similarity is low. Existing code should FAIL. Also check malformed bool/nonfinite vector rejection and safe cosine dimensions/finite results without changing model weights.

## Proposed GREEN

Only reuse persisted cached vectors if they have the configured length, real finite numeric entries (not bool), and squared L2 norm within a conservative tolerance of 1 (the cache stores 6-decimal rounded normalized values). Otherwise treat the key as missing, re-embed from source key text under the existing cap/deadline; if encoder unavailable, fail closed via existing fallback rather than use a false high similarity. Make `cosine` reject mismatched dimensions/nonfinite dot products rather than clamp them into apparently valid similarity. No authority upgrade, no cache schema change or source rewrite; preserve existing valid caches and all explicit negative gates.

## Verification

Focused `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_semantic_memory`, compile, exact-parent privacy/diff, raw artifacts for RED and GREEN. Full software suite on latest exact source, no native/Redmi or learned semantic-quality claim. Preserve failed attempts; no main merge without independent review.
