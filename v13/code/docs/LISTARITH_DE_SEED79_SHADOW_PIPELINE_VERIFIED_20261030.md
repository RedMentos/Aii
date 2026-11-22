# German typed-list arithmetic SHADOW candidate — verified source-only checkpoint (2026-10-30)

Review-only child of #1220, base `542c8c426f4ff15dd5b26d94dd89152fe60d9dbc`. Original C3 native raw separately verified in `C3_DE79_INDEPENDENT_NATIVE_REVIEW_20261030.md`. No original model, seed79 fixture, native harness, seed73 classifier, English tool, runtime, C5/ToolStep, age or learning modification.

## Candidate
- New `v13/agi/listarith_de_shadow_pipeline.py`: accepts **caller-supplied** C3 typed JSON and the existing seed73 v2 German question proposal; rejects duplicate JSON keys, invalid schema, aggregates, unsupported/meta/negated questions, missing or mismatched source name-to-number adjacency, reused source spans, invented numbers. Computes with unchanged `listarith.compute` only after all guards. Returns explicit `SHADOW_RESULT` or `SHADOW_ABSTAIN`, never live action authority.
- New 20 adversarial source-only tests: total, difference, dates, multiline, signed values, repeated names, wrong header labels, number/name inventions, source span reuse, aggregate claims, duplicate JSON keys, invalid numeric types and all negative gates. No model call in tests.
- First CI Actions `41012425616` **RED**: 4/20 tests failed because source-span regex incorrectly rejected comma/period list separators; original raw preserved. Corrected only candidate regex to reject decimal continuations but permit separators.
- **Exact-source GREEN** Actions `41012468843` at head `dae5ce1b196143bfc52c0baacfc7298b84737ffe`: 20/20 PASS, Python compile PASS, privacy CLEAN, diff PASS, 4/4 stage exits0. Original artifact `12958366032`, ZIP SHA256 **`64924ab49da530107da09d391d47c849d00bb0a5dea3bb382347dca73a36ce45`**, CRC clean, **10/10 inner SHA256SUMS**.
- **No end-to-end native pipeline result yet** at this checkpoint: native seed79 C3 outputs exist (11/12 exact extraction), but this new candidate has only synthetic software tests. Do not infer production utility or German generalization.

## Next
Build a **read-only posthoc replay** of the original immutable seed79 native ZIP through the new pipeline. Bind ZIP SHA256, CRC, all inner hashes, HEAD, frozen fixture/model pins, original raw rows/PID/reaping, then report exact abstentions and arithmetic results. This is a diagnostic, **not** a preregistered end-to-end holdout. Follow with fresh disjoint blinded German input/operation fixtures before proposing any consumer integration. Preserve the historical original RED and all negative gates.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; Redmi UNMEASURED; whole V13 INCOMPLETE. Platform remaining budget UNKNOWN.
