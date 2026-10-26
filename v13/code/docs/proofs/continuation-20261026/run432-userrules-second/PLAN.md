# Run432 — independent Claude WP-UR8 second-opinion integrity review

Date 2026-10-26. Owner GPT. Source-only review branch stacked on Claude WP-UR8 PR416 exact head `65ff1cd8d27732ba4691879b5db4afaabc7b890e`. Does not mutate Claude branch, frozen classifier weights, thresholds, training data or sealed cohorts.

## Counterexample / RED-first

The active learned JEF second-opinion is allowed to add caution only. `userrules._second` catches classifier exceptions and asks, but Python JSON accepts nonfinite `NaN` and `Infinity` and the classifier's floating-point sigmoid/comparison can return NaN without raising. `NaN >= threshold` is false. A corrupted model's bias, threshold or selected weight can therefore silently suppress the cautionary question even though the fixed reader found no restriction. The model loader also accepts nonfinite JSON literals. The test preregisters these cases and verifies unchanged valid-model behavior before modifying source.

## Repair / acceptance

Reject nonfinite JSON constants and invalid schema/weights/threshold at model load before caching. Detect nonfinite score and threshold on every inference, raising to existing `_second` fail-cautious handler. Preserve valid classifier numerical outputs, default `jef`, fixed-reader authority, K8 no-loosening, and the WP-UR8 verdict `USER_RULES_V8_UNSAFE`. Run focused and inherited userrules tests and privacy scan; preserve actual RED and GREEN Actions logs and hashes. No new fresh round, no safety/accuracy gate promotion.

## Boundaries

This is a corruption-integrity fix, not a demonstration that user-rule interpretation is safe. No native model, Redmi, STEP2, B3, Body-JEPA or Age proof.
