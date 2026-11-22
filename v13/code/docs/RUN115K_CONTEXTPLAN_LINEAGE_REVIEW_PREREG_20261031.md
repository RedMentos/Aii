# Run115K-R3 persisted ContextPlan lineage guard prereg (2026-10-31)

Independent review of exact Run115K-R2 source HEAD `1ec6e3e3aab2af3b05bc67e8c1860f5de3b52b29`. The preceding source/authority patch is GREEN on original Actions 41223662925; original RED 41223522704 retained.

Hypothesis: after `build_typed_jef_role_formatter` persists a SHADOW ContextPlan, a deleted or tampered `packets(kind='ContextPlan')` payload can leave the Run115K bridge returning VERIFIED with an orphaned or modified plan ID. The bridge currently rechecks sources, offers, JEF recipe and mode but not the persisted plan packet. This violates the meaning of a claimed ContextPlan lineage even though no native output occurs.

Frozen test before fix: real SQLite Runtime + synthetic B1/B2 offers; monkeypatch only the formatter return boundary to tamper the actual persisted ContextPlan packet after creation. Expected fail-closed with no C3 messages and orphan ID, while untampered positive control stays green. Also reject missing plan, foreign event, changed generation, non-SHADOW mode or changed provenance. Implement minimal read-only exact plan validation before/after prompt assembly. Preserve original RED attempt and new GREEN raw artifact, no frozen cohort/source changes.

No production wiring, native calls, Redmi, STEP2/B3/Body-JEPA/age/JEPA promotion. This is an integrity guard only.
