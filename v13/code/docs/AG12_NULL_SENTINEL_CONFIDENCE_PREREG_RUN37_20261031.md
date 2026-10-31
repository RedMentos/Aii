# Run37 prereg — AG12 native null sentinel is not nonfinite confidence

Owner GPT-6 scheduled continuation, 2026-10-31 UTC. Review-only child of Run36 #1363 at exact `9d3bffd28e010b472fbc4e5d423bdca217f43e6a`. Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7`, original frozen AG12 solver `66a9419143c456f01747b4796fb327b3b36711b3`, Run31 finite helper `46982818f6c6078d823c97388c1a4ec250d82e14`, native `focal.token_confidence` source `2135f4404f241cfc198abd7fe2288f13a622f4fc` unchanged.

## Discovered semantic distinction, registered before code

The original native `focal.token_confidence(pairs,field='answer')` returns a dict with `field_min_prob=None` and `field_mean_prob=None` **legitimately when no answer-field token span was recognized**, while `mean_prob` may still be finite. The Run31 `safe_confidence` currently treats a **present None** at the highest-priority field as `invalid:field_min_prob` and returns 0, even though this is a documented absent-span sentinel rather than NaN/Inf. This can change votes and cause an apparent invalid-native-metric incidence even with entirely finite logprobs. The in-flight Run36 seed17 native cohort (Actions `41149111278`) is source-frozen and **must not be edited or restarted**. Its aggregate `invalid:field_min_prob` category cannot by itself prove actual NaN/Inf incidence; report this limitation even if Run36 is GREEN.

## Isolated software candidate and frozen tests

Implement `safe_confidence_null_aware` in a new isolated module, not changing Run31/33/36, original solver, runner or production. Exact semantics:
- absent `metrics`, absent `token_confidence`, `token_confidence=None`, or all priority fields missing/None -> historical .5, source `none`;
- for each key in original priority order (`field_min_prob`, `field_mean_prob`, `mean_prob`), a **None** means unavailable and is skipped, never treated as certainty or malformed;
- first present non-None bool/string/NaN/±Inf/overflow/non-numeric -> hard zero `invalid:<key>`, with **no** fallback to lower-priority fields;
- first present finite numeric -> clamp [0,1] with original source key, exact finite parity.

Tests must include native `focal.token_confidence` output with no answer-field span, absent and all-None, finite parity, NaN/+Inf/boolean/string/overflow hard-zero, and an isolated same-output vote witness distinguishing null sentinel from actual invalid. Source/fake model only; no native proof. No new production integration or threshold tuning. This is a narrower semantic correction, not proof of AG12 utility, calibration or real native invalid incidence. If a future native cohort is needed, preregister **separate source/type counts** (None vs nonfinite) and run after Run36 terminal and native owner release.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; World-JEPA SHADOW; no Redmi, no learned German transfer, no live JEF or whole V13 completion. No production merge/auto-merge.
