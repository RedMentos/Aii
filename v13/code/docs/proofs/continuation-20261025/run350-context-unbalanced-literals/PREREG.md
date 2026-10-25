# Run350 prereg — Context OS unbalanced literal delimiters must stay RAW (2026-10-25)

Base: Run349 review head `79aa5ec014e1cf69b2c49a76b7c1e9cdbe9ca6f6`, building on Run348/Run347; not main. Owner: `v13/code/v13/context_os.py`, new `tests/test_context_unbalanced_literals_run350.py`, new workflow and this proof folder. No other source/owner changes, no registered cohort/model/seed changes.

## Concrete source-loss risk
`ContextOS.compress` already keeps matched code, URLs, numbers, quotes and unmatched triple-fence tails RAW. However a late unmatched **single inline backtick**, ASCII quote, or German/curly quotation delimiter is not returned by `exact_spans`; the extractive summary can silently omit it from the active context view. The underlying source remains stored, but the promised exact active view may lose a literal whose closing delimiter is absent. A conservative RAW fallback is preferable to inventing or dropping text.

## Frozen acceptance
- RED-first pure deterministic tests show that a long older turn with late unpaired backtick, ASCII `"`, German `„`, curly `“` or `”` currently compresses despite losing the delimiter and following content.
- GREEN `compress` returns original text and `ok=False` for unpaired literal delimiters; does not claim to have compressed or preserved a nonexistent matching span.
- Balanced inline code, fenced code, ASCII/German/curly quotes and numbers still compress when safe, keeping every exact span. Existing `test_context_os`, `test_context_exact_pin_run73`, `test_context_exact_quotes_run93` pass. Source-only software, no native/Redmi/ContextOS ACTIVE authority promotion.
- Use conservative source-only detection on text **outside complete code and quoted spans**; no semantic reconstruction. Exact-head GitHub Actions, raw RED/GREEN logs and hashes, privacy scan, independent ZIP CRC/internal SHA and private backup. Keep all original negative gates.

No evidence from this source-only repair promotes G6/G6B, native cache utility, STEP2, B3, Body-JEPA, jepa_weight, AG6, Redmi or whole-V13.
