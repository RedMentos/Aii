# WP-N8 / STEP3 — turn-local semantic query freshness (preregistered)

Date: 2026-10-27 UTC. Owner: GPT-6 scheduled continuation. Review-only child of PR #741, parent exact `fe57536308819b6facc5947d24fcff66468ab34e`. This package does not touch the frozen Canon, models, training cohorts, source hashes, or learning/age permissions.

## Suspected defect / expected RED

`SemanticKeys.last_query` is a mutable in-memory embedding snapshot reused by `episodes.observe_turn` if its digest matches the current turn text. `Memory.recall` does not clear this snapshot on disabled embeddings, empty candidate pools, `top_k=0`, or a failed encoder. `SemanticKeys.similarities` also leaves a previous successful snapshot intact when a subsequent call fails. Thus a later turn with the **same text** may consume a prior-turn embedding even when the current recall did not produce one. The digest is a text equality check, not a turn freshness proof.

Preregister test: first complete an embedding recall and assert the snapshot exists. Then repeat the identical text after switching embeddings off, with `top_k=0`, and after a simulated encoder `Unavailable`; each path must clear the snapshot. Direct `similarities` failure must also clear it. Existing code is expected to FAIL these assertions. Check `episodes.observe_turn` does not consume a stale vector after disabled recall. Use synthetic Fake embeddings only, no model-quality claims.

## Proposed GREEN / constraints

Clear `last_query` at the start of **every** `Memory.recall`, including `top_k=0`, before any early exit. Clear it at the start of `SemanticKeys.similarities` for direct calls, and publish the new digest/vector only after a successful complete result, not before a cache-write or cosine failure. Keep current successful same-turn WP-N8 reuse, source-backed recall, lexical fallback, cache validity, and all caps/deadlines. No persistence schema change.

## Verification plan

Run focused semantic-memory and episode tests, compile, privacy scan against exact parent, `git diff --check`, then full software suite on exact source in an isolated GitHub Actions runner. Record RED failures and GREEN raw exits, workflow source SHAs, artifact hashes, and independent review. Synthetic/software proof only. Preserve LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, STEP2 UTILITY_FAIL, B3 L1 FAIL, `jepa_weight=0`, Age authority 0, Redmi unmeasured, V13 incomplete.
