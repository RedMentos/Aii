# Prereg: Context OS long-quote exact-span preservation (2026-10-28)

Owner: independent ChatGPT review-only Context OS package, branch `assistant/v13-contextos-long-quote-pin-20261028` from verified integration candidate `c6cc1bf4a4c6b72948494366dad9a3d7670b7ad4`. No modification to frozen Runtime, model weights, source cohorts, B3 or learning gates.

## Reproduced defect before edit
In `v13/code/v13/context_os.py` blob `127af0b872bfce002c6dd72020a22574f52691e8`, `QUOTE` matches only 1..80 characters on a single line. `compress()` then considers a 120-character quoted literal not an exact span. For text beginning `Intro. He quoted "<120 As>" ...`, `first_sentence()` returns only `Intro.`; compression can be marked successful while dropping the quoted literal. This violates Canon §8.4 exact quotation preservation in the active view, independently of any model.

## Locked change and checks
- Recognize paired long and multiline ASCII `"…"` and German `„…“` quotations as exact spans without silently truncating; the existing `SPAN_CHARS`/`SPAN_MAX` caps force RAW fallback for oversized spans. Unbalanced quote delimiters also force RAW fallback rather than silently discarding possible literal text. Do not alter existing compression thresholds, cache layout, user mode, source provenance or learning authority.
- Add deterministic software tests: long ASCII quote, long German quote, multiline quote, >400-char quote RAW, unbalanced quote RAW, and original numeric/code/URL span behavior. Existing Context OS/Context-Sleep tests and full suite must remain GREEN.
- Source-pinned Actions focused and full software suite, compile, privacy/diff, closed raw artifact SHA256. This is a software correctness fix, not measured native cache/Redmi gain.
- Original STEP2/B3/Body-JEPA/LP3/Age/Stage11/Redmi gates unchanged. No production merge without review.

Next: test and independently audit exact-source evidence, then continue other canonical organs.