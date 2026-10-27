# STEP3 semantic embedding cache integrity — independent review 2026-10-27

**Owner:** GPT-6 continuation; review-only child of PR #740 exact `130083fa8fcd7b5ee0cd81635d654da0e4927cfe`. Preregistration `7a86405ce5f6ada52e9f1c21fd25464b31ed8c8d` before test and source changes. Canon, model revisions and EmbeddingGemma hashes unchanged.

## Confirmed defect

`SemanticKeys.similarities` trusted any persisted cache list of the correct length, even if its L2 norm was enormously larger than one. A finite JSON cache of `[1000000.0]*dim` bypassed the encoder and `cosine` clamped the enormous dot product to 1.0 (maximum relevance) for an unrelated query. Direct `cosine([nan],[1])` also silently returned 1.0. This can contaminate STEP3 relevance ranking; stored human-approved memory values and source authority were not themselves rewritten.

## Repair

Validate cached embedding length, exact numeric non-bool entries, finite coordinates and squared unit norm in [.98,1.02] (six-decimal cache rounding stays well within). Invalid cache entries become missing keys and are re-embedded from their stored human key text under existing deadline/cap; if the encoder fails, existing lexical fallback applies, not false-perfect similarity. `cosine` now rejects length mismatch and nonfinite dot product. No model weights, cache key version, source data, learning authority or Age gates changed.

## Exact-source RED evidence

RED test-only commit `f4b2487e525ce58aa258bdd6ae2b82370f6ead36`, original semantic blob `a7c22c6775b67db6ab06aa07c6f4ab3b43706988`, Actions `40534732955`: **10 tests, 2 expected FAIL**, 8 PASS. Invalid cached vector had `encoded_keys=0` instead of 1; nonfinite cosine failed to raise `Unavailable`. INSTALL/COMPILE/PRIVACY/DIFF exits 0, UNIT exit 1. Artifact `12747304758`, ZIP SHA256 `a7c243748051b118386611e0941db8b00260e68ba7d87c69ad794d1282921eda`, CRC, HEAD, source blob, raw exits and failures verified. Private Library backup re-downloaded byte-identical at `/V13-Checkpoints/2026-10-27/Automation11K-Semantic-Cache/RED-40534732955.zip`.

GREEN source `5ee57cb17092de6d9a4e4272ee33ff9d7f639a0b`, blob `b8fef1143d4a27eb00a3260fa99b7a79efd46ef2`; final bool-cache regression test commit `11c022da839899f4d8d8ccb7019de0cabde6c93b`. Focused Actions `40534936708` at exact source/test head `11c022da839899f4d8d8ccb7019de0cabde6c93b`: **10/10 PASS**, INSTALL/UNIT/COMPILE/PRIVACY/DIFF all exit 0. Artifact `12746044766`, ZIP SHA256 `4e7e97845b373d672753da9f56faaf93302e7908064891bd30649a0286a87834`; CRC, HEAD, semantic source blob and raw exits verified. Private Library backup byte-identical at `/V13-Checkpoints/2026-10-27/Automation11K-Semantic-Cache/GREEN-40534936708.zip`. Full software suite workflow created at `4984b6006e4f38d659db59c2a05334a8d18ccf53`: **PENDING**, no full-suite PASS claimed. An intermediate pending Actions run `40534911381` was cancelled by concurrency replacement, not a software failure; preserve that attempt.

## Gates / next

LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; `jepa_weight=0`; Age authority 0; Redmi unmeasured; V13 incomplete. This is synthetic/software cache integrity, not semantic embedding quality or second-attempt gain. **Next:** inspect exact-head focused/full suite, preserve raw exits/ZIP hashes/private byte-exact backups, then independent review and continue separate canonical work. No automatic main merge.
