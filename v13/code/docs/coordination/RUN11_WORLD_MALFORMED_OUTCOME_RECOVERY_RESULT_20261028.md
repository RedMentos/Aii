# Run11 World malformed completed outcome recovery — 2026-10-28

Independent F4 World/Self lifecycle review candidate based on #850 `b454f81da33de9d621af6417ed47ab55cba6263f`, prereg `4b2d8d206ed636d91c41988ede9959f47cd8426c` before implementation. This branch is separate from numeric duration guard #861 and has not been integrated into production.

`Store.finish_action` can preserve arbitrary JSON-serializable actual outcomes. Previously `WorldState.observe` and `forecast` assumed all decoded outcomes were dictionaries and called `.get`, so a malformed completed action such as `[]` or `null` could interrupt World recovery after restart. The candidate preserves the **exact raw value** in `PredictionOutcome.observation.observed`, uses a safe empty view only for optional timing/role fields, does not score timing or latent reward, and excludes non-dict outcomes from future timing samples with an explicit `invalid_outcome_shape_count`. Valid dict outcomes retain existing behavior. No source, action or corollary history is rewritten.

New no-model Store/Runtime tests cover malformed list/null/string/int, exact raw preservation, unscored observation, restart recovery after an unobserved completed malformed action, and later valid [2,3,4] timing median. Candidate world blob `ee430d3c1df2e00c51d42ce1b0aff00f621814e4`, new test blob `e52aadd31ff896ee770c520c6bf49a15cadadafc`, original world blob `b4ed658f2212c013b9c77285a3dc2d3dc5553758` preserved on other branches.

GitHub source-pinned focused/full Linux software CI is staged; **status unverified/pending**. No native model inference, no Redmi, no JEPA training or Age promotion. Next: inspect CI raw and hashes, preserve RED, independently review how to combine with #861 only after both pass, then test crash recovery on exact new source.

Unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight0, Age0 RECORD_ONLY, phone_measured=false, whole_system_complete=false.