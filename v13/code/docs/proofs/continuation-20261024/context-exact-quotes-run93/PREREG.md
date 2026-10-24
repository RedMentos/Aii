# Run93 prereg — Context OS quote exact-span preservation

2026-10-24. Exact base Run92 PR125 `e56245c1055a1ef117fbc43af57aefd35aaaf665`, Linux selected 397/397 and extracted ZIP 96/96 PASS. Owner: `v13/code/v13/context_os.py` QUOTE recognition only; new `tests/test_context_exact_quotes_run93.py`; focused and extracted CI invocation; Run93 proof. No ContextOS mode/knob/age/learning or native model changes.

## Expected RED
§8.4 exact-span compression claims quotes survive compression or the turn stays RAW. Existing `QUOTE` regex recognizes only ASCII double and German low-high quotes of length 1..80, omits common English curly double quotes `“...”` and all longer quoted spans. A long prior turn may be compressed while silently dropping a late quote. Preregister real `context_os.exact_spans/compress` tests: short English curly quote, long ASCII and German quotes >80, oversized quote >SPAN_CHARS must force RAW, and existing short quote controls. Preserve RED before any code fix.

## Fix acceptance
Recognize paired ASCII, German low-high and English curly double quotes without an arbitrary 80-char regex cap. Let existing SPAN_CHARS/SPAN_MAX compression budget force exact RAW fallback on oversized spans; do not change other source/ContextOS policy or active authority. Run selected Linux, extracted source ZIP, official privacy; no learned semantic utility, native/Redmi, STEP2/B3/JEPA gate promotion.