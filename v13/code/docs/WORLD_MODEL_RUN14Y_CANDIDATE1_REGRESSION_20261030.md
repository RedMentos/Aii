# Run14Y — candidate 1 regression preserved (2026-10-30)

Original test-first Actions 41128046744: 15 tests, 4 expected failures, 0 errors. All setup/pin/compile/privacy/diff exits zero. Original ZIP artifact 13011676801 SHA256 eb3de6e239aeeee7afd8cdbd72e3e9f3752cbdc1666505f93439bd1911d4f603, CRC and 18/18 SHA256SUMS verified.

First candidate Actions 41128169920: 36 tests, 1 failure, 0 errors; all setup/pin/compile/privacy/diff exits zero. ZIP artifact 13012575385. Existing `test_world_model.FiniteEvidence.test_malformed_persisted_transitions_are_skipped_not_fitted` expects a row with nonfinite **optional latent** to remain eligible as a real action transition with `latent=None`. Importing World F4's full `_strict_json_object` rejected the entire row because its parse_constant rejects NaN even in unused optional latent. That changes historical T8 fit inclusion and breaks a passing regression. Do not waive or edit the historical test.

Candidate 2 will reuse only World F4's `_unique_world_object` duplicate-key hook with `json.loads` and require an object, while retaining existing T8 numeric checks on authoritative forecast/outcome and optional latent. This is a deliberate narrower policy than World F4 derived-receipt admission. Duplicate keys remain rejected at every depth. Original failed candidate remains archived and not a success. All gates remain negative.
