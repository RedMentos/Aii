# C2 learned-route numeric invariance candidate — prospective software ablation (2026-10-30)

Owner GPT-6, isolated child of verified G13 #1285 checkpoint 9d14c3cc0ffeacf3ac7fc2c8cffedae9b6ea5bb6. No active C2 route-head or frozen cohort edits.

## Observed limitation

Current `v13/route_words.py` claims digits fold to `#` but uses per-digit substitution, so a word containing 7 versus 7000 becomes `#` versus `####`. Decimal, scientific and grouped numbers also create different token counts. A learned route classifier can exploit irrelevant numeric spelling/length instead of the task's processing requirement. This is a candidate hypothesis, not measured utility failure attribution.

## Frozen controls and acceptance

- Preserve original route_words v1 byte-for-byte and its learned weights. Implement separately versioned v2 candidate with the same 512-dimensional signed CRC32 feature scheme but **not** interchangeable learned weights. Never silently load v1 weights under v2.
- Normalize complete standalone decimal, grouped, percentage and scientific numeric literals to one numeric marker, while preserving number of distinct numeric operands and surrounding words. Embedded digits in alphanumeric labels collapse per run. ISO dates remain multiple numeric components; operator punctuation is not yet modeled.
- Matched tasks with same words but different literal numeric values/length/notation should have identical v2 features; v1 must demonstrate at least one numeric-length difference. Different task words and operand counts should remain distinguishable. Deterministic repeat and empty input controls.
- Measure and print v1/v2 cosine similarity on fixed diagnostic pairs, without claiming downstream route accuracy, transfer, latency or learning gains. Follow-up needs a new preregistered disjoint human-route-label cohort, trained head, ablation, retention and Redmi checks.
- Software CI: focused unit tests, compile, Canon blob, privacy, diff, raw artifact + SHA256SUMS. No model/native/Redmi jobs or Age0 authority change.

All original negative gates remain: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 no promotion, Body-JEPA unavailable, jepa_weight0, whole-system incomplete. Exact next command: add isolated `v13/route_words_numeric_candidate.py` and focused tests, then run pinned CI and record measured software-only results.
