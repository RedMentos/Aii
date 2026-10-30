# V13 seed101 German closed-world completeness — verified software checkpoint (2026-10-30)

Review-only branch `assistant/v13-de-closedworld-run11a-20261030` from #1223 HEAD `be26f5176a55180be0f9086868a9c4a1c2a5889c`. Preregistration committed **first** `ea8cf0e6f220dc5d516f37ab85433dadb27e9b62`; 24 frozen cases committed **before candidate** `2048a043fe3f7b06bf8310d3af3e7adc4de05dab`, fixture Git blob `71011ba309759931f2cb9afa487d621e66aebdaa`. Candidate source `52dd27262047ae89f982bd2eee00e394e7642ac9`; frozen baseline pipeline Git blob `25cacd7388e5464dd814f4b18c545e2ec2f78b54` unchanged.

## Concrete result
The original C3 typed-read SHADOW checks each extracted (name, integer) against an adjacent source span, but can accept an incomplete subset. New **unwired** `v13/agi/listarith_de_closedworld_candidate.py` conservatively verifies all integer occurrences in the pre-question data are covered with multiplicity, re-verifies every pair in the data (not just the question), rejects decimals/ambiguous boundaries and otherwise retains the baseline result. A source year or stated aggregate leads to abstention rather than pretending to know which numbers are irrelevant.

The frozen 12 supported cases all emitted the expected exact operation and value; all 12 negative cases abstained, including at least eight baseline-accepted omitted-item examples (checked by tests). This is an authored synthetic cohort, **not** blind, native, Redmi or live tool utility.

## Closed software evidence
GitHub Actions `41018254933` **SUCCESS**, exact tested HEAD `e4a9f5073749cadde3cec0bc950c196e8ac44927`, artifact `12960930057`, downloaded original ZIP SHA256 `8610f8938f242940fe3929cb0e2e348ad4c9cf7112a758cca993c52ce14fc8e1`, 2,248 bytes, CRC clean, **9/9 SHA256SUMS** verified. Original raw TEST: **28/28 OK** (new 8 + baseline 20), TEST/COMPILE/PRIVACY/DIFF **4/4 exit0**, privacy CLEAN, `git diff --check` clean. This is software-only CI on Ubuntu 24.04; no native C3 invocation. Original historical seed79/83 and STEP2 negative evidence not rescored or altered.

## Review limitations and next
- Existing German pipeline remains byte-identical and wired behavior unchanged. The conservative guard can lose coverage on metadata, dates, aggregates, and unrecognized question segmentation; no broad-utility claim.
- Next: independent read-only replay of **original** seed83 native ZIP `12958586993` (expected SHA256 `e92fda4b20a0ba01e533d1b2a343091fb4f46bebe7c9e8a60efdf3f2ca667f57`) with exact-source verifier and this candidate, without changing frozen native score; report per-row candidate coverage/abstentions. No heavy native jobs needed.
- No new approval, age, ToolStep/C5, model or learning authority. Keep all original source/model/seed hashes.

Negative gates unchanged: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; Redmi UNMEASURED; whole V13 INCOMPLETE. Remaining platform budget UNKNOWN.
