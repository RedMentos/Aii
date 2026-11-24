# V13 DE closed-world numeric coverage — preregistration (2026-10-30, run11a)

Owner: `assistant/v13-de-closedworld-run11a-20261030`. Parent PR #1223 HEAD `be26f5176a55180be0f9086868a9c4a1c2a5889c`. Review-only, **unwired SHADOW_ONLY**. No native inference, no live ToolStep/C5, no new age/learning/approval rights. Existing `listarith_de_shadow_pipeline.py` and frozen seed79/83/97 cohorts MUST remain byte-identical.

## Problem, falsifiable scope
The current source-binding verifier proves each C3-extracted (name, number) appears in the source but does not prove **completeness**. C3 can omit a source item and still emit a plausible but wrong total or max-minus-min. This package adds a conservative **candidate wrapper** that requires a bijection between all integer tokens in the pre-question data segment and all extracted values, preserving the current source-name binding and original operation classifier. Metadata numbers, dates, aggregates, decimals and ambiguous question boundaries may cause safe abstentions; do not silently exclude them to inflate coverage.

## Frozen design and tests, before code
- Seed 101, 24 fresh synthetic German cases: 12 fully enumerated supported tasks (8 totals, 4 max-min) and 12 negative cases (omitted items, repeated-value omissions, hidden extreme, unrelated metadata year, stated aggregate, decimal, malformed source, mismatched JSON). Fixture is committed separately **after this prereg and before candidate source**. No seed79/83/97 fixture changes.
- Evaluate both frozen baseline `listarith_de_shadow_pipeline.evaluate` and new wrapper on the same rows. Preserve exact numeric answers only for supported rows. At least 10/12 positive supported, **12/12 negative abstentions**, **0 wrong emitted**, **0 negative-gate promotion**; explicitly report any baseline unsafe accepted omissions.
- New wrapper must fail closed when the source has any unclaimed integer occurrence, when extracted values include unbound source tokens, or when question/data separation is ambiguous. Duplicate integer values require multiplicity. Signs including Unicode minus normalize consistently; decimals do not get rounded/truncated. No parsing of HTML or external input authority.
- Tests include adversarial mutation controls and exact source SHA/provenance; unit tests are software/synthetic only. Run focused tests, compile, privacy scan, diff check through a dedicated GitHub Actions workflow; retain raw output and SHA256SUMS artifact. Do not call this native or independent blind generalization.

## Success and follow-up
This package is a safety/precision candidate, **not** evidence that STEP2 utility improves. After remote-verified checkpoint, pursue an independent next package: measured coverage on original closed seed83 native rows without changing their frozen scoring, then fresh preregistered native or another organ if heavy owner active. Never change frozen model, source pins, seed, raw failures or claims.

Gates: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; Redmi UNMEASURED; whole V13 INCOMPLETE.
