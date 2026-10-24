# Run68 design review refinement before implementation

The prereg originally said to refuse a fallback `stable_prefix` transcript. Independent source inspection showed this would prevent append-only from ever bootstrapping: the first turn necessarily falls back to `stable_prefix` when no prior transcript exists. The intended invariant is therefore **qualified seed provenance**, not a ban on every stable_prefix seed.

An actual same-mode stable_prefix plan may seed the next append-only turn only when the configured layout was append_only, consecutive-user capability was verified, the plan was within the transcript cap, and the persisted record explicitly marks `append_seed=true`, `applied`, and its effective layout. SHADOW seeds remain eligible for SHADOW-only hypothetical cache evaluation, never for ACTIVE. Legacy entries without metadata fail closed. No model/age/permission gates change.

This correction was recorded before tests of the production callsite; the original prereg remains intact.
