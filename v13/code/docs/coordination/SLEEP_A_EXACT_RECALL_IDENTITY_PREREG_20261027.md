# Sleep A retention probe exact memory identity — prereg (2026-10-27)

Review-only independent F9/Sleep A package based on verified C1+World+B3-seed integration `1ab88aa30947e2f3da9905b1d3055f04b98a8bed`, not main. Owner GPT independent Sleep review. File ownership: `v13/code/v13/sleep.py`, new `v13/code/tests/test_sleep_a_exact_recall_identity_review.py`, dedicated CI and coordination. No native/model jobs, no other owner's branch edits.

## Falsifiable defect

`SleepCycle._probe` currently counts a protected memory as recalled when **either** its exact memory ID is returned **or any other retrieved memory has the same value text**. Two different source-backed human corrections can legitimately share a value (e.g. `120 Euro`). Recalling only the wrong event/key then incorrectly yields Sleep A `PASS`, hiding a retention failure. This contradicts source-bound episode retention. The underlying `Memory.recall` returns stable IDs and validates its own sources, so value-only fallback is unnecessary for proof.

## RED tests before fix

1. Two active, different source-backed facts in the same session with identical value; mocked recall returns only the *other* ID. Probe of the target must report `FAIL` with `RECALL_MISS:<target_id>` (currently falsely PASS).
2. Mocked recall with same value but missing ID must also FAIL.
3. Exact target ID recalled with matching value must PASS; no broad retrieval-policy change.
4. Existing Sleep scheduler, replay, retention, source-integrity and privacy tests remain passing. No source/model/seed/cohort edits, no learned utility or Age promotion.

## GREEN and evidence

Change only the Sleep A retention check to require the exact memory ID in the verified recall result. Prereg then test-only RED, source GREEN, focused and full software CI, raw exits/ZIP hashes/CRC/private backup. Keep original failed attempts. No automatic training, facts or weights are changed. STEP2/B3/LP1/LP2/BJ1 negative gates and `jepa_weight=0` unchanged; whole V13 incomplete.
