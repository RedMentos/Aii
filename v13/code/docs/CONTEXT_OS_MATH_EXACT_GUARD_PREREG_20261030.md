# Context OS numeric equation source-retention guard — pre-edit contract (2026-10-30)

Owner GPT-6 automation, review-only child of native Run13A #1280 at `5ba394d08ab9494d77f0b406b74ea931532b0388`. Different Canon organ from STEP2; no native/model/Redmi work and no live ACTIVE mode promotion.

Observed potential source-loss class in current `v13/context_os.py`: extractive compression pins individual numeric tokens but may omit their arithmetic relation when it appears after the first sentence. Example: an older turn with `487 - 318 = 169` may retain `487`, `318`, `169` in an appended exact-span list without preserving the operators/order. Similarly scientific `1.23e-5` can split into fragments. The current exact-span invariant is necessary but not sufficient for preserving numerical reasoning semantics.

Bounded implementation contract:
- Preserve entire RAW turn (no compression) when a numeric arithmetic/comparison operator is present outside safe lexical date/range forms. Recognize `=`, `×`, `÷`, `*`, `/`, `+`, Unicode minus `−`, `<`, `>`, `≤`, `≥`, and spaced ASCII subtraction. Keep ISO `2026-10-09` and simple unspaced numeric range from triggering this guard; they remain exact-spanned under existing policy. Conservative false positives are acceptable because RAW retains source.
- Pin complete scientific notation tokens such as `1.23e-5` and `-2E+6` in exact spans. Avoid treating exponent sign as a separate subtraction.
- Do not alter Context OS default SHADOW, Age0 rights, source IDs, learning rates, active layout, scorer, model pins or frozen cohorts. Existing exact quotes, URLs, code and date compression should still pass.
- Tests: pure compression positive/negative controls, scientific token preservation, old-turn planning remains RAW when budget allows, existing Context OS test families. Source-only CI must pin source/Canon hashes, preserve all RED, privacy/diff, original raw and private backup. No STEP2/B3/JEPA/Redmi/age promotion.

This is a conservative information-integrity change, not a claim that models understand arithmetic or that full Context OS is complete.
