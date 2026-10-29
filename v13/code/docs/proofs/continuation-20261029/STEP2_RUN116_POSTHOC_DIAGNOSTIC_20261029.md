# STEP2 Run116 frozen native diagnostic — exploratory read-only reanalysis (2026-10-29)

**Evidence and scope.** Independently downloaded original Run126 exact-head software ZIP from Actions `40812183190`, artifact `12870729267`, ZIP SHA256 `6b1f12aa2e8259e2073887394665f27e3d7728f37332a96b24fb00882d71d87f`. That ZIP embeds original Run116 native `STEP2_RAW.json` SHA256 `c0cd539ec28f9583abe25c93f48871597df6758c442782eb6fedd56ad612105f` and `TOOL_RAW.json`; original nested 29/29 hashes and outer 51/51 hashes verified, CRC clean. All observations below are **historical Linux-native Run116** plus **software-only Run126 pair preparation**, not new C3 calls. This is a post-hoc diagnostic, not a preregistered utility result.

## Actual Run116 C3 tool replay by frozen variant (six fixtures each)

| Variant | Action exact | Wrong committed | UNKNOWN | Full JSON exact | Mean field utility |
| --- | ---: | ---: | ---: | ---: | ---: |
| b1_only | 0/6 | 0/6 | 6/6 | 0/6 | 0.5139 |
| b2_only | 1/6 | 0/6 | 5/6 | 0/6 | 0.2222 |
| both_none | 1/6 | 0/6 | 5/6 | 0/6 | 0.4722 |
| both_exact | 2/6 | 0/6 | 4/6 | 0/6 | 0.6250 |
| both_control | 2/6 | 0/6 | 4/6 | 0/6 | 0.5417 |
| same_policy_dual | 0/6 | 0/6 | 6/6 | 0/6 | 0.5000 |
| prompt_only_dual | 0/6 | 0/6 | 6/6 | 0/6 | 0.3750 |

All six `both_exact` oracles require action A. Atlas, Borealis and Cygnus returned UNKNOWN because both option `remaining` and `eligible` values were null despite correct costs/days/locality. Delta and Epsilon selected A and had correct option fields but scored 0.9167 each (project/action field issue in original scorer must be inspected before any broader claim). Fornax returned UNKNOWN; it also inverted locality for option A and left remaining/eligible null. This is **not** evidence of a two-body causal utility win: 0/6 fully exact and canonical STEP2 remains UTILITY_FAIL.

## New software-only quote transport integrity (no native inference)

Original Run126 preflight `experiment/pairs.json` has 42 unique project×variant pairs: **30** treatment rows add exactly one verified historical rule sentence to **B2_GIST** `verified_quotes`; **12** unchanged control pairs are byte-identical. Independent check against six original fixture histories verified all **42/42** source text SHA256, char offsets, span SHA256 and pair mutation scope; **0 mismatches**. Only consumer user-payload keys are `analysts` and `current_source`, with no oracle/action/score key. All 42 original control messages and 42 treatment messages are prepared, **0 new native C3 calls**.

The source-only intervention is a *transport ablation*, not B2 selecting a rule, not learning, not proof of C3 utility. The next meaningful measurement is the separately preregistered 42 matched pairs / 84 actual C3 calls, with original pinned C3 seed13, B1/B2 CQP20 source, serial Linux resource owner, independent raw verifier and no wrong committed treatment action. That native path remains **BLOCKED** until a separate verified native-owner release receipt exists; the exact-head software audit alone does not authorize dispatch.

## Original negatives preserved

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi UNMEASURED; whole system INCOMPLETE. No model, runtime, registered cohort, seed or original evidence was modified by this analysis.
