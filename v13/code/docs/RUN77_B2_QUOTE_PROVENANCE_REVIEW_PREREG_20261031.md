# Run77 B2 exact SourceRef/quote provenance — independent diagnostic preregistration

Date: 2026-10-31 UTC. Owner: GPT-6, isolated review branch `assistant/v13-run77-b2-quote-provenance-review-20261031-gpt6`. Exact parent: `8da75d9396760c7907726d71d783c236527cefa7` (Run77 forensic PR #1438). Original Run77 PR #1437 and both original/replay verifier REDs remain untouched. This package is **software-only and diagnostic-only**; no fresh science, native execution, production wiring, or permission changes.

## Problem and hypothesis
The frozen Run77 driver accepts any prior source slice occurring in prior text, whereas the frozen verifier demands that the entire cited source slice equal one offered quote. The actual `Cognition.analyst_context` supports both exact equality and bounded `quote_span` pointer verification. Neither frozen predicate alone faithfully represents the consumer's bounded source-span semantics. The replay's five B2 prior-evidence disagreements and zero strict semantic scores are retained as observed, not re-scored.

## Locked plan before implementation
1. Add a **read-only** report auditor which examines exactly six seed797 WITH_PRIOR B2 current offers, binds refs to registered prior/current source SHA256, source_id, UTF-8 character offsets, modality, and exact offered quotes; support only the existing `quote_span` pointer path with `quote_context_chars <= 200`. Refuse foreign source, forged hash, boolean/negative/out-of-range offsets, missing quote, and malformed report. Count prior and current refs separately. Zero prior evidence is a valid **negative** observation, never fabricated proof.
2. Add adversarial synthetic tests: valid exact quote, bounded pointer, no evidence, foreign source, altered hash, off-by-one span, non-quoted span, invalid quote-context width, malformed rows. No original fixture/seed/scorer/model/runner source changes.
3. Run Python unit tests and compile/privacy/diff checks in isolated GitHub Actions. Capture raw stage exits, SHA256SUMS and HEAD in a small artifact. Verify the original artifact if retrievable; otherwise explicitly retain original raw verification gap. No heavy native jobs.
4. Save original results, source hashes, status and exact next command to a scoped BUILD_STATE doc; verify remote bytes. Do not reinterpret any Run77 original scientific RED or promote STEP2/B3/Body-JEPA/World-JEPA/jepa_weight/Redmi.

Acceptance: all new synthetic tests green and independent remote checks, no source or authority mutation; any failure stays RED. This is an independent source-provenance diagnostic, **not** a new B1/B2 semantic utility result.

Next command after prereg: implement `v13/code/scripts/run77_b2_quote_provenance_audit.py`, `v13/code/tests/test_run77_b2_quote_provenance_audit.py` and isolated CI workflow, then inspect original Actions and raw evidence. Remaining platform budget UNKNOWN.
