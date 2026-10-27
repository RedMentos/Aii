# WP-N7 Context OS native cache-cost integrity — 2026-10-27

**Owner:** `codex/automation11-n7-cache-metric-integrity-20261027`; review-only sibling of PR #719, based on PR #718 exact SHA `edd0212c1774f893433040f48fa6b57c3d2d4209`. Do not merge directly into old `main`.

## Defect and patch
`ContextOS.observe` accepted `isinstance(True,int)` and negative cache/prompt token counts. For example `cache_n=-2,prompt_n=10` generated a negative reuse ratio and, with Context OS ACTIVE, a nonphysical N10 cost-error signal. Float, nonfinite, missing and malformed envelopes could also escape or raise after the user-visible answer.

The fix accepts only exact Python integers with `0 <= cache_n,prompt_n <= 2**31-1` and strictly positive total. Missing evidence yields no cost credit; malformed supplied evidence is returned as `cache_rejected=True` and does not change aggregate cache statistics or signal the modulator. Valid observations still report measured reuse and cost as before. Default SHADOW/ACTIVE policy and source history are untouched.

Added regression cases to `tests/test_context_os.py`: bool, negative, zero-total, float, NaN, oversized, incomplete and non-dict timings, with explicit no-modulator/no-aggregate assertions, followed by a valid positive control.

## Evidence and gate limits
- Focused software CI workflow: `.github/workflows/n7-cache-integrity-review.yml`, no models downloaded.
- This is software integrity evidence only. It does not establish native KV reuse, Context OS utility, STEP2 success, B3 success, age promotion, Redmi measurements or completed V13.
- Keep all Canon requirements, provenance and negative gates intact. No private data or training states added.

**Next command:** `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_context_os`.

**Next prerequisite:** exact-head CI PASS and independent review; then continue other Canon packages or a real source-bound cache-cost holdout. Do not use invalid synthetic metrics as real learning evidence.
