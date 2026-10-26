# Run403 — independent registered 378-row STEP2 full-cohort postflight

2026-10-26. Owner GPT continuation. Base Run402/PR397 `b213c1231373f666d9246584841737cf252ddcfa`, stacked review only. Own new `scripts/run403_full_postflight.py`, `tests/test_run403_full_postflight.py`, new workflow and this proof folder. No changes to frozen Run394/395 fixture/model/seed/runtime or Run397 append-only native runner. Run401 real O_s20 native job `40250662450` is a separate active owner; Run403 is source-only and must not start a competing model job.

## Gap

Run397 records validated native attempts but does not aggregate all 9 arms (O/P/S × seeds 20/21/22), six fixtures, seven variants = 378 rows into independent paired utility and source/quote provenance. Pilot Run396 covers only 42 rows. Need an independent full-cohort verifier before any STEP2 claim.

## Scope and acceptance

- Read-only audit of the **exact preregistered** FULL manifest, all nine validated Run397 completed receipts, native source/model/runner/consumer/row hashes, finite field utilities, zero wrong committed tool actions, append-only failure history and consistent manifest.
- For each seed, fixture and variant, compute paired P−O and P−S utility differences with identical fixture/seed pairing; aggregate means and explicit per-seed/per-fixture slices. Keep native timing and memory as descriptive if present; do not manufacture confidence or use pilot to choose thresholds.
- If any arm is missing or invalid, report `INCOMPLETE_OR_RED`, preserve all negative gates and all raw; never silently average only completed arms. A source-only synthetic 378-row test is not native evidence.
- Even with complete native data, do not auto-promote STEP2; the canonical gate needs preregistered threshold/controls, independent review, and no regression. Preserve B3 L1 FAIL, Body-JEPA/jepa_weight=0, Age0, no Redmi and whole V13 incomplete.

## Next

Once all nine native arms are observed, use the full-cohort postflight on the verified restored work tree, hash-close the result and compare to registered STEP2 utility gates. Until then continue serial Run401/Run402 staged native work and independent blueprint implementation.