# WP-T8 WorldModel source-lineage preflight — preregistration (2026-10-25)

Base: verified Run222 PR250 head `d0bf78b933718b4def9bb821c1683af7c5d5b498`. Independent of active Run223 DS3 owner; exclusive production ownership `v13/code/v13/world_model.py`, new `v13/code/tests/test_world_event_source_integrity_20261025.py`, new workflow and this proof directory. No Runtime, DS3, native owner, learning/age/approval, registered cohort or gate edits.

Problem: `world_model.transitions` and `for_event` currently accept numerically valid actions without checking the originating EventEnvelope's SourceRef when a real Store source reader is available. A revoked or tampered event source must not remain valid evidence for world-model fitting or event counterfactuals. Existing synthetic SQLite test doubles without source reader are *legacy test-only* and must retain their existing behavior; this exception is not a production authorization.

Predeclared adversarial checks:
1. An action with intact EventEnvelope, matching source_id and verified readable source remains one observed row; no model fit is implied.
2. Deleted source, missing event, mismatched source_id, malformed event packet or failed source read produce **zero** observed transitions, not invented zero data.
3. `for_event` for such an action returns `SIMULATION_UNCERTAIN`, `authority=HYPOTHESIS`, `confidence=0`, `prediction=None`, reason `INVALID_EVENT_SOURCE`.
4. Unmodified minimal synthetic SQLite test doubles without `read_source` continue their legacy test semantics, so existing non-source-specific tests remain valid.
5. No external tools, model weights, live JEF authority, native model or Redmi claim. The original gates remain STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, whole V13 incomplete.

RED-first: commit preregistration then adversarial tests; preserve failing actual-source CI. GREEN: narrow WorldModel source validation only, rerun existing WorldModel regressions and privacy scan. Fitted-model provenance/revocation *after fitting* is a distinct follow-up package and is **not** claimed solved by this ingest guard.

Next independent work after checkpoint: source-bind fitted WorldModel state and invalidate persisted weights after source revocation, with full lineage/restart test; or continue other canonical package if owner conflict.
