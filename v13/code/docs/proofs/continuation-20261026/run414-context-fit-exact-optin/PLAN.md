# Run414 — optional exact Context OS fit count (independent Claude PR407 review)

2026-10-26. Review-only branch from Claude PR407 `7b7a06ea99a273a55ac56c43688ca29d0f72d8b1`, separate from active Run413 native STEP2 chain. No merge into main or current native cohort.

## Observed risk
PR407 `context_fit.fit` quick-accepts a prompt when Python character length <= `limit * 1.5` and skips native token counting. That ratio is a heuristic, not a proven tokenizer bound for emoji, unusual Unicode, or high-density ASCII; an over-budget prompt can be incorrectly labelled `fits=True`. `counter` also reports the static label EXACT even after falling back to an estimate on native error. Existing tests explicitly exercise the quick bypass but not an adversarial high-token-density counterexample. The PR407 300-row historical results remain immutable.

## Scope
Add a persisted validated `context_fit_count_mode=legacy_quick|exact` setting, default `legacy_quick` to preserve previous behavior and benchmark comparability. In `exact` mode disable the unproven quick-accept shortcut (`sure=0`), so the real runner tokenizer is called before any `fits` claim. If native counting fails, mark the count source as estimated in per-turn telemetry; never silently call it exact. Do not change stable/pinned rules, source refs, age/learning rights or any native model weights. Add adversarial software tests with a fake high-token-density tokenizer and explicit opt-in behavior. This is source-only; new paired native and Redmi latency/utility measurements are prerequisites before changing the default.

## Gates
No new STEP2/B3/Body-JEPA/Redmi/Age/whole-system proof. PR407's historical 165->188/300 comparison is not rerun or silently reinterpreted. The exact opt-in path can trade latency for more reliable overflow detection; performance unknown until measured.
