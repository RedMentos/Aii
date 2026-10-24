# Run67 prereg — exact source-ID matching in JEF experience lifecycle

2026-10-24. Base Run66 PR99 978c41a2ebd15b0696c510d024b50cc0487c478f. Own minimal `v13/code/v13/jefoutcome.py` lifecycle diff, new `v13/code/v13/jef_lifecycle_sources.py`, `v13/code/tests/test_jef_lifecycle_sources.py`, and `v13/code/docs/proofs/continuation-20261024/jef-lifecycle-run67/*`. No changes to Callosum, Sleep, World, history owner or native jobs.

Source observation: `jefoutcome.lifecycle` identifies an update as dependent on a feedback/outcome source if `any(sid in u['manifest'] for sid in srcs)`. This is raw substring matching in serialized JSON, so source ID 'src1' matches 'src10' or an unrelated string field and may falsely report L4/L5/L7/L9/L11 progress, including promotion. No actual model update is implied by this read-model bug.

Fix: parse each manifest as a JSON mapping, read only the explicit `source_ids` list of exact string identifiers, match via set intersection. Malformed/nonmapping manifests and malformed source_ids are excluded, not guessed. Keep all lifecycle stage names, read-only behavior, permissions, age and learning gates unchanged. Preserve original false-positive RED.

Predeclared tests: substring collision, unrelated text field, exact source match, malformed JSON, non-list source_ids, duplicate IDs, empty sources, no source authority changes, Python -O. Actual lifecycle+SQLite integration requires complete checkout; full suite/privacy/native/Redmi separate. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE.
