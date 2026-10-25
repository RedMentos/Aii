# WorldModel fitted-state source lineage and revocation — prereg (2026-10-25)

Base: PR258 exact full-suite head `ddad7815b368819c8987695c0bee1256e104ddff`. Exclusive ownership: `v13/code/v13/world_model.py`, `v13/code/tests/test_world_model.py` (synthetic fixture separation), new actual-Store test, unique CI/proof. No changes to DS3, Runtime, live C3/JEF, ContextOS, model/seed registrations, LP3, Age, source snapshots, native owner or gate policy.

Gap after WP-T8 PR252: WorldModel now verifies live EventEnvelope source **when ingesting** observations and in `for_event`, but a fitted `world_model_state` can remain usable after one of its training sources is revoked, or an action outcome is changed. Old v1 fitted states are unbound.

Predeclared contract:
1. Actual Store with >=8 legitimate final actions and verified EventEnvelope source can fit; persisted state must include exact action/source lineage, deterministic action row hashes, and model payload integrity; `load` rechecks all bindings before every use.
2. After source deletion, event packet/source mismatch, action outcome mutation or model-state tampering, `load` refuses and `counterfactual` returns no supported prediction; explicit stale `st` cannot bypass checks when a real Store source reader exists.
3. Old unbound revision is not loadable in production; no automatic rebind of old weights. Synthetic SQLite test doubles without `read_source` may still exercise pure math and are never native/production evidence.
4. Revalidate before persistence after fit to catch mid-fit revocation; source changes after commit remain blocked at load. No learning activation, semantic truth authority, native inference, Redmi, or whole-system promotion.
5. Preserve existing numeric WorldModel tests via an explicitly synthetic Store double, not by disabling production source checks. All original STEP2/B3/Body-JEPA/jepa_weight negative gates remain.

RED-first: actual-Store revocation/restart/tamper tests before implementation, closed failing CI. GREEN: narrowly implement revision v2 source-bound state, run existing WorldModel suites, actual Runtime integration and privacy scan. Preserve failed attempts and exact remote hashes.

Potential cost: verifying up to MAX_ROWS source blobs at each load is conservative and may affect latency; measure separately on device before claiming phone-ready. No cache that could bypass revocation.
