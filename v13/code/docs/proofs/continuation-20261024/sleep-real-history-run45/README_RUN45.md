# Run45 — exact upstream native_history + Run42 staging, synthetic Store

**Source identity:** The executed `vendor/v13/history.py` is byte-for-byte Git blob `05455f297205b40fe8e0f818c4657f1fedcd9fa3` from `v13/code/v13/history.py`. The executed Run42 staging module is byte-for-byte blob `8dcd4b36cbe58f06ea330a510f1735b37f0ad600`. Supporting `Store`, `output_policy`, `inputs` and `common` modules are **test stubs**, not production code. This is a stronger integration test than Run42's mocked history provider, but **not** a real Runtime/Store test.

**Tests 14/14 PASS:** valid pair, revoked target source, revoked prior context source, revoked transitive `context_source_refs`, removed fixed-answer rule, malformed/missing metadata, truncated history, stale export clearing, source hash mismatch, non-model-generated target, session isolation, deterministic repeat, dependency ref count. No sources or model weights written, no Age rights or factual authority.

**Evidence:** `evidence/run45-source-evidence.tar.xz.b64` decodes to source, stubs, tests, initial/final raw logs and hashes. Decoded archive SHA256 `8ee73582cdcee28cfdfdb3241c4f61d0c43c4d5d328c9fe5b5b775a27664733b`. Decode: `base64 -d evidence/run45-source-evidence.tar.xz.b64 > run45-source-evidence.tar.xz && tar -xJf run45-source-evidence.tar.xz`.

**Claim limits:** Synthetic Store does not exercise real SQLite transactions, `Store.read_source` range/hash semantics, live rule validation, runtime cancellation, native model generation or actual training consumer. The real `native_history` function itself was not modified. A previously exported candidate can become stale after later source deletion, so consumption must revalidate. No production wiring.

**Next:** In a full checkout, independently run these tests and replace fake Store with actual `Runtime` and `Store`, including transitive revocation and fixed-rule removal. Keep STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0 and full V13 INCOMPLETE until independent native proof.

**Ownership:** Codex Run45 owns only this folder. No changes to Run41 JEF, Run42 Sleep, Run43 Callosum, Run44 negative cohort, or frozen runtime.
