# Run104 — semantic memory cached embedding integrity (preregistered)

Date: 2026-10-25 UTC. Parent: Run103 PR #135 `9de124ff64dc04aba2db22ad15f29616d124376b`. New independent owner: `v13/code/v13/semantic_memory.py`, new `tests/test_semantic_cache_integrity_run104.py`, isolated CI workflow, and this evidence folder. Do not touch active Memory.feedback, userrules, World, Callosum, JEF or LP3 owners. Existing model/source/seed registrations frozen.

## Hypothesis / fail-open case

`SemanticKeys.similarities` currently trusts persisted state values whenever they are a list of the expected length. A raw persisted `[NaN,0]` can pass through `cosine`, whose Python `max(-1.,min(1.,nan))` returns 1.0. A forged unnormalised `[100,0]` also clips to 1.0. These are **not** source-backed relevance proofs. The store API itself disallows NaN writes; test deliberately injects malformed persisted SQLite bytes as an adversarial crash/tamper fixture, not a normal operator action.

## Expected RED before fix

- Cached NaN/Inf, huge magnitude, boolean and wrong-type vectors are never scored or promoted as similarity; re-encode from pinned key text instead. Baseline currently returns false 1.0 or raises TypeError for at least some cases.
- A valid cached unit vector is reused (query-only encoder call); a rounded near-unit vector is not needlessly rejected.
- After restart, malformed persisted cache remains non-authoritative and is replaced only by a newly encoded vector.
- If fresh encoder is unavailable, do not silently reuse the poisoned cache.

## Intended narrow correction

Validate **all** cached coordinates are finite real numbers (not bool), correct dimension, and unit norm within rounding tolerance before using them. Invalid caches are cache misses. Keep source revalidation and entity guard in `Memory.recall`; no changes to native encoder, authority, permissions or model manifest. This is not cryptographic authenticity of a valid unit vector and not native embedding quality.

## Proof/limits

Preregister tests before implementation; retain actual RED log, then GREEN on GitHub Actions real full checkout, official privacy scan and old semantic/retrieval regressions. Synthetic vectors + real SQLite persistence, not real native embeddings/Redmi. Gates unchanged: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; V13 INCOMPLETE.
