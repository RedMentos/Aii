# Run198 — Context OS unmatched inline-code loss audit and SHADOW-only guard

## Parent and ownership
- Parent Run197 PR225 verified head `f67658861eefabdb980b6edc4a3cefe7c1e72aab`, on top of Run196/Run195 chain. Owner only `scripts/context_inline_guard_run198.py`, `tests/test_context_inline_guard_run198.py`, new workflow and this proof folder. No edits to frozen `v13/context_os.py`, Runtime, Age, learning, Canon or active native owner.

## Problem and candidate
- Existing Context OS `compress` protects complete fenced code and paired single-backtick spans. An unmatched inline backtick after the summary head has no CODE span; the current compressor may omit it in the active view. This is a *source-literal retention* gap, not a new native or learning result.
- Candidate `compress_candidate` checks Markdown inline delimiter integrity before invoking unchanged ContextOS compression. It conservatively keeps RAW if an unclosed single backtick, unsupported double delimiter, or multi-line inline code would be dropped. Closed fences, paired inline code and ordinary prose still use the existing compression path.
- Default off, no Runtime wiring. A production integration would require owner release, exact source/provenance audit, regression against Context OS source/restoration/KV reuse, long-history tests and Redmi measurements. This candidate alone does not authorize ACTIVE mode or raise any gate.

## Evidence and cross-review
- Local 9/9 synthetic tests PASS using an explicitly copied minimal ContextOS compression stub (NOT the actual full checkout). The original source code was read from verified GitHub remote. The stub and local test log are retained as diagnostic only; GitHub Actions on the full repository is the actual-source verification and must be checked separately.
- Independent counterexample review identified that two matched backticks separated by a newline are also not recognized by ContextOS's `CODE` regex. Candidate now checks exact same-line regex coverage, not only even delimiter count. Test added.
- CI workflow executes Run198 plus existing Run93/Run100 exact quote/fence tests on the real remote source and the official public privacy scanner. Native models and Redmi are NOT RUN.

## Unchanged gates and exact next step
- STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; DS2 H2 `FAIL`; full V13 `INCOMPLETE`.
- Next: inspect Run198 CI, independently review parser against escaped/fenced Markdown and full ContextOS history binding. If safe and SourceHandoff ownership releases, propose narrow runtime integration with full tests and source-backed second-attempt utility. Otherwise keep candidate SHADOW-only and continue independent canonical functional work.
- Command: `cd v13/code && python -m unittest -v tests.test_context_inline_guard_run198 tests.test_context_unclosed_fence_run100 tests.test_context_exact_quotes_run93`.