# Run100 — Context OS unfinished fenced-code must remain RAW (preregistered)
Date: 2026-10-25 UTC. Base: Run99 PR #131 head `4b0ccad29c837bba7067bc9dec8e825f1437f5bb`.
Owner: `v13/code/v13/context_os.py` **only** `compress()` early refusal; new `tests/test_context_unclosed_fence_run100.py`; isolated workflow and this evidence directory. Do not touch concurrent Run99 Callosum, Run97 JEF, Run96 Sleep, or Run94 World Model owners.

## Reproducer and causal hypothesis
The existing `CODE` regex matches *paired* Markdown triple-backtick fences, but an incomplete fence (common in interrupted assistant messages) is not matched. `compress()` may shorten the source to the first sentence while silently losing the remaining incomplete code block. This violates the Context OS exact-source/lossless-on-risk obligation. Unclosed source stays intact in storage, but the active compressed view may lose its code; source links alone do not make that view faithful.

## Pre-registered RED controls
1. Late unclosed ```python fence containing unique code identifiers and no digits must force RAW: `ok=False`, output exactly input.
2. Unclosed fence with numbers (whose digits may be extracted) must still force RAW: preserving only digits is insufficient.
3. A *closed* short fenced code block after a long ordinary history must still compress, preserving the complete code span byte-for-byte.
4. Two closed fenced blocks must still compress when within existing SPAN limits; no global disable.
5. Ordinary prose remains compressible.

Expected tests-only head: 2 RED, 3 GREEN. Keep raw CI evidence before implementation. Candidate fix: a conservative precheck for odd triple-backtick fence delimiter count in `compress()`; return unchanged source with `ok=False`. This is a safety fallback, not a parser redesign. Future multi-turn incremental fence state remains out of scope.

## Proof and non-promotions
Run Linux software tests in isolated GitHub Actions with original Context OS and Run93 quote regressions; privacy scan; inspect both RED and GREEN outputs. No native models, training, Redmi, active-mode changes or new learned utility. STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; canonical_architecture_complete=false; user_full_scope_complete=false. Canon and user decisions untouched. This branch must not be merged without independent review.
