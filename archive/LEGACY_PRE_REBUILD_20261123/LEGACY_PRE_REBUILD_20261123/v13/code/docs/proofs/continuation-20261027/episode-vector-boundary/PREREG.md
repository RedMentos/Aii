# WP-N8 A1 episode-boundary vector integrity — preregistered

Date 2026-10-27 UTC. Owner GPT-6 continuation. Review-only child of PR #742 exact `0047aa76d5e5d221f18c0e4d4ce36c14bcb70f46`. The existing canonical episode/semantic-memory behavior remains the target; no model/learning/age changes.

## Suspected defect / expected RED

`Episodes.observe` stores caller-supplied vectors using `round(x,5)` without finite/type checks. A NaN vector reaches strict JSON persistence and raises, losing the boundary observation; malformed vectors may also skew `signals`. `Episodes.cosine` uses `zip` for dot products but full-length norms, silently treating dimension-mismatched vectors as comparable; for identical turn text, an extra large dimension can fabricate a high context-shift boundary. A1 boundaries are supposed to use comparable valid signals, falling back to lexical shift when embeddings are unavailable.

Preregister software tests: (1) two identical-text events with vectors `[1.,0.]` and `[1.,0.,100.]` must fall back to lexical shift (0), not cut for a fabricated semantic change; (2) nonfinite, bool, nonnumeric, and zero vectors must not crash `observe` or persist a false semantic vector, and same-text lexical fallback remains 0; (3) finite same-dimensional real vectors still drive an actual context shift. Existing code should FAIL the negative cases. Tests use synthetic vectors, not EmbeddingGemma quality.

## Proposed GREEN / limits

Accept only nonempty list/tuple of finite real non-bool coordinates with nonzero finite L2 norm; do not accept malformed persisted previous vectors. Compare semantic vectors only when their dimensions match; otherwise leave semantic signal unavailable and invoke the existing lexical fallback. Compute cosine with numerically stable normalization (divide before multiplying), preserving finite valid behavior. Never change episode gates, source provenance, semantic cache, Age, JEF/C3/Bodies or model hashes. No new authority. Validate under focused tests and exact-source full software suite; preserve RED raw artifacts, failed attempts and private backup. No native/Redmi claim.

Negative gates: LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; `jepa_weight=0`; Age authority 0; Redmi unmeasured; whole V13 incomplete.
