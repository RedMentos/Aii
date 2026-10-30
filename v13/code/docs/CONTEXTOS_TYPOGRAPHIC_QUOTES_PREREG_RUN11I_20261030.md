# Context OS typographic exact-literal preservation — preregistration 2026-10-30

Owner GPT-6. Review-only child of JEF #1238 exact verified head `c21e180f1902029e1d27aea099728815764dd394`; independent file ownership `v13/code/v13/context_os.py`, new focused tests and workflow, scoped docs only. Canon v10.16.1 and original registered cohorts/model/source/seed pins unchanged.

## Hypothesis and original risk
`ContextOS.compress` extracts ASCII double, German low-double and ASCII single-quoted exact spans, but not English curly double `“...”`, French guillemets `«...»`, or curly single `‘...’`. It may silently compress away source-critical quoted text; English curly double currently fails RAW from being mistaken for an unmatched German close quote. This is a source-fidelity and context-utility problem, not native JEPA learning.

## Test-first frozen cases
Construct long irrelevant old-turn context with a short literal after the first sentence and a large tail, then call `compress(text, 140)`. Before patch freeze the following assertions:
1. Balanced English curly double `“violet compass”`: exact span pinned and output compressed (not needless RAW).
2. Balanced French `«violet compass»`: exact span pinned and output compressed.
3. Balanced curly single `‘violet compass’`: exact span pinned and output compressed.
4. Curly single with contraction `‘don’t forget’`: entire literal pinned, output compressed.
5. Unclosed French `«unclosed literal`: must remain full RAW.
6. Unclosed curly single `‘unclosed literal`: must remain full RAW.
7. Unclosed English `“unclosed literal`: must remain full RAW.
8. Intra-word typographic apostrophe `don’t` outside quotation is not a quote delimiter and must not force RAW.
9. Existing German `„literal“` remains exact pinned and compressible.
These are software synthetic tests only; do not modify historical test data or the frozen Canon.

## Proposed conservative fix
Add narrowly paired typographic quote patterns to `exact_spans`; fail closed for unpaired/malformed typographic delimiters, while treating U+2019 between letters as an apostrophe rather than a closing quote. Strip matched German low-double spans before evaluating English curly double delimiters (same U+201C glyph) to preserve existing German behavior. Existing ASCII/German semantics, source refs, live Context OS authority and Age0 gates unchanged.

## Proof
Test-first original RED and fixed GREEN through isolated GitHub Actions with full original raw logs, SHA256SUMS, compile/privacy/diff checks. No claimed native/Redmi or whole-system utility. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi UNMEASURED, V13 INCOMPLETE.
