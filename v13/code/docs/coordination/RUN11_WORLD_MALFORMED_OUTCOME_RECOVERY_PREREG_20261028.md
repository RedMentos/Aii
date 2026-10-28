# Run11 World malformed completed outcome recovery prereg — 2026-10-28

Owner GPT-6, independent review-only F4 World/Self lifecycle candidate based on #850 at `b454f81da33de9d621af6417ed47ab55cba6263f`. This preregistration precedes code. Separate from timing numeric validity #861; do not edit #861, frozen cohorts, model/source hashes, or main.

**Observed source-level failure:** `Store.finish_action` durably accepts any JSON-serializable `actual`, including `[]`, `null`, a string or integer. `WorldState.observe` assumes decoded outcome is a dict and calls `.get`; `WorldState.forecast` also assumes every completed outcome is a dict. A malformed completed outcome can raise during `WorldState.recover` and block reconstruction after restart. The action itself must remain preserved as raw evidence, not silently rewritten to a fabricated successful dict.

**Planned minimal candidate:** Treat non-dict completed outcomes as invalid timing evidence; exclude them from forecast samples with an explicit invalid-outcome count, but preserve their raw JSON value in `PredictionOutcome.observation.observed`. In `observe`, use a separate safe dict view only for optional fields, never score timing/latent reward on malformed data, and still persist the PredictionOutcome and rebuild materialized World state. Keep valid dict behavior byte-equivalent. Do not change Store serialization, model training, Age0 rights, semantic authority, or original native evidence.

**Tests:** actual Store/Runtime with a malformed JSON-serializable completed action, direct observe and crash-window restart/recover, raw value preserved, no timing score, subsequent valid actions still forecast correctly; baseline valid World tests unchanged. Exact-source Linux focused/full regression, privacy, raw ZIP. No native model run or Redmi.

All gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight0, Age0 RECORD_ONLY, phone_measured=false, whole_system_complete=false.