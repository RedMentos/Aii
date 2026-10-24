# V13 Run29 — WP-T8 actual SQLite data-path regression for World-Model

Base PR64 `b638ccc942ef4e545f8a26a38a59ff0f8af312c1`. This is a new isolated **test package** using Run28 candidate; no edits to production runtime, Canon, learning/age gates, original preregistrations or other owners. Tests create a real on-disk SQLite database with the minimal actual actions/packets/kv/log tables and synthetic own digital action outcomes. No LLM, external tools or Redmi.

## Tests

7/7 Linux SQLite+NumPy synthetic integration tests PASS, compileall PASS. Real DB queries, action selection packets, training from 160 persisted rows, heldout forward/inverse metrics, state-align UNAVAILABLE without latent, MEASURED with actual stored latent, counterfactual HYPOTHESIS, save/reopen/load, malformed rows excluded, corrupted stored weights fail closed, valid for_event path, and too-few-transitions restart all exercised.

**Claim limit:** Actual SQLite data path tested with synthetic digital transitions, NOT native LLM-generated actions, NOT a proven causal world model, NOT Redmi. The real V13 runtime/full-suite and official privacy scan remain NOT RUN because this container cannot clone GitHub. No gate promoted. The isolated Run28 source is copied byte-for-byte for self-contained test; source SHA in this package must match PR64.

## Next

Independently integrate the candidate on the full current checkout, run original world-model tests and real SQLite migration/restart. Add explicit skipped-row counts/telemetry before claiming robust ingestion; then register a fresh observed action-outcome cohort for WP-Z12 / G-SELF-WORLD-005 and separate body/world JEPA ablations. All original failed/unavailable gates remain.
